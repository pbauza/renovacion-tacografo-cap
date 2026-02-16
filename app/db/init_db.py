from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models import Alert, Client, Document  # noqa: F401

settings = get_settings()

EXPECTED_COLUMNS = {
    "clients": {"id", "full_name", "company", "photo_path", "nif", "phone", "email", "created_at"},
    "documents": {
        "id",
        "client_id",
        "doc_type",
        "expiry_date",
        "issue_date",
        "birth_date",
        "address",
        "pdf_path",
        "course_number",
        "renewed_with_us",
        "payment_method",
        "fundae",
        "fundae_payment_type",
        "operation_number",
        "flag_fran",
        "flag_ciusaba",
        "expiry_fran",
        "expiry_ciusaba",
        "created_at",
    },
    "alerts": {"id", "client_id", "document_id", "expiry_date", "alert_date", "created_at"},
}


async def _sqlite_schema_mismatch() -> bool:
    async with engine.connect() as conn:
        for table, expected in EXPECTED_COLUMNS.items():
            result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
            columns = {row[1] for row in result.fetchall()}
            if columns and not expected.issubset(columns):
                return True
    return False


async def init_db() -> None:
    should_reset = settings.reset_db_on_startup
    is_sqlite = engine.url.get_backend_name() == "sqlite"
    if not should_reset and is_sqlite and settings.auto_reset_sqlite_on_schema_mismatch:
        should_reset = await _sqlite_schema_mismatch()

    async with engine.begin() as conn:
        if should_reset:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
