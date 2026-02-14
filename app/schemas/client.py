from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClientBase(BaseModel):
    full_name: str
    company: str | None = None
    photo_path: str | None = None
    nif: str
    phone: str
    email: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    full_name: str | None = None
    company: str | None = None
    photo_path: str | None = None
    nif: str | None = None
    phone: str | None = None
    email: str | None = None


class ClientRead(ClientBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
