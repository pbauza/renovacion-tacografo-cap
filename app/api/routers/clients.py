from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import and_, exists, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.alert import Alert
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.services.audit_log_service import log_event
from app.services.storage_service import save_client_photo

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Client:
    existing = await session.scalar(select(Client).where(Client.nif == payload.nif))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client with this NIF already exists")

    client = Client(**payload.model_dump())
    session.add(client)
    await session.commit()
    await session.refresh(client)
    log_event("create_client", f"client_id={client.id}, nif={client.nif}")
    return client


@router.get("", response_model=list[ClientRead])
async def list_clients(
    q: str | None = Query(default=None),
    full_name: str | None = Query(default=None),
    nif: str | None = Query(default=None),
    company: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    status_color: str | None = Query(default=None, description="green|yellow|red"),
    session: AsyncSession = Depends(get_db_session),
) -> list[Client]:
    query = select(Client)

    if q:
        like = f"%{q}%"
        query = query.where(
            or_(
                Client.full_name.ilike(like),
                Client.nif.ilike(like),
                Client.company.ilike(like),
                Client.phone.ilike(like),
            )
        )

    if full_name:
        query = query.where(Client.full_name.ilike(f"%{full_name}%"))
    if nif:
        query = query.where(Client.nif.ilike(f"%{nif}%"))
    if company:
        query = query.where(Client.company.ilike(f"%{company}%"))
    if phone:
        query = query.where(Client.phone.ilike(f"%{phone}%"))

    today = date.today()
    if status_color == "red":
        query = query.where(exists(select(Alert.id).where(and_(Alert.client_id == Client.id, Alert.alert_date <= today))))
    elif status_color == "yellow":
        query = query.where(
            exists(select(Alert.id).where(and_(Alert.client_id == Client.id, Alert.alert_date > today)))
        )
    elif status_color == "green":
        query = query.where(not_(exists(select(Alert.id).where(Alert.client_id == Client.id))))

    query = query.order_by(Client.created_at.desc())
    result = await session.scalars(query)
    return list(result)


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(client_id: int, session: AsyncSession = Depends(get_db_session)) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    updates = payload.model_dump(exclude_unset=True)
    if "nif" in updates:
        existing = await session.scalar(select(Client).where(Client.nif == updates["nif"], Client.id != client_id))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client with this NIF already exists")

    for field, value in updates.items():
        setattr(client, field, value)

    await session.commit()
    await session.refresh(client)
    log_event("update_client", f"client_id={client.id}")
    return client


@router.post("/{client_id}/photo", response_model=ClientRead)
async def upload_client_photo(
    client_id: int,
    photo: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if not photo.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    content_type = (photo.content_type or "").lower()
    ext = Path(photo.filename).suffix.lower()
    allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
    is_image = content_type.startswith("image/") or ext in allowed_image_exts
    is_pdf = content_type == "application/pdf" or ext == ".pdf"
    if not (is_image or is_pdf):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image or PDF files are allowed")

    stored_path = save_client_photo(client.nif, photo)
    client.photo_path = stored_path

    await session.commit()
    await session.refresh(client)
    log_event("upload_client_photo", f"client_id={client.id}, file={stored_path}")
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: int, session: AsyncSession = Depends(get_db_session)) -> Response:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    await session.delete(client)
    await session.commit()
    log_event("delete_client", f"client_id={client_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
