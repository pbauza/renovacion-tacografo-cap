from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.client import Client
from app.models.document import Document
from app.pdf_generator import PdfGeneratorService
from app.services.alert_service import calculate_alert_date
from app.services.audit_log_service import log_event, read_recent_logs
from app.services.importer_service import ImportValidationError, SpreadsheetImporter, parse_document_type, to_bool, to_date

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/import/template")
async def download_import_template() -> FileResponse:
    path = Path("static/samples/clients_import_example.xlsx")
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template file not found")
    return FileResponse(path, filename="clients_import_example.xlsx")


@router.post("/import/clients")
async def import_clients(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    upload_dir = Path("storage/imports")
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = upload_dir / file.filename

    with input_path.open("wb") as output:
        output.write(await file.read())

    importer = SpreadsheetImporter()
    try:
        rows = importer.import_file(input_path)
    except ImportValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    clients_created = 0
    clients_updated = 0
    documents_created = 0
    errors: list[str] = []

    for row in rows:
        data = row.data
        try:
            nif = str(data.get("nif") or "").strip()
            full_name = str(data.get("full_name") or "").strip()
            phone = str(data.get("phone") or "").strip()
            company = data.get("company")
            email = data.get("email")

            if not nif or not full_name or not phone:
                errors.append(f"Row {row.row_number}: missing required fields")
                continue

            client = await session.scalar(select(Client).where(Client.nif == nif))
            if client is None:
                client = Client(full_name=full_name, nif=nif, phone=phone, company=company, email=email)
                session.add(client)
                await session.flush()
                clients_created += 1
            else:
                client.full_name = full_name
                client.phone = phone
                client.company = company
                client.email = email
                clients_updated += 1

            doc_type = parse_document_type(data.get("document_type"))
            expiry_date = to_date(data.get("expiry_date"))
            if doc_type and expiry_date:
                doc = Document(
                    client_id=client.id,
                    doc_type=doc_type,
                    expiry_date=expiry_date,
                    issue_date=to_date(data.get("issue_date")),
                    birth_date=to_date(data.get("birth_date")),
                    address=data.get("address"),
                    course_number=data.get("course_number"),
                    flag_fran=to_bool(data.get("flag_fran")),
                    flag_ciusaba=to_bool(data.get("flag_ciusaba")),
                    expiry_fran=to_date(data.get("expiry_fran")),
                    expiry_ciusaba=to_date(data.get("expiry_ciusaba")),
                )
                session.add(doc)
                await session.flush()
                existing_alert = await session.scalar(select(Alert).where(Alert.document_id == doc.id))
                if existing_alert is None:
                    session.add(
                        Alert(
                            client_id=client.id,
                            document_id=doc.id,
                            expiry_date=expiry_date,
                            alert_date=calculate_alert_date(expiry_date),
                        )
                    )
                documents_created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Row {row.row_number}: {exc}")

    await session.commit()
    log_event("import_clients", f"created={clients_created}, updated={clients_updated}, docs={documents_created}, errors={len(errors)}")

    return {
        "clients_created": clients_created,
        "clients_updated": clients_updated,
        "documents_created": documents_created,
        "errors": errors,
    }


@router.post("/pdf/client/{client_id}")
async def generate_client_pdf(client_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    docs = list(await session.scalars(select(Document).where(Document.client_id == client_id).order_by(Document.created_at.asc())))
    alerts = list(await session.scalars(select(Alert).where(Alert.client_id == client_id).order_by(Alert.alert_date.asc(), Alert.created_at.asc())))

    service = PdfGeneratorService()
    output_name = service.default_output_name(prefix=f"cliente_{client.nif}")
    output_path = Path("storage/exports") / output_name
    generated = service.generate_client_report(
        output_path=output_path,
        client=client,
        documents=docs,
        alerts=alerts,
    )
    log_event(
        "generate_client_pdf",
        f"client_id={client_id}, documents={len(docs)}, alerts={len(alerts)}, output={generated.as_posix()}",
    )

    return {"path": generated.as_posix(), "filename": generated.name}


@router.post("/pdf/bulk")
async def generate_bulk_pdf(session: AsyncSession = Depends(get_db_session)) -> dict:
    docs = list(await session.scalars(select(Document).where(Document.pdf_path.is_not(None)).order_by(Document.created_at.asc())))
    pdf_files = [doc.pdf_path for doc in docs if doc.pdf_path]

    if not pdf_files:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No PDF documents available")

    service = PdfGeneratorService()
    output_name = service.default_output_name(prefix="bulk_renovaciones")
    output_path = Path("storage/exports") / output_name
    generated = service.generate_bundle(output_path=output_path, ordered_files=pdf_files)
    log_event("generate_bulk_pdf", f"documents={len(pdf_files)}, output={generated.as_posix()}")

    return {"path": generated.as_posix(), "filename": generated.name, "documents": len(pdf_files)}


@router.get("/logs")
async def get_system_logs(limit: int = 200) -> dict:
    return {"lines": read_recent_logs(limit=limit)}
