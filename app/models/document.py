import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentType(str, enum.Enum):
    DNI = "dni"
    DRIVING_LICENSE = "driving_license"
    CAP = "cap"
    TACHOGRAPH_CARD = "tachograph_card"
    POWER_OF_ATTORNEY = "power_of_attorney"
    OTHER = "other"


class PaymentMethod(str, enum.Enum):
    EFECTIVO = "efectivo"
    VISA = "visa"
    EMPRESA = "empresa"


class FundaePaymentType(str, enum.Enum):
    RECIBO = "recibo"
    TRANSFERENCIA = "transferencia"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type_enum"),
        nullable=False,
        index=True,
    )

    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    course_number: Mapped[str | None] = mapped_column(String(128), nullable=True)

    renewed_with_us: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum"),
        nullable=True,
    )
    fundae: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fundae_payment_type: Mapped[FundaePaymentType | None] = mapped_column(
        Enum(FundaePaymentType, name="fundae_payment_type_enum"),
        nullable=True,
    )
    operation_number: Mapped[str | None] = mapped_column(String(128), nullable=True)

    flag_fran: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_ciusaba: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expiry_fran: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_ciusaba: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    client = relationship("Client", back_populates="documents")
    alerts = relationship("Alert", back_populates="document", cascade="all, delete-orphan")
