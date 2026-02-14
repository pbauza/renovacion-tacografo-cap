from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.models.document import DocumentType

REQUIRED_CLIENT_COLUMNS = {"full_name", "nif", "phone"}


@dataclass
class ImportedRow:
    data: dict[str, Any]
    row_number: int


@dataclass
class ImportResult:
    clients_created: int
    clients_updated: int
    documents_created: int
    errors: list[str]


class ImportValidationError(Exception):
    pass


class SpreadsheetImporter:
    SUPPORTED_SUFFIXES = {".csv", ".xlsx"}

    def import_file(
        self,
        file_path: str | Path,
        column_mapping: dict[str, str] | None = None,
    ) -> list[ImportedRow]:
        path = Path(file_path)
        if path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise ImportValidationError(f"Unsupported file type: {path.suffix}")

        rows = self._read_csv(path) if path.suffix.lower() == ".csv" else self._read_xlsx(path)
        mapped = self._apply_mapping(rows, column_mapping or {})
        self._validate_required_columns(mapped)
        return mapped

    def _read_csv(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            return [dict(row) for row in reader]

    def _read_xlsx(self, path: Path) -> list[dict[str, Any]]:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise ImportValidationError("openpyxl is required to import .xlsx files") from exc

        workbook = load_workbook(path, data_only=True)
        sheet = workbook.active
        headers: list[str] = []
        records: list[dict[str, Any]] = []

        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                headers = [str(value).strip() if value is not None else "" for value in row]
                continue

            data = {headers[col_idx]: value for col_idx, value in enumerate(row) if col_idx < len(headers) and headers[col_idx]}
            if any(v is not None and str(v).strip() != "" for v in data.values()):
                records.append(data)

        return records

    def _apply_mapping(self, rows: list[dict[str, Any]], column_mapping: dict[str, str]) -> list[ImportedRow]:
        imported: list[ImportedRow] = []
        for idx, row in enumerate(rows, start=2):
            mapped: dict[str, Any] = {}
            for source_column, value in row.items():
                target_key = column_mapping.get(source_column, source_column)
                mapped[target_key] = self._normalize_value(value)

            imported.append(ImportedRow(data=mapped, row_number=idx))

        return imported

    def _validate_required_columns(self, rows: list[ImportedRow]) -> None:
        if not rows:
            raise ImportValidationError("File has no data rows")

        keys = set(rows[0].data.keys())
        missing = REQUIRED_CLIENT_COLUMNS - keys
        if missing:
            raise ImportValidationError(f"Missing required columns: {', '.join(sorted(missing))}")

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            return value
        return value


def parse_document_type(value: Any) -> DocumentType | None:
    if not value:
        return None

    token = str(value).strip().lower()
    aliases = {
        "dni": DocumentType.DNI,
        "carnet": DocumentType.DRIVING_LICENSE,
        "driving_license": DocumentType.DRIVING_LICENSE,
        "cap": DocumentType.CAP,
        "tachograph": DocumentType.TACHOGRAPH_CARD,
        "tachograph_card": DocumentType.TACHOGRAPH_CARD,
        "power_of_attorney": DocumentType.POWER_OF_ATTORNEY,
        "other": DocumentType.OTHER,
    }
    return aliases.get(token)


def to_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        token = value.strip().lower()
        return token in {"1", "true", "yes", "y", "si", "s"}
    return False
