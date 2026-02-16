from pathlib import Path

from fastapi import UploadFile

BASE_DIR = Path("storage")
CLIENTS_DIR = BASE_DIR / "clientes"
DOCUMENTS_DIR = BASE_DIR / "documentos"


def _safe_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_")


def _suffix(upload: UploadFile, default: str = ".bin") -> str:
    name = upload.filename or ""
    ext = Path(name).suffix.lower()
    return ext or default


def save_client_photo(nif: str, upload: UploadFile) -> str:
    safe_nif = _safe_token(nif)
    ext = _suffix(upload, default=".jpg")

    target_dir = CLIENTS_DIR / safe_nif
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{safe_nif}_foto_cliente{ext}"
    with target_path.open("wb") as output:
        output.write(upload.file.read())

    return str(target_path.as_posix())


def save_document_pdf(nif: str, doc_type: str, upload: UploadFile) -> str:
    safe_nif = _safe_token(nif)
    safe_type = _safe_token(doc_type)
    ext = _suffix(upload, default=".pdf")

    target_dir = DOCUMENTS_DIR / safe_nif / safe_type
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{safe_nif}_{safe_type}{ext}"
    with target_path.open("wb") as output:
        output.write(upload.file.read())

    return str(target_path.as_posix())
