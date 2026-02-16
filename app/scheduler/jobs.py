from __future__ import annotations

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.document import Document, DocumentType
from app.services.alert_service import calculate_alert_date

ALERT_WINDOWS = {30, 60, 90}


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


async def create_deadline_alerts(session: AsyncSession) -> int:
    """Create alerts for documents expiring in 30/60/90 days."""
    today = date.today()

    documents = list(await session.scalars(select(Document)))
    created = 0

    for document in documents:
        expiries = _collect_document_expiry_dates(document)
        if not expiries:
            continue

        for expiry_date in expiries:
            days_until_due = (expiry_date - today).days
            if days_until_due not in ALERT_WINDOWS:
                continue

            existing_alert = await session.scalar(
                select(Alert).where(
                    and_(
                        Alert.client_id == document.client_id,
                        Alert.document_id == document.id,
                        Alert.expiry_date == expiry_date,
                    )
                )
            )
            if existing_alert:
                continue

            session.add(
                Alert(
                    client_id=document.client_id,
                    document_id=document.id,
                    expiry_date=expiry_date,
                    alert_date=calculate_alert_date(expiry_date),
                )
            )
            created += 1

    if created:
        await session.commit()

    return created
