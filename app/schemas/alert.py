from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AlertBase(BaseModel):
    client_id: int
    document_id: int | None = None
    expiry_date: date
    alert_date: date


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    client_id: int | None = None
    document_id: int | None = None
    expiry_date: date | None = None
    alert_date: date | None = None


class AlertRead(AlertBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
