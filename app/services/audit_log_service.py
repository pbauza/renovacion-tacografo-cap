from datetime import datetime
from pathlib import Path

LOG_DIR = Path("storage/logs")
LOG_FILE = LOG_DIR / "app.log"


def log_event(action: str, details: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp}] {action}: {details}\n")


def read_recent_logs(limit: int = 200) -> list[str]:
    if not LOG_FILE.exists():
        return []

    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return lines[-limit:]
