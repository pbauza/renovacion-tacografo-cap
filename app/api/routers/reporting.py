from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.document import Document
from app.schemas.reporting import DashboardSummary

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
