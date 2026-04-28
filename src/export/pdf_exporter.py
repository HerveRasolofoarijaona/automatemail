import logging
import csv
import zipfile
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER

# ── Colors ─────────────────────────────────────────────────────
MVOLA_GREEN  = colors.HexColor("#00A651")
MVOLA_YELLOW = colors.HexColor("#FFD700")
MVOLA_DARK   = colors.HexColor("#1A1A1A")
MVOLA_GREY   = colors.HexColor("#F5F5F5")
MVOLA_BORDER = colors.HexColor("#DDDDDD")
TEXT_MUTED   = colors.HexColor("#666666")

SELECTED_COLS = [
    "DATE_TRANS", "N_TRANSACTION", "INITIATOR", "TRANS_TYPE",
    "AMOUNT", "DEBTOR", "CREDITOR", "DETAILS1", "DETAILS2",
]

LABELS = {
    "DATE_TRANS": "Date / Heure",
    "N_TRANSACTION": "N° Transaction",
    "INITIATOR": "Initiateur",
    "TRANS_TYPE": "Type",
    "AMOUNT": "Montant",
    "DEBTOR": "Débiteur",
    "CREDITOR": "Créditeur",
    "DETAILS1": "Détails 1",
    "DETAILS2": "Détails 2",
}

AMOUNT_COLS = {"AMOUNT"}
WATERMARK_LOGO = os.getenv("WATERMARK_LOGO")

# ── Formatters ─────────────────────────────────────────────────
def _fmt_amount(val):
    try:
        return f"{float(val):,.0f} Ar".replace(",", " ")
    except:
        return val

def _fmt_date(val):
    try:
        return datetime.fromisoformat(val.split(".")[0]).strftime("%d/%m/%Y %H:%M")
    except:
        return val

# ── Watermark (FIX) ────────────────────────────────────────────
def _draw_watermark(canvas, doc):
    if WATERMARK_LOGO and Path(WATERMARK_LOGO).exists():
        w, h = landscape(A4)
        logo = ImageReader(WATERMARK_LOGO)

        canvas.saveState()
        canvas.setFillAlpha(0.08)

        canvas.translate(w / 2, h / 2)
        canvas.rotate(45)

        canvas.drawImage(
            logo,
            -120, -120,
            width=240,
            height=240,
            preserveAspectRatio=True,
            mask="auto"
        )

        canvas.restoreState()

# ── Header/Footer ──────────────────────────────────────────────
def _on_page(canvas, doc):
    canvas.saveState()
    w, h = landscape(A4)

    canvas.setFillColor(MVOLA_GREEN)
    canvas.rect(0, h - 8 * mm, w, 8 * mm, fill=1, stroke=0)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.white)
    canvas.drawString(15 * mm, h - 6 * mm, "MVola")

    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 15 * mm, h - 5.5 * mm, f"Page {doc.page}")

    canvas.setStrokeColor(MVOLA_YELLOW)
    canvas.setLineWidth(2)
    canvas.line(0, 10 * mm, w, 10 * mm)

    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(
        w / 2, 6 * mm,
        "À conserver pour vos archives — Service Client MVola : 807"
    )

    canvas.restoreState()

# ── Table style ────────────────────────────────────────────────
def _table_style(headers):
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), MVOLA_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MVOLA_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.3, MVOLA_BORDER),
    ]

    if "AMOUNT" in headers:
        idx = headers.index("AMOUNT")
        style.append(("ALIGN", (idx, 1), (idx, -1), "RIGHT"))

    return TableStyle(style)

# ── Generate PDF ───────────────────────────────────────────────
def generate_pdf_for_day(
    day: str,
    rows: list[dict],
    filename_prefix: str,
    report_type: str,
    output_dir: Path,
    account_number: str = "",
):
    if not rows:
        raise ValueError("Aucune donnée")

    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / f"{filename_prefix}_{day}.pdf"

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    headers = [h for h in SELECTED_COLS if h in rows[0]]
    page_width = landscape(A4)[0] - 30 * mm

    col_widths = []
    for h in headers:
        if h == "DATE_TRANS":
            col_widths.append(35 * mm)
        elif h == "AMOUNT":
            col_widths.append(25 * mm)
        else:
            col_widths.append(page_width / len(headers))

    cell_style = ParagraphStyle("cell", fontSize=7)
    hdr_style = ParagraphStyle("hdr", fontSize=7, textColor=colors.white)

    # ── HEADER INFO ─────────────────────────
    elements = []

    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(f"<b>Compte :</b> {account_number}", cell_style))
    elements.append(Paragraph(f"<b>Type :</b> {report_type}", cell_style))
    elements.append(Paragraph(f"<b>Date :</b> {day}", cell_style))
    elements.append(Spacer(1, 5 * mm))

    # ── TABLE ───────────────────────────────
    data = [[Paragraph(LABELS.get(h, h), hdr_style) for h in headers]]

    for r in rows:
        row_data = []
        for h in headers:
            val = str(r.get(h, ""))
            if h == "DATE_TRANS":
                val = _fmt_date(val)
            elif h in AMOUNT_COLS:
                val = _fmt_amount(val)
            row_data.append(Paragraph(val, cell_style))
        data.append(row_data)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style(headers))

    elements.append(table)

    doc.build(
        elements,
        onFirstPage=_on_page,
        onLaterPages=_on_page,
        onFirstPageEnd=_draw_watermark,
        onLaterPagesEnd=_draw_watermark,
    )

    return filepath

# ── CSV → PDFs + ZIP ───────────────────────────────────────────

def generate_pdfs_from_csv(
        csv_path: str,
        filename_prefix: str,
        report_type: str,
        output_base_dir: str = "outputs",
        account_number: str = "",
        date_col: str = "DATE_TRANS",
        csv_delimiter: str = ";",
    ):
        logger = logging.getLogger("send_report")
        logging.basicConfig(level=logging.INFO)

        # ── Read CSV ───────────────────────────
        with open(csv_path, encoding="utf-8") as f:
            data = list(csv.DictReader(f, delimiter=csv_delimiter))

        if not data:
            raise ValueError(f"CSV vide : {csv_path}")

        logger.info(f"{len(data)} lignes chargées")

        # ── Group by day ───────────────────────
        grouped = defaultdict(list)
        for row in data:
            grouped[row[date_col][:10]].append(row)

        logger.info(f"{len(grouped)} jour(s) détecté(s)")

        # ── Output dir ─────────────────────────
        output_dir = Path(output_base_dir) / report_type
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_pdfs = []

        # ── Generate PDFs ──────────────────────
        for day in sorted(grouped.keys()):
            pdf_path = generate_pdf_for_day(
                day=day,
                rows=grouped[day],
                filename_prefix=filename_prefix,
                report_type=report_type,
                output_dir=output_dir,
                account_number=account_number,
            )
            generated_pdfs.append(pdf_path)

        # ── ZIP ────────────────────────────────
        zip_path = output_dir / f"{filename_prefix}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for pdf in generated_pdfs:
                z.write(pdf, pdf.name)

        logger.info(f"ZIP généré : {zip_path}")

        return zip_path


# ── Run ────────────────────────────────────────────────────────
if __name__ == "__main__":
    zip_file = generate_pdfs_from_csv("input.csv")
    print(zip_file)