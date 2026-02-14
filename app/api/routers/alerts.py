from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.client import Client
from app.models.document import Document
from app.schemas.alert import AlertCreate, AlertRead, AlertUpdate
from app.services.audit_log_service import log_event

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(payload: AlertCreate, session: AsyncSession = Depends(get_db_session)) -> Alert:
    client = await session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if payload.document_id is not None:
        document = await session.get(Document, payload.document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    alert = Alert(**payload.model_dump())
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    log_event("create_alert", f"alert_id={alert.id}, client_id={alert.client_id}")
    return alert


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    window_days: int | None = Query(default=None, description="30|60|90"),
    urgent_only: bool = Query(default=False),
    missing_documents: bool = Query(default=False),
    client_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[Alert]:
    query = select(Alert)

    today = date.today()
    if window_days in {30, 60, 90}:
        query = query.where(Alert.expiry_date <= today + timedelta(days=window_days), Alert.expiry_date >= today)

    if urgent_only:
        query = query.where(Alert.alert_date <= today)

    if client_id is not None:
        query = query.where(Alert.client_id == client_id)

    if missing_documents:
        query = query.join(Document, Document.id == Alert.document_id, isouter=True).where(
            Document.pdf_path.is_(None)
        )

    result = await session.scalars(query.order_by(Alert.alert_date.asc(), Alert.created_at.desc()))
    return list(result)


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(alert_id: int, session: AsyncSession = Depends(get_db_session)) -> Alert:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertRead)
async def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Alert:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    updates = payload.model_dump(exclude_unset=True)
    if "client_id" in updates:
        client = await session.get(Client, updates["client_id"])
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if "document_id" in updates and updates["document_id"] is not None:
        document = await session.get(Document, updates["document_id"])
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    for field, value in updates.items():
        setattr(alert, field, value)

    await session.commit()
    await session.refresh(alert)
    log_event("update_alert", f"alert_id={alert.id}")
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: int, session: AsyncSession = Depends(get_db_session)) -> Response:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    await session.delete(alert)
    await session.commit()
    log_event("delete_alert", f"alert_id={alert_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
