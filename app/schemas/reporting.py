from datetime import date, datetime

from pydantic import BaseModel

from app.models.document import DocumentType, FundaePaymentType, PaymentMethod


class DashboardSummary(BaseModel):
    due_in_30_days: int
    due_in_60_days: int
    due_in_90_days: int
    documents_total: int
    alerts_total: int
    alerts_due_today_or_older: int


class RenewedDocumentItem(BaseModel):
    document_id: int
    client_id: int
    client_name: str
    client_nif: str
    company: str | None = None
    doc_type: DocumentType
    expiry_date: date | None = None
    payment_method: PaymentMethod
    fundae: bool = False
    fundae_payment_type: FundaePaymentType | None = None
    operation_number: str | None = None
    created_at: datetime


class RenewedDocumentsReport(BaseModel):
    year: int
    payment_method: PaymentMethod | None = None
    fundae: bool | None = None
    doc_type: DocumentType | None = None
    total: int
    by_doc_type: dict[str, int]
    items: list[RenewedDocumentItem]
