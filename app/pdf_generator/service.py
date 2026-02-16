from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfgen.canvas import Canvas

from app.core.app_config import get_app_json_config

try:
    from PIL import Image
except Exception:  # noqa: BLE001
    Image = None


class PdfGeneratorService:
    """Service for assembling client and bulk PDF outputs."""

    def generate_bundle(self, output_path: str | Path, ordered_files: list[str | Path]) -> Path:
        target = Path(output_path)
        if not ordered_files:
            raise ValueError("ordered_files no puede estar vacio")

        target.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        for source in ordered_files:
            src = Path(source)
            if src.exists() and src.suffix.lower() == ".pdf":
                writer.append(str(src))

        with target.open("wb") as output:
            writer.write(output)
        return target

    def default_output_name(self, prefix: str) -> str:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{stamp}.pdf"

    def generate_client_report(
        self,
        output_path: str | Path,
        *,
        client: Any,
        documents: list[Any],
        alerts: list[Any],
    ) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        generated_at = datetime.utcnow()
        app_json = get_app_json_config()
        logo_path = Path(app_json.ui.logo_path.lstrip("/")) if app_json.ui.logo_path.startswith("/") else Path(app_json.ui.logo_path)
        app_name = app_json.pdf.report_title
        contact_email = app_json.pdf.contact_email
        contact_phone = app_json.pdf.contact_phone

        doc, styles, on_page = _build_base_template(
            output_path=target,
            generated_at=generated_at,
            logo_path=logo_path if logo_path.exists() else None,
            app_name=app_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )

        story: list[Any] = []
        story.extend(
            self._build_title_page(
                styles=styles,
                generated_at=generated_at,
                client=client,
                logo_path=logo_path if logo_path.exists() else None,
                organization_name=app_json.pdf.organization_name or app_json.app_name,
            )
        )

        if len(documents) + len(alerts) > 6:
            story.extend(self._build_table_of_contents(styles=styles))

        story.extend(self._build_client_data_section(styles=styles, client=client))
        story.extend(self._build_documents_summary_section(styles=styles, documents=documents))
        story.extend(self._build_documents_detail_section(styles=styles, documents=documents))
        story.extend(self._build_alerts_summary_section(styles=styles, alerts=alerts))

        canvas_maker = lambda *args, **kwargs: NumberedCanvas(
            *args,
            on_page=on_page,
            contact_email=contact_email,
            contact_phone=contact_phone,
            **kwargs,
        )
        doc.build(story, canvasmaker=canvas_maker)

        photo_pdf_path = _resolve_existing_path(getattr(client, "photo_path", None))
        if photo_pdf_path and photo_pdf_path.suffix.lower() == ".pdf":
            writer = PdfWriter()
            writer.append(str(target))
            writer.append(str(photo_pdf_path))
            with target.open("wb") as out:
                writer.write(out)

        return target

    def _build_title_page(
        self,
        *,
        styles: dict[str, ParagraphStyle],
        generated_at: datetime,
        client: Any,
        logo_path: Path | None,
        organization_name: str,
    ) -> list[Any]:
        story: list[Any] = []
        story.append(Spacer(1, 45 * mm))
        story.append(Paragraph("INFORME DE RENOVACIONES DEL CLIENTE", styles["title"]))
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(organization_name, styles["subtitle"]))
        story.append(Spacer(1, 14 * mm))

        info_rows = [
            ["Nombre del cliente", str(getattr(client, "full_name", "") or "-")],
            ["ID de cliente", str(getattr(client, "id", "") or "-")],
            ["NIF", str(getattr(client, "nif", "") or "-")],
            ["Telefono", str(getattr(client, "phone", "") or "-")],
            ["Empresa", str(getattr(client, "company", "") or "-")],
            ["Fecha del informe", _fmt_official_datetime(generated_at)],
        ]
        table = _styled_key_value_table(info_rows, width=165 * mm)
        story.append(table)
        story.append(Spacer(1, 8 * mm))

        photo_path = _resolve_existing_path(getattr(client, "photo_path", None))
        if photo_path:
            image = _build_thumbnail(photo_path, max_w=70 * mm, max_h=70 * mm)
            if image:
                story.append(Paragraph("Foto del cliente", styles["h3"]))
                story.append(Spacer(1, 2 * mm))
                story.append(image)

        story.append(PageBreak())
        return story

    def _build_table_of_contents(self, *, styles: dict[str, ParagraphStyle]) -> list[Any]:
        story: list[Any] = []
        story.append(Paragraph("INDICE DE CONTENIDOS", styles["h1"]))
        story.append(Spacer(1, 3 * mm))
        entries = [
            "1. Datos del cliente",
            "2. Resumen de documentos",
            "3. Detalle de documentos",
            "4. Resumen de alertas",
        ]
        for entry in entries:
            story.append(Paragraph(entry, styles["body"]))
            story.append(Spacer(1, 1.5 * mm))
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("La numeracion de pagina se muestra en el pie de cada hoja.", styles["muted"]))
        story.append(PageBreak())
        return story

    def _build_client_data_section(self, *, styles: dict[str, ParagraphStyle], client: Any) -> list[Any]:
        rows = [
            ["ID de cliente", str(getattr(client, "id", "") or "-")],
            ["Nombre completo", str(getattr(client, "full_name", "") or "-")],
            ["NIF", str(getattr(client, "nif", "") or "-")],
            ["Empresa", str(getattr(client, "company", "") or "-")],
            ["Telefono", str(getattr(client, "phone", "") or "-")],
            ["Email", str(getattr(client, "email", "") or "-")],
            ["Fecha de alta", _fmt_official_datetime(getattr(client, "created_at", None))],
        ]
        story = [Paragraph("1. DATOS DEL CLIENTE", styles["h1"]), Spacer(1, 3 * mm), _styled_key_value_table(rows), Spacer(1, 8 * mm)]
        return story

    def _build_documents_summary_section(self, *, styles: dict[str, ParagraphStyle], documents: list[Any]) -> list[Any]:
        story: list[Any] = [Paragraph("2. RESUMEN DE DOCUMENTOS", styles["h1"]), Spacer(1, 3 * mm)]
        if not documents:
            story.append(Paragraph("No hay documentos registrados.", styles["body"]))
            story.append(Spacer(1, 8 * mm))
            return story

        header = ["ID", "Tipo", "Caducidad", "Estado", "PDF"]
        rows = [header]
        for doc in documents:
            exp = getattr(doc, "expiry_date", None)
            status = _expiration_status(exp)
            rows.append(
                [
                    str(getattr(doc, "id", "")),
                    _human_doc_type(getattr(getattr(doc, "doc_type", None), "value", getattr(doc, "doc_type", ""))),
                    _fmt_official_date(exp),
                    status,
                    "Si" if getattr(doc, "pdf_path", None) else "No",
                ]
            )

        table = Table(rows, colWidths=[18 * mm, 44 * mm, 36 * mm, 30 * mm, 16 * mm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 8 * mm))
        return story

    def _build_documents_detail_section(self, *, styles: dict[str, ParagraphStyle], documents: list[Any]) -> list[Any]:
        story: list[Any] = [Paragraph("3. DETALLE DE DOCUMENTOS", styles["h1"]), Spacer(1, 3 * mm)]
        if not documents:
            story.append(Paragraph("No hay detalle de documentos disponible.", styles["body"]))
            story.append(Spacer(1, 8 * mm))
            return story

        for doc in documents:
            story.append(
                Paragraph(
                    f"Documento {getattr(doc, 'id', '-')} - "
                    f"{_human_doc_type(getattr(getattr(doc, 'doc_type', None), 'value', getattr(doc, 'doc_type', '')))}",
                    styles["h2"],
                )
            )
            story.append(Spacer(1, 1.5 * mm))

            fields = [
                ["ID de cliente", str(getattr(doc, "client_id", "") or "-")],
                ["Fecha de caducidad", _fmt_official_date(getattr(doc, "expiry_date", None))],
                ["Fecha de emision", _fmt_official_date(getattr(doc, "issue_date", None))],
                ["Fecha de nacimiento", _fmt_official_date(getattr(doc, "birth_date", None))],
                ["Direccion", str(getattr(doc, "address", "") or "-")],
                ["Numero de curso", str(getattr(doc, "course_number", "") or "-")],
                ["Apoderamiento Fran", "Si" if bool(getattr(doc, "flag_fran", False)) else "No"],
                ["Apoderamiento CIUSABA", "Si" if bool(getattr(doc, "flag_ciusaba", False)) else "No"],
                ["Caducidad FRAN", _fmt_official_date(getattr(doc, "expiry_fran", None))],
                ["Caducidad CIUSABA", _fmt_official_date(getattr(doc, "expiry_ciusaba", None))],
                ["Archivo del documento", str(getattr(doc, "pdf_path", "") or "-")],
            ]
            story.append(_styled_key_value_table(fields))

            doc_image = _build_thumbnail(_resolve_existing_path(getattr(doc, "pdf_path", None)), max_w=50 * mm, max_h=50 * mm)
            if doc_image:
                story.append(Spacer(1, 1 * mm))
                story.append(Paragraph("Miniatura del documento", styles["muted"]))
                story.append(doc_image)

            story.append(Spacer(1, 5 * mm))
        return story

    def _build_alerts_summary_section(self, *, styles: dict[str, ParagraphStyle], alerts: list[Any]) -> list[Any]:
        story: list[Any] = [Paragraph("4. RESUMEN DE ALERTAS", styles["h1"]), Spacer(1, 3 * mm)]
        if not alerts:
            story.append(Paragraph("No hay alertas disponibles para este cliente.", styles["body"]))
            return story

        header = ["ID alerta", "ID documento", "Fecha caducidad", "Fecha alerta"]
        rows = [header]
        for alert in alerts:
            rows.append(
                [
                    str(getattr(alert, "id", "") or "-"),
                    str(getattr(alert, "document_id", "") or "-"),
                    _fmt_official_date(getattr(alert, "expiry_date", None)),
                    _fmt_official_date(getattr(alert, "alert_date", None)),
                ]
            )

        table = Table(rows, colWidths=[26 * mm, 28 * mm, 44 * mm, 44 * mm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        return story


def _build_base_template(
    *,
    output_path: Path,
    generated_at: datetime,
    logo_path: Path | None,
    app_name: str,
    contact_email: str,
    contact_phone: str,
) -> tuple[SimpleDocTemplate, dict[str, ParagraphStyle], Any]:
    """Create base PDF template with official margins, typography and header/footer callback."""

    left_margin = 20 * mm
    right_margin = 20 * mm
    top_margin = 34 * mm
    bottom_margin = 22 * mm

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=app_name,
        author=get_app_json_config().app_name,
    )

    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            alignment=1,
            textColor=colors.HexColor("#0f172a"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Heading2"],
            fontName="Helvetica",
            fontSize=12,
            alignment=1,
            textColor=colors.HexColor("#334155"),
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#111827"),
            spaceAfter=3,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1f2937"),
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#334155"),
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#111827"),
        ),
        "muted": ParagraphStyle(
            "muted",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#6b7280"),
        ),
    }

    def on_page(canvas: Canvas) -> None:
        width, height = A4
        canvas.saveState()

        if logo_path and logo_path.exists():
            try:
                canvas.drawImage(str(logo_path), left_margin, height - 25 * mm, width=20 * mm, height=20 * mm, preserveAspectRatio=True, mask="auto")
            except Exception:  # noqa: BLE001
                pass

        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.drawString(left_margin + 24 * mm, height - 13 * mm, app_name)

        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(colors.HexColor("#374151"))
        canvas.drawString(left_margin + 24 * mm, height - 18 * mm, f"Generado: {_fmt_official_datetime(generated_at)}")
        canvas.setStrokeColor(colors.HexColor("#d1d5db"))
        canvas.line(left_margin, height - 27 * mm, width - right_margin, height - 27 * mm)

        canvas.restoreState()

    return doc, styles, on_page


