from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentType


class DocumentBase(BaseModel):
    client_id: int
    doc_type: DocumentType
    expiry_date: date | None = None
    issue_date: date | None = None
    birth_date: date | None = None
    address: str | None = None
    pdf_path: str | None = None
    course_number: str | None = None
    flag_fran: bool = False
    flag_ciusaba: bool = False
    expiry_fran: date | None = None
    expiry_ciusaba: date | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    client_id: int | None = None
    doc_type: DocumentType | None = None
    expiry_date: date | None = None
    issue_date: date | None = None
    birth_date: date | None = None
    address: str | None = None
    pdf_path: str | None = None
    course_number: str | None = None
    flag_fran: bool | None = None
    flag_ciusaba: bool | None = None
    expiry_fran: date | None = None
    expiry_ciusaba: date | None = None


class DocumentRead(DocumentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
