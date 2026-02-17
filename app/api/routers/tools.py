from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.client import Client
from app.models.document import Document, DocumentType, PaymentMethod
from app.pdf_generator import PdfGeneratorService
from app.services.alert_service import calculate_alert_date
from app.services.audit_log_service import log_event, read_recent_logs
from app.services.importer_service import (
    ImportValidationError,
    SpreadsheetImporter,
    parse_document_type,
    parse_fundae_payment_type,
    parse_payment_method,
    to_bool,
    to_date,
)

router = APIRouter(prefix="/tools", tags=["tools"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOTS = [PROJECT_ROOT / "config", PROJECT_ROOT / "static/config"]


class ConfigFileUpdate(BaseModel):
    content: str


def _collect_document_expiry_dates(document: Document) -> list:
    expiries: list = []
    if document.doc_type == DocumentType.POWER_OF_ATTORNEY:
        if document.flag_fran and document.expiry_fran:
            expiries.append(document.expiry_fran)
        if document.flag_ciusaba and document.expiry_ciusaba:
            expiries.append(document.expiry_ciusaba)
        return list(dict.fromkeys(expiries))

    if document.expiry_date:
        expiries.append(document.expiry_date)
    return expiries


def _none_if_blank(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    return value


def _matches_nullable(column: Any, value: Any) -> Any:
    return column.is_(None) if value is None else column == value


async def _find_existing_document_for_import(
    session: AsyncSession,
    *,
    client_id: int,
    doc_type: DocumentType,
    expiry_date: Any,
    issue_date: Any,
    birth_date: Any,
    address: Any,
    course_number: Any,
    renewed_with_us: bool,
    payment_method: Any,
    fundae: bool,
    fundae_payment_type: Any,
    operation_number: Any,
    flag_fran: bool,
    flag_ciusaba: bool,
    flag_permiso_c: bool,
    flag_permiso_d: bool,
    expiry_fran: Any,
    expiry_ciusaba: Any,
) -> Document | None:
    query = select(Document).where(
        Document.client_id == client_id,
        Document.doc_type == doc_type,
        _matches_nullable(Document.expiry_date, expiry_date),
        _matches_nullable(Document.issue_date, issue_date),
        _matches_nullable(Document.birth_date, birth_date),
        _matches_nullable(Document.address, address),
        _matches_nullable(Document.course_number, course_number),
        Document.renewed_with_us == renewed_with_us,
        _matches_nullable(Document.payment_method, payment_method),
        Document.fundae == fundae,
        _matches_nullable(Document.fundae_payment_type, fundae_payment_type),
        _matches_nullable(Document.operation_number, operation_number),
        Document.flag_fran == flag_fran,
        Document.flag_ciusaba == flag_ciusaba,
        Document.flag_permiso_c == flag_permiso_c,
        Document.flag_permiso_d == flag_permiso_d,
        _matches_nullable(Document.expiry_fran, expiry_fran),
        _matches_nullable(Document.expiry_ciusaba, expiry_ciusaba),
    )
    return await session.scalar(query.limit(1))


def _resolve_config_path(raw_path: str) -> Path:
    if not raw_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El parametro path es obligatorio.")

    normalized = Path(raw_path.strip().lstrip("/"))
    if normalized.suffix.lower() != ".json":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se permiten archivos .json.")

    resolved = normalized.resolve()
    for root in CONFIG_ROOTS:
        root_resolved = root.resolve()
        try:
            resolved.relative_to(root_resolved)
            return resolved
        except ValueError:
            continue
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La ruta esta fuera de los directorios de configuracion permitidos.")


@router.get("/config/files")
async def list_config_files() -> dict:
    files: list[str] = []
    for root in CONFIG_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            if path.is_file():
                files.append(path.relative_to(PROJECT_ROOT).as_posix())
    files.sort()
    return {"files": files}


@router.get("/config/file")
async def get_config_file(path: str) -> dict:
    target = _resolve_config_path(path)
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo de configuracion no encontrado.")

    content = target.read_text(encoding="utf-8")
    return {"path": target.relative_to(PROJECT_ROOT).as_posix(), "content": content}


@router.put("/config/file")
async def update_config_file(payload: ConfigFileUpdate, path: str) -> dict:
    target = _resolve_config_path(path)
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo de configuracion no encontrado.")

    try:
        import json

        parsed = json.loads(payload.content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"JSON invalido: {exc}") from exc

    normalized = json.dumps(parsed, ensure_ascii=False, indent=2) + "\n"
    target.write_text(normalized, encoding="utf-8")
    rel_path = target.relative_to(PROJECT_ROOT).as_posix()
    log_event("update_config_file", f"path={rel_path}")
    return {"path": rel_path, "saved": True}


@router.get("/import/template")
async def download_import_template() -> FileResponse:
    path = Path("static/samples/clients_import_example.xlsx")
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")
    return FileResponse(path, filename="clients_import_example.xlsx")


@router.post("/import/clients")
async def import_clients(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archivo vacio.")

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
    documents_skipped_existing = 0
    documents_updated_existing = 0
    errors: list[str] = []

    for row in rows:
        data = row.data
        try:
            nif = str(data.get("nif") or "").strip()
            full_name = str(data.get("full_name") or "").strip()
            phone = str(data.get("phone") or "").strip()
            company_raw = data.get("company")
            company = str(company_raw).strip() if company_raw is not None else None
            if company == "":
                company = None
            email_raw = data.get("email")
            email = str(email_raw).strip() if email_raw is not None else None
            if email == "":
                email = None

            if not nif or not full_name:
                errors.append(f"Fila {row.row_number}: faltan campos obligatorios.")
                continue

            client = await session.scalar(select(Client).where(Client.nif == nif))
            if client is None:
                client = Client(full_name=full_name, nif=nif, phone=phone, company=company, email=email)
                session.add(client)
                await session.flush()
                clients_created += 1
            else:
                client.full_name = full_name
                if phone:
                    client.phone = phone
                if company is not None:
                    client.company = company
                if email is not None:
                    client.email = email
                clients_updated += 1

            doc_type = parse_document_type(data.get("document_type"))
            expiry_date = to_date(data.get("expiry_date"))
            if doc_type:
                renewed_with_us = to_bool(data.get("renewed_with_us") or data.get("renovado_con_nosotros"))
                raw_payment_method = data.get("payment_method") or data.get("forma_pago") or data.get("forma de pago")
                payment_method = parse_payment_method(raw_payment_method)
                fundae = to_bool(data.get("fundae") or data.get("fundae_flag") or data.get("flag_fundae"))
                if isinstance(raw_payment_method, str) and raw_payment_method.strip().lower() == "fundae":
                    payment_method = PaymentMethod.EMPRESA
                    fundae = True
                fundae_payment_type = parse_fundae_payment_type(
                    data.get("fundae_payment_type") or data.get("fundae_tipo_pago") or data.get("fundae tipo pago")
                )
                operation_number_raw = (
                    data.get("operation_number") or data.get("numero_operacion") or data.get("numero de operacion")
                )
                operation_number = str(operation_number_raw).strip() if operation_number_raw else None
                if operation_number == "":
                    operation_number = None

                if doc_type not in {DocumentType.CAP, DocumentType.TACHOGRAPH_CARD}:
                    renewed_with_us = False
                    payment_method = None
                    fundae = False
                    fundae_payment_type = None
                    operation_number = None
                elif not renewed_with_us:
                    payment_method = None
                    fundae = False
                    fundae_payment_type = None
                    operation_number = None
                elif payment_method is None:
                    errors.append(f"Fila {row.row_number}: renovado con nosotros requiere forma de pago.")
                    continue
                elif payment_method != PaymentMethod.EMPRESA:
                    fundae = False
                    fundae_payment_type = None
                    operation_number = None

                if doc_type not in {DocumentType.POWER_OF_ATTORNEY, DocumentType.DRIVING_LICENSE} and not expiry_date:
                    errors.append(f"Fila {row.row_number}: falta la fecha de caducidad del documento.")
                    continue

                flag_fran = to_bool(data.get("flag_fran"))
                flag_ciusaba = to_bool(data.get("flag_ciusaba"))
                flag_permiso_c = to_bool(data.get("flag_permiso_c") or data.get("permiso_c") or data.get("flag_c"))
                flag_permiso_d = to_bool(data.get("flag_permiso_d") or data.get("permiso_d") or data.get("flag_d"))
                expiry_fran = to_date(data.get("expiry_fran"))
                expiry_ciusaba = to_date(data.get("expiry_ciusaba"))
                if doc_type != DocumentType.DRIVING_LICENSE:
                    flag_permiso_c = False
                    flag_permiso_d = False
                if doc_type == DocumentType.POWER_OF_ATTORNEY:
                    has_valid_expiry = (flag_fran and expiry_fran) or (flag_ciusaba and expiry_ciusaba)
                    if not has_valid_expiry:
                        errors.append(
                            f"Fila {row.row_number}: en poder notarial debe existir Apoderamiento Fran o Apoderamiento CIUSABA con su fecha de caducidad."
                        )
                        continue

                issue_date = to_date(data.get("issue_date"))
                birth_date = to_date(data.get("birth_date"))
                address = _none_if_blank(data.get("address"))
                course_number = _none_if_blank(data.get("course_number"))

                if doc_type == DocumentType.DRIVING_LICENSE:
                    existing_license = await session.scalar(
                        select(Document).where(
                            Document.client_id == client.id,
                            Document.doc_type == DocumentType.DRIVING_LICENSE,
                        )
                    )
                    if existing_license is not None:
                        merged_c = bool(existing_license.flag_permiso_c) or flag_permiso_c
                        merged_d = bool(existing_license.flag_permiso_d) or flag_permiso_d
                        changed = False
                        if merged_c != existing_license.flag_permiso_c:
                            existing_license.flag_permiso_c = merged_c
                            changed = True
                        if merged_d != existing_license.flag_permiso_d:
                            existing_license.flag_permiso_d = merged_d
                            changed = True
                        if changed:
                            documents_updated_existing += 1
                        else:
                            documents_skipped_existing += 1
                        continue

                existing_document = await _find_existing_document_for_import(
                    session,
                    client_id=client.id,
                    doc_type=doc_type,
                    expiry_date=expiry_date,
                    issue_date=issue_date,
                    birth_date=birth_date,
                    address=address,
                    course_number=course_number,
                    renewed_with_us=renewed_with_us,
                    payment_method=payment_method,
                    fundae=fundae,
                    fundae_payment_type=fundae_payment_type,
                    operation_number=operation_number,
                    flag_fran=flag_fran,
                    flag_ciusaba=flag_ciusaba,
                    flag_permiso_c=flag_permiso_c,
                    flag_permiso_d=flag_permiso_d,
                    expiry_fran=expiry_fran,
                    expiry_ciusaba=expiry_ciusaba,
                )
                if existing_document is not None:
                    documents_skipped_existing += 1
                    continue

                doc = Document(
                    client_id=client.id,
                    doc_type=doc_type,
                    expiry_date=expiry_date,
                    issue_date=issue_date,
                    birth_date=birth_date,
                    address=address,
                    course_number=course_number,
                    renewed_with_us=renewed_with_us,
                    payment_method=payment_method,
                    fundae=fundae,
                    fundae_payment_type=fundae_payment_type,
                    operation_number=operation_number,
                    flag_fran=flag_fran,
                    flag_ciusaba=flag_ciusaba,
                    flag_permiso_c=flag_permiso_c,
                    flag_permiso_d=flag_permiso_d,
                    expiry_fran=expiry_fran,
                    expiry_ciusaba=expiry_ciusaba,
                )
                session.add(doc)
                await session.flush()
                for due_date in _collect_document_expiry_dates(doc):
                    existing_alert = await session.scalar(
                        select(Alert).where(
                            Alert.document_id == doc.id,
                            Alert.expiry_date == due_date,
                        )
                    )
                    if existing_alert is None:
                        session.add(
                            Alert(
                                client_id=client.id,
                                document_id=doc.id,
                                expiry_date=due_date,
                                alert_date=calculate_alert_date(due_date),
                            )
                        )
                documents_created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Fila {row.row_number}: {exc}")

    await session.commit()
    log_event(
        "import_clients",
        (
            f"created={clients_created}, updated={clients_updated}, docs={documents_created}, "
            f"docs_skipped_existing={documents_skipped_existing}, docs_updated_existing={documents_updated_existing}, "
            f"errors={len(errors)}"
        ),
    )

    return {
        "clients_created": clients_created,
        "clients_updated": clients_updated,
        "documents_created": documents_created,
        "documents_skipped_existing": documents_skipped_existing,
        "documents_updated_existing": documents_updated_existing,
        "errors": errors,
    }


@router.post("/pdf/client/{client_id}")
async def generate_client_pdf(client_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

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
    service = PdfGeneratorService()
    clients = list(await session.scalars(select(Client).order_by(Client.created_at.asc())))
    if not clients:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No hay clientes disponibles.")

    individual_reports: list[Path] = []
    for client in clients:
        docs = list(await session.scalars(select(Document).where(Document.client_id == client.id).order_by(Document.created_at.asc())))
        alerts = list(await session.scalars(select(Alert).where(Alert.client_id == client.id).order_by(Alert.alert_date.asc(), Alert.created_at.asc())))

        report_name = service.default_output_name(prefix=f"cliente_{client.nif}")
        report_path = Path("storage/exports") / "bulk_parts" / report_name
        generated_report = service.generate_client_report(
            output_path=report_path,
            client=client,
            documents=docs,
            alerts=alerts,
        )
        individual_reports.append(generated_report)

    output_name = service.default_output_name(prefix="bulk_renovaciones")
    output_path = Path("storage/exports") / output_name
    generated_bundle = service.generate_bundle(output_path=output_path, ordered_files=individual_reports)
    log_event(
        "generate_bulk_pdf",
        f"clients={len(clients)}, reports={len(individual_reports)}, output={generated_bundle.as_posix()}",
    )

    return {
        "path": generated_bundle.as_posix(),
        "filename": generated_bundle.name,
        "clients": len(clients),
        "reports": len(individual_reports),
    }


@router.get("/logs")
async def get_system_logs(limit: int = 200) -> dict:
    return {"lines": read_recent_logs(limit=limit)}