class NumberedCanvas(Canvas):
    def __init__(self, *args: Any, on_page: Any, contact_email: str, contact_phone: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._on_page = on_page
        self._contact_email = contact_email
        self._contact_phone = contact_phone
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._on_page(self)
            self._draw_footer(total_pages)
            super().showPage()
        super().save()

    def _draw_footer(self, total_pages: int) -> None:
        width, _ = A4
        self.saveState()
        self.setStrokeColor(colors.HexColor("#d1d5db"))
        self.line(20 * mm, 17 * mm, width - 20 * mm, 17 * mm)
        self.setFillColor(colors.HexColor("#4b5563"))
        self.setFont("Helvetica", 8)
        self.drawString(20 * mm, 12 * mm, f"Contacto: {self._contact_email} | {self._contact_phone}")
        self.drawRightString(width - 20 * mm, 12 * mm, f"Pagina {self._pageNumber} / {total_pages}")
        self.restoreState()


def _styled_key_value_table(rows: list[list[str]], width: float = 170 * mm) -> Table:
    table = Table(rows, colWidths=[45 * mm, width - 45 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.2),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _build_thumbnail(path: Path | None, *, max_w: float, max_h: float) -> RLImage | None:
    if not path or not path.exists():
        return None

    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}:
        if suffix in {".jpg", ".jpeg", ".png"}:
            return RLImage(str(path), width=max_w, height=max_h)
        if Image is None:
            return None
        try:
            with Image.open(path) as img:
                rgb = img.convert("RGB")
                buffer = BytesIO()
                rgb.save(buffer, format="PNG")
                buffer.seek(0)
            return RLImage(buffer, width=max_w, height=max_h)
        except Exception:  # noqa: BLE001
            return None
    return None


def _resolve_existing_path(raw_path: Any) -> Path | None:
    if not raw_path:
        return None
    p = Path(str(raw_path))
    if p.exists():
        return p
    rel = Path(str(raw_path).lstrip("/"))
    if rel.exists():
        return rel
    return None


def _fmt_official_date(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return _format_spanish_date(value)
    try:
        parsed = datetime.fromisoformat(str(value)).date()
        return _format_spanish_date(parsed)
    except Exception:  # noqa: BLE001
        return str(value)


def _fmt_official_datetime(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())
    if isinstance(value, datetime):
        return f"{_format_spanish_date(value.date())} {value.strftime('%H:%M')}"
    try:
        parsed = datetime.fromisoformat(str(value))
        return f"{_format_spanish_date(parsed.date())} {parsed.strftime('%H:%M')}"
    except Exception:  # noqa: BLE001
        return str(value)


def _format_spanish_date(value: date) -> str:
    meses = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    return f"{value.day:02d} {meses[value.month]} {value.year}"


def _human_doc_type(raw: str) -> str:
    mapping = {
        "dni": "DNI",
        "driving_license": "Carnet de conducir",
        "cap": "CAP",
        "tachograph_card": "Tarjeta tacografo",
        "power_of_attorney": "Poder notarial",
        "other": "Otro",
    }
    return mapping.get(str(raw), str(raw))


def _expiration_status(value: Any) -> str:
    if value is None:
        return "Sin caducidad"
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        try:
            value = datetime.fromisoformat(str(value)).date()
        except Exception:  # noqa: BLE001
            return "Desconocido"
    today = date.today()
    if value < today:
        return "Caducado"
    if (value - today).days <= 90:
        return "Caduca pronto"
    return "Vigente"
