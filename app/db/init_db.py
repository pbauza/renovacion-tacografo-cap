from datetime import datetime
from pathlib import Path
import os
import sqlite3
import zipfile

from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models import Alert, Client, Document  # noqa: F401
from app.services.audit_log_service import log_event

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
        "flag_permiso_c",
        "flag_permiso_d",
        "expiry_fran",
        "expiry_ciusaba",
        "created_at",
    },
    "alerts": {"id", "client_id", "document_id", "expiry_date", "alert_date", "created_at"},
}


def _resolve_sqlite_path_from_url(database_url: str) -> Path | None:
    try:
        parsed = make_url(database_url)
    except Exception:
        return None

    if parsed.get_backend_name() != "sqlite":
        return None

    raw_path = parsed.database
    if not raw_path or raw_path == ":memory:":
        return None

    # SQLAlchemy may expose Windows absolute paths as /C:/...
    if os.name == "nt" and len(raw_path) > 2 and raw_path[0] == "/" and raw_path[2] == ":":
        raw_path = raw_path[1:]

    db_path = Path(raw_path).expanduser()
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    return db_path


def _cleanup_old_backups(backup_dir: Path, pattern: str, keep_last: int) -> None:
    if keep_last <= 0:
        return

    backups = sorted(backup_dir.glob(pattern), key=lambda p: p.name, reverse=True)
    for old_file in backups[keep_last:]:
        try:
            old_file.unlink()
        except OSError:
            continue


def create_sqlite_startup_backup() -> Path | None:
    if not settings.backup_on_startup:
        return None

    db_path = _resolve_sqlite_path_from_url(settings.database_url)
    if db_path is None or not db_path.exists():
        return None

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_suffix = db_path.suffix or ".db"
    backup_path = backup_dir / f"{db_path.stem}_{timestamp}{db_suffix}"

    try:
        with sqlite3.connect(str(db_path), timeout=30) as source:
            with sqlite3.connect(str(backup_path), timeout=30) as target:
                source.backup(target)
        _cleanup_old_backups(backup_dir, f"{db_path.stem}_*{db_suffix}", settings.backup_keep_last)
        log_event("startup_backup", f"source={db_path.as_posix()}, backup={backup_path.as_posix()}")
        return backup_path
    except Exception as exc:
        log_event("startup_backup_error", f"source={db_path.as_posix()}, error={exc}")
        return None


def create_storage_startup_backup() -> Path | None:
    if not settings.storage_backup_on_startup:
        return None

    storage_dir = Path("storage")
    if not storage_dir.exists() or not storage_dir.is_dir():
        return None

    backup_dir = storage_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"storage_{timestamp}.zip"

    try:
        with zipfile.ZipFile(backup_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in storage_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                try:
                    file_path.relative_to(backup_dir)
                    continue
                except ValueError:
                    pass
                archive.write(file_path, arcname=file_path.relative_to(storage_dir).as_posix())
        _cleanup_old_backups(backup_dir, "storage_*.zip", settings.storage_backup_keep_last)
        log_event("startup_storage_backup", f"source={storage_dir.as_posix()}, backup={backup_path.as_posix()}")
        return backup_path
    except Exception as exc:
        log_event("startup_storage_backup_error", f"source={storage_dir.as_posix()}, error={exc}")
        return None


async def _sqlite_schema_mismatch() -> bool:
    async with engine.connect() as conn:
        for table, expected in EXPECTED_COLUMNS.items():
            result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
            columns = {row[1] for row in result.fetchall()}
            if columns and not expected.issubset(columns):
                return True
    return False


async def init_db() -> None:
    create_sqlite_startup_backup()
    create_storage_startup_backup()

    should_reset = settings.reset_db_on_startup
    is_sqlite = engine.url.get_backend_name() == "sqlite"
    if not should_reset and is_sqlite and settings.auto_reset_sqlite_on_schema_mismatch:
        should_reset = await _sqlite_schema_mismatch()

    async with engine.begin() as conn:
        if should_reset:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
