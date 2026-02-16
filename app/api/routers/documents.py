from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.client import Client
from app.models.document import Document, DocumentType, PaymentMethod
from app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate
from app.services.alert_service import calculate_alert_date
from app.services.audit_log_service import log_event
from app.services.storage_service import save_document_pdf

router = APIRouter(prefix="/documents", tags=["documents"])

DOC_TYPE_LABELS = {
    DocumentType.DNI: "DNI",
    DocumentType.DRIVING_LICENSE: "carnet de conducir",
    DocumentType.CAP: "CAP",
    DocumentType.TACHOGRAPH_CARD: "tarjeta de tacografo",
    DocumentType.POWER_OF_ATTORNEY: "poder notarial",
    DocumentType.OTHER: "otro",
}


def _normalize_payment_fields(data: dict, doc_type: DocumentType) -> None:
    operation_number = data.get("operation_number")
    if isinstance(operation_number, str) and not operation_number.strip():
        data["operation_number"] = None

    if doc_type not in {DocumentType.CAP, DocumentType.TACHOGRAPH_CARD}:
        data["renewed_with_us"] = False
        data["payment_method"] = None
        data["fundae"] = False
        data["fundae_payment_type"] = None
        data["operation_number"] = None
        return

    renewed_with_us = bool(data.get("renewed_with_us"))
    payment_method = data.get("payment_method")
    fundae = bool(data.get("fundae"))
    fundae_payment_type = data.get("fundae_payment_type")

    if not renewed_with_us:
        data["payment_method"] = None
        data["fundae"] = False
        data["fundae_payment_type"] = None
        data["operation_number"] = None
        return

    if payment_method is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Si el documento esta renovado con nosotros, la forma de pago es obligatoria.",
        )

    if payment_method != PaymentMethod.EMPRESA:
        data["fundae"] = False
        data["fundae_payment_type"] = None
        data["operation_number"] = None
        return

    # Para pago EMPRESA, FUNDAE es solo un indicador informativo.
    # El tipo (recibo/transferencia) y numero de operacion pueden guardarse
    # independientemente de que FUNDAE este activado o no.
    data["fundae"] = fundae
    data["fundae_payment_type"] = fundae_payment_type


def _validate_payload(data: dict, doc_type: DocumentType) -> None:
    if doc_type == DocumentType.DNI:
        if not data.get("expiry_date") or not data.get("birth_date") or not data.get("address"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El DNI requiere fecha de caducidad, fecha de nacimiento y direccion.",
            )

    if doc_type == DocumentType.DRIVING_LICENSE:
        if not data.get("expiry_date") or not data.get("issue_date") or not data.get("address"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El carnet de conducir requiere fecha de caducidad, fecha de obtencion y direccion.",
            )

    if doc_type in {DocumentType.CAP, DocumentType.TACHOGRAPH_CARD, DocumentType.OTHER}:
        if not data.get("expiry_date"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El documento {DOC_TYPE_LABELS.get(doc_type, doc_type.value)} requiere fecha de caducidad.",
            )

    if doc_type == DocumentType.POWER_OF_ATTORNEY:
        has_flag = data.get("flag_fran") or data.get("flag_ciusaba")
        if not has_flag:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El poder notarial requiere al menos un apoderamiento: Fran o CIUSABA.",
            )
        if data.get("flag_fran") and not data.get("expiry_fran"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="expiry_fran es obligatorio cuando flag_fran es verdadero.",
            )
        if data.get("flag_ciusaba") and not data.get("expiry_ciusaba"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="expiry_ciusaba es obligatorio cuando flag_ciusaba es verdadero.",
            )


def _collect_document_expiry_dates(document: Document) -> list[date]:
    expiries: list[date] = []
    if document.doc_type == DocumentType.POWER_OF_ATTORNEY:
        if document.flag_fran and document.expiry_fran:
            expiries.append(document.expiry_fran)
        if document.flag_ciusaba and document.expiry_ciusaba:
            expiries.append(document.expiry_ciusaba)
        return list(dict.fromkeys(expiries))

    if document.expiry_date:
        expiries.append(document.expiry_date)
    return expiries


def _document_payload_dict(document: Document) -> dict:
    return {
        "client_id": document.client_id,
        "doc_type": document.doc_type,
        "expiry_date": document.expiry_date,
        "issue_date": document.issue_date,
        "birth_date": document.birth_date,
        "address": document.address,
        "pdf_path": document.pdf_path,
        "course_number": document.course_number,
        "renewed_with_us": document.renewed_with_us,
        "payment_method": document.payment_method,
        "fundae": document.fundae,
        "fundae_payment_type": document.fundae_payment_type,
        "operation_number": document.operation_number,
        "flag_fran": document.flag_fran,
        "flag_ciusaba": document.flag_ciusaba,
        "expiry_fran": document.expiry_fran,
        "expiry_ciusaba": document.expiry_ciusaba,
    }


async def _upsert_auto_alert(session: AsyncSession, document: Document) -> None:
    target_expiries = set(_collect_document_expiry_dates(document))
    existing_alerts = list(await session.scalars(select(Alert).where(Alert.document_id == document.id)))

    alerts_by_expiry: dict[date, Alert] = {}
    for alert in existing_alerts:
        current = alerts_by_expiry.get(alert.expiry_date)
        if current is None:
            alerts_by_expiry[alert.expiry_date] = alert
        else:
            await session.delete(alert)

    for expiry_date, alert in list(alerts_by_expiry.items()):
        if expiry_date not in target_expiries:
            await session.delete(alert)

    for expiry_date in target_expiries:
        alert = alerts_by_expiry.get(expiry_date)
        alert_date = calculate_alert_date(expiry_date)
        if alert is None:
            session.add(
                Alert(
                    client_id=document.client_id,
                    document_id=document.id,
                    expiry_date=expiry_date,
                    alert_date=alert_date,
                )
            )
            continue
        alert.client_id = document.client_id
        alert.expiry_date = expiry_date
        alert.alert_date = alert_date


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate, session: AsyncSession = Depends(get_db_session)) -> Document:
    client = await session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    data = payload.model_dump()
    _normalize_payment_fields(data, payload.doc_type)
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
                Document.course_number.ilike(like),
            )
        )

    result = await session.scalars(query.order_by(Document.created_at.desc()))
    return list(result)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: int, session: AsyncSession = Depends(get_db_session)) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
    return document


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    payload: DocumentUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")

    updates = payload.model_dump(exclude_unset=True)
    if "client_id" in updates:
        client = await session.get(Client, updates["client_id"])
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    for field, value in updates.items():
        setattr(document, field, value)

    data = _document_payload_dict(document)
    _normalize_payment_fields(data, document.doc_type)
    document.renewed_with_us = data["renewed_with_us"]
    document.payment_method = data["payment_method"]
    document.fundae = data["fundae"]
    document.fundae_payment_type = data["fundae_payment_type"]
    document.operation_number = data["operation_number"]
    _validate_payload(data, document.doc_type)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")

    client = await session.get(Client, document.client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    if not document_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archivo vacio.")
    if not document_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se permiten archivos PDF.")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")

    await session.delete(document)
    await session.commit()
    log_event("delete_document", f"document_id={document_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
