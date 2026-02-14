from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import and_, cast, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.client import Client
from app.models.document import Document, DocumentType
from app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate
from app.services.alert_service import calculate_alert_date
from app.services.audit_log_service import log_event
from app.services.storage_service import save_document_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


def _validate_payload(data: dict, doc_type: DocumentType) -> None:
    if doc_type == DocumentType.DNI:
        if not data.get("expiry_date") or not data.get("birth_date") or not data.get("address"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="DNI requires expiry_date, birth_date and address")

    if doc_type == DocumentType.DRIVING_LICENSE:
        if not data.get("expiry_date") or not data.get("issue_date") or not data.get("address"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Driving license requires expiry_date, issue_date and address")

    if doc_type in {DocumentType.CAP, DocumentType.TACHOGRAPH_CARD, DocumentType.OTHER}:
        if not data.get("expiry_date"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{doc_type.value} requires expiry_date")

    if doc_type == DocumentType.POWER_OF_ATTORNEY:
        has_flag = data.get("flag_fran") or data.get("flag_ciusaba")
        if not has_flag:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Power of attorney requires at least one flag: flag_fran or flag_ciusaba")
        if data.get("flag_fran") and not data.get("expiry_fran"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expiry_fran is required when flag_fran is true")
        if data.get("flag_ciusaba") and not data.get("expiry_ciusaba"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expiry_ciusaba is required when flag_ciusaba is true")


async def _upsert_auto_alert(session: AsyncSession, document: Document) -> None:
    if not document.expiry_date:
        return

    alert = await session.scalar(select(Alert).where(Alert.document_id == document.id))
    alert_date = calculate_alert_date(document.expiry_date)

    if alert is None:
        session.add(
            Alert(
                client_id=document.client_id,
                document_id=document.id,
                expiry_date=document.expiry_date,
                alert_date=alert_date,
            )
        )
    else:
        alert.client_id = document.client_id
        alert.expiry_date = document.expiry_date
        alert.alert_date = alert_date


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate, session: AsyncSession = Depends(get_db_session)) -> Document:
    client = await session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    data = payload.model_dump()
    _validate_payload(data, payload.doc_type)

    document = Document(**data)
    session.add(document)
    await session.flush()

    await _upsert_auto_alert(session, document)
    await session.commit()
    await session.refresh(document)
    log_event("create_document", f"document_id={document.id}, client_id={document.client_id}")
    return document


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    client_id: int | None = Query(default=None),
    doc_type: DocumentType | None = Query(default=None),
    expiration_status: str | None = Query(default=None, description="expired|expiring|ok"),
    expires_within_days: int | None = Query(default=None),
    missing_pdf: bool = Query(default=False),
    q: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[Document]:
    query = select(Document)

    if client_id is not None:
        query = query.where(Document.client_id == client_id)
    if doc_type is not None:
        query = query.where(Document.doc_type == doc_type)
    if missing_pdf:
        query = query.where(Document.pdf_path.is_(None))

    today = date.today()
    if expiration_status == "expired":
        query = query.where(Document.expiry_date.is_not(None), Document.expiry_date < today)
    elif expiration_status == "expiring":
        query = query.where(Document.expiry_date.is_not(None), Document.expiry_date >= today, Document.expiry_date <= today + timedelta(days=90))
    elif expiration_status == "ok":
        query = query.where(or_(Document.expiry_date.is_(None), Document.expiry_date > today + timedelta(days=90)))

    if expires_within_days is not None and expires_within_days > 0:
        query = query.where(Document.expiry_date.is_not(None), Document.expiry_date >= today, Document.expiry_date <= today + timedelta(days=expires_within_days))

    if q:
        like = f"%{q}%"
        query = query.join(Client, Client.id == Document.client_id).where(
            or_(
                Client.full_name.ilike(like),
                Client.nif.ilike(like),
                cast(Document.doc_type, String).ilike(like),
            )
        )

    result = await session.scalars(query.order_by(Document.created_at.desc()))
    return list(result)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: int, session: AsyncSession = Depends(get_db_session)) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    payload: DocumentUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    updates = payload.model_dump(exclude_unset=True)
    if "client_id" in updates:
        client = await session.get(Client, updates["client_id"])
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    for field, value in updates.items():
        setattr(document, field, value)

    _validate_payload(document.__dict__, document.doc_type)
    await _upsert_auto_alert(session, document)

    await session.commit()
    await session.refresh(document)
    log_event("update_document", f"document_id={document.id}")
    return document


@router.post("/{document_id}/file", response_model=DocumentRead)
async def upload_document_file(
    document_id: int,
    document_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    client = await session.get(Client, document.client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if not document_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if not document_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")

    stored_path = save_document_pdf(client.nif, document.doc_type.value, document_file)
    document.pdf_path = stored_path

    await session.commit()
    await session.refresh(document)
    log_event("upload_document_pdf", f"document_id={document.id}, file={stored_path}")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, session: AsyncSession = Depends(get_db_session)) -> Response:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await session.delete(document)
    await session.commit()
    log_event("delete_document", f"document_id={document_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
