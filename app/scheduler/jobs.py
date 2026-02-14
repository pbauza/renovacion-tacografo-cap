from __future__ import annotations

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.document import Document
from app.services.alert_service import calculate_alert_date

ALERT_WINDOWS = {30, 60, 90}


async def create_deadline_alerts(session: AsyncSession) -> int:
    """Create alerts for documents expiring in 30/60/90 days."""
    today = date.today()

    documents = list(await session.scalars(select(Document).where(Document.expiry_date.is_not(None))))
    created = 0

    for document in documents:
        if document.expiry_date is None:
            continue

        days_until_due = (document.expiry_date - today).days
        if days_until_due not in ALERT_WINDOWS:
            continue

        existing_alert = await session.scalar(
            select(Alert).where(
                and_(
                    Alert.client_id == document.client_id,
                    Alert.document_id == document.id,
                    Alert.expiry_date == document.expiry_date,
                )
            )
        )
        if existing_alert:
            continue

        session.add(
            Alert(
                client_id=document.client_id,
                document_id=document.id,
                expiry_date=document.expiry_date,
                alert_date=calculate_alert_date(document.expiry_date),
            )
        )
        created += 1

    if created:
        await session.commit()

    return created
