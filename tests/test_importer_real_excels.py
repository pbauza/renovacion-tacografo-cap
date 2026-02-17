from datetime import date
from pathlib import Path

from app.services.importer_service import SpreadsheetImporter


def test_import_cap_real_excel_generates_cap_and_driving_license_rows():
    importer = SpreadsheetImporter()
    rows = importer.import_file(Path("static/samples/CAP 2025.xlsx"))
    data_rows = [row.data for row in rows]

    cap_rows = [row for row in data_rows if row.get("document_type") == "cap"]
    license_rows = [row for row in data_rows if row.get("document_type") == "driving_license"]

    assert cap_rows
    assert license_rows

    cap_with_fundae = next(row for row in cap_rows if row.get("nif") == "29081084E")
    assert cap_with_fundae["course_number"] == "379476"
    assert cap_with_fundae["issue_date"] == date(2025, 12, 15)
    assert cap_with_fundae["expiry_date"] == date(2030, 12, 15)
    assert cap_with_fundae["fundae"] is True
    assert cap_with_fundae["phone"] == "671513200"

    cap_with_non_numeric_phone = next(row for row in cap_rows if row.get("nif") == "44326036E")
    assert cap_with_non_numeric_phone["phone"] in {"", None}

    c_d_license = next(row for row in license_rows if row.get("nif") == "X0724360K")
    assert c_d_license["flag_permiso_c"] is True
    assert c_d_license["flag_permiso_d"] is True
    assert c_d_license.get("issue_date") is None
    assert c_d_license.get("expiry_date") is None


def test_import_tarjetas_real_excel_generates_tachograph_and_apodera_rows():
    importer = SpreadsheetImporter()
    rows = importer.import_file(Path("static/samples/TARJETAS 2025.xlsx"))
    data_rows = [row.data for row in rows]

    tachograph_rows = [row for row in data_rows if row.get("document_type") == "tachograph_card"]
    power_rows = [row for row in data_rows if row.get("document_type") == "power_of_attorney"]

    assert tachograph_rows
    assert power_rows

    conductor_tachograph = next(row for row in tachograph_rows if row.get("nif") == "41516660G")
    assert conductor_tachograph["issue_date"] == date(2025, 1, 17)
    assert conductor_tachograph["expiry_date"] == date(2030, 1, 17)

    empresa_tachograph = next(row for row in tachograph_rows if row.get("nif") == "A07424393")
    assert empresa_tachograph["issue_date"] == date(2025, 9, 18)
    assert empresa_tachograph["expiry_date"] == date(2030, 9, 18)

    empresa_apodera = next(row for row in power_rows if row.get("nif") == "A07424393")
    assert empresa_apodera["flag_fran"] is True
    assert empresa_apodera["expiry_fran"] == date(2030, 9, 18)


def test_import_cap_skips_date_subtable_header_rows(tmp_path):
    from openpyxl import Workbook

    file_path = tmp_path / "CAP 2025.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Hoja2"

    sheet.append(["09-10-11-12-13-16-17 ENERO ONLINE (DNI)", None, None, "DNI", None, None, None, None, None])
    sheet.append([1, "CONDUCTOR PRUEBA", None, "12345678Z", 379999, "EMPRESA TEST", 600123123, "NO", "C"])
    workbook.save(file_path)

    importer = SpreadsheetImporter()
    rows = importer.import_file(file_path)
    data_rows = [row.data for row in rows]

    assert all((row.get("nif") or "").upper() != "DNI" for row in data_rows)

    cap_row = next(row for row in data_rows if row.get("document_type") == "cap")
    assert cap_row["issue_date"] == date(2025, 1, 9)
    assert cap_row["expiry_date"] == date(2030, 1, 9)
