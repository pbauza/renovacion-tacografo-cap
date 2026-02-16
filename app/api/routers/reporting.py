from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.client import Client
from app.models.document import Document, DocumentType, PaymentMethod
from app.schemas.reporting import DashboardSummary, RenewedDocumentItem, RenewedDocumentsReport

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(session: AsyncSession = Depends(get_db_session)) -> DashboardSummary:
    today = date.today()

    due_30 = await session.scalar(
        select(func.count()).select_from(Document).where(
            Document.expiry_date.is_not(None),
            Document.expiry_date >= today,
            Document.expiry_date <= today + timedelta(days=30),
        )
    )
    due_60 = await session.scalar(
        select(func.count()).select_from(Document).where(
            Document.expiry_date.is_not(None),
            Document.expiry_date >= today,
            Document.expiry_date <= today + timedelta(days=60),
        )
    )
    due_90 = await session.scalar(
        select(func.count()).select_from(Document).where(
            Document.expiry_date.is_not(None),
            Document.expiry_date >= today,
            Document.expiry_date <= today + timedelta(days=90),
        )
    )
    documents_total = await session.scalar(select(func.count()).select_from(Document))
    alerts_total = await session.scalar(select(func.count()).select_from(Alert))
    alerts_due_today_or_older = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.alert_date <= today)
    )

    return DashboardSummary(
        due_in_30_days=due_30 or 0,
        due_in_60_days=due_60 or 0,
        due_in_90_days=due_90 or 0,
        documents_total=documents_total or 0,
        alerts_total=alerts_total or 0,
        alerts_due_today_or_older=alerts_due_today_or_older or 0,
    )


@router.get("/renewals", response_model=RenewedDocumentsReport)
async def get_renewed_documents_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    payment_method: PaymentMethod | None = Query(default=None),
    fundae: bool | None = Query(default=None),
    doc_type: DocumentType | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> RenewedDocumentsReport:
    allowed_doc_types = (DocumentType.CAP, DocumentType.TACHOGRAPH_CARD)
    if doc_type is not None and doc_type not in allowed_doc_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se permite filtrar por CAP o tarjeta de tacografo.",
        )

    selected_year = year or date.today().year
    year_start = datetime(selected_year, 1, 1)
    next_year_start = datetime(selected_year + 1, 1, 1)

    query = (
        select(Document, Client)
        .join(Client, Client.id == Document.client_id)
        .where(
            Document.renewed_with_us.is_(True),
            Document.doc_type.in_(allowed_doc_types),
            Document.created_at >= year_start,
            Document.created_at < next_year_start,
            Document.payment_method.is_not(None),
        )
    )

    if payment_method is not None:
        query = query.where(Document.payment_method == payment_method)
    if fundae is not None:
        query = query.where(Document.fundae.is_(fundae))
    if doc_type is not None:
        query = query.where(Document.doc_type == doc_type)

    rows = (await session.execute(query.order_by(Document.created_at.desc()))).all()
    items: list[RenewedDocumentItem] = []
    by_doc_type: dict[str, int] = {}

    for document, client in rows:
        if document.payment_method is None:
            continue

        by_doc_type[document.doc_type.value] = by_doc_type.get(document.doc_type.value, 0) + 1
        items.append(
            RenewedDocumentItem(
                document_id=document.id,
                client_id=client.id,
                client_name=client.full_name,
                client_nif=client.nif,
                company=client.company,
                doc_type=document.doc_type,
                expiry_date=document.expiry_date,
                payment_method=document.payment_method,
                fundae=document.fundae,
                fundae_payment_type=document.fundae_payment_type,
                operation_number=document.operation_number,
                created_at=document.created_at,
            )
        )

    return RenewedDocumentsReport(
        year=selected_year,
        payment_method=payment_method,
        fundae=fundae,
        doc_type=doc_type,
        total=len(items),
        by_doc_type=by_doc_type,
        items=items,
    )
