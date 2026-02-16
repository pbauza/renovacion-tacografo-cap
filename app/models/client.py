from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nif: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    documents = relationship("Document", back_populates="client", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="client", cascade="all, delete-orphan")
