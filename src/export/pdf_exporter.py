import logging
import csv
import zipfile
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    PageBreak,
    Spacer,
    KeepTogether,
)

import os
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# ── Brand colors ──────────────────────────────────────────────────────────────
MVOLA_GREEN  = colors.HexColor("#00A651")
MVOLA_YELLOW = colors.HexColor("#FFD700")
MVOLA_DARK   = colors.HexColor("#1A1A1A")
MVOLA_GREY   = colors.HexColor("#F5F5F5")
MVOLA_BORDER = colors.HexColor("#DDDDDD")
TEXT_MUTED   = colors.HexColor("#666666")

# ── Columns to include ────────────────────────────────────────────────────────
SELECTED_COLS = [
    "DATE_TRANS", "N_TRANSACTION", "INITIATOR", "TRANS_TYPE",
    "AMOUNT", "DEBTOR", "CREDITOR", "DETAILS1", "DETAILS2",
]
LABELS = {
    "DATE_TRANS":    "Date / Heure",
    "N_TRANSACTION": "N° Transaction",
    "INITIATOR":     "Initiateur",
    "TRANS_TYPE":    "Type",
    "AMOUNT":        "Montant",
    "DEBTOR":        "Débiteur",
    "CREDITOR":      "Créditeur",
    "DETAILS1":      "Détails 1",
    "DETAILS2":      "Détails 2",
}
AMOUNT_COLS = {"AMOUNT"}

WATERMARK_LOGO = os.getenv("WATERMARK_LOGO")


# ── Formatters ────────────────────────────────────────────────────────────────

def _fmt_amount(val: str) -> str:
    try:
        return f"{float(val):,.0f} Ar".replace(",", " ")
    except Exception:
        return val


def _fmt_date(val: str) -> str:
    """2026-02-28 18:50:47.419000  →  28/02/2026 18:50"""
    try:
        return datetime.fromisoformat(val.split(".")[0]).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return val


def _fmt_date_heading(date_str: str) -> str:
    """2026-02-28  →  Samedi 28 février 2026"""
    DAYS_FR   = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
    MONTHS_FR = ["","janvier","février","mars","avril","mai","juin",
                 "juillet","août","septembre","octobre","novembre","décembre"]
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{DAYS_FR[d.weekday()]} {d.day} {MONTHS_FR[d.month]} {d.year}"
    except Exception:
        return date_str


# ── Table style ───────────────────────────────────────────────────────────────

def _day_table_style():
    return TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  MVOLA_GREEN),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0),  7),
        ("ALIGN",          (0, 0), (-1, 0),  "CENTER"),
        ("BOTTOMPADDING",  (0, 0), (-1, 0),  5),
        ("TOPPADDING",     (0, 0), (-1, 0),  5),
        ("FONTNAME",       (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 1), (-1, -1), 7),
        ("ALIGN",          (0, 1), (-1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MVOLA_GREY]),
        ("GRID",           (0, 0), (-1, -1), 0.3, MVOLA_BORDER),
        ("BOTTOMPADDING",  (0, 1), (-1, -1), 3),
        ("TOPPADDING",     (0, 1), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 4),
    ])


# ── Single-day PDF generator ──────────────────────────────────────────────────

def generate_pdf_for_day(
    day: str,
    rows: list[dict],
    filename_prefix: str,
    report_type: str,
    output_dir: Path,
    rows_per_page: int = 50,
    account_number: str = "",
) -> Path:
    """Generate one PDF for a single day."""
    logger = logging.getLogger("send_report")

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{filename_prefix}_{day}.pdf"
    filepath = output_dir / filename
    logger.info(f"  → {filename} ({len(rows)} lignes)")

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # ── Canvas header/footer ──────────────────────────────────────────────────
    def _on_page(canvas, doc):
        canvas.saveState()
        w, h = landscape(A4)

        # ── FILIGRANE (en premier, sous tout le reste) ────────
        if WATERMARK_LOGO and Path(WATERMARK_LOGO).exists():
            logo = ImageReader(WATERMARK_LOGO)
            canvas.setFillAlpha(0.10)
            canvas.translate(w / 2, h / 2)
            canvas.rotate(45)
            canvas.drawImage(logo, -80, -80, width=160, height=160,
                            mask="auto", preserveAspectRatio=True)
            canvas.rotate(-45)
            canvas.translate(-w / 2, -h / 2)
            canvas.setFillAlpha(1.0)
        # ──────────────────────────────────────────────────────

        canvas.setFillColor(MVOLA_GREEN)
        canvas.rect(0, h - 8 * mm, w, 8 * mm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(colors.white)
        canvas.drawString(15 * mm, h - 6 * mm, "MVola")
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.drawString(15 * mm + 38, h - 5.5 * mm,
                        "1ère solution de paiement par mobile à Madagascar")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 15 * mm, h - 5.5 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(MVOLA_YELLOW)
        canvas.setLineWidth(2)
        canvas.line(0, 10 * mm, w, 10 * mm)
        canvas.setFont("Helvetica-Oblique", 7)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawCentredString(w / 2, 6 * mm,
            "À conserver pour vos archives — Service Client MVola : 807 — service.client@mvola.mg")

        canvas.restoreState()  # ← toujours en dernier

    elements = []
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    day_total = sum(float(r.get("AMOUNT", 0) or 0) for r in rows)

    # ── Page header block ─────────────────────────────────────────────────────
    elements.append(Spacer(1, 4 * mm))

    kpi_style = ParagraphStyle("kpi", fontName="Helvetica", fontSize=8,
                               textColor=TEXT_MUTED, alignment=TA_CENTER)
    title_style = ParagraphStyle("report_title", fontName="Helvetica-Bold",
                                 fontSize=16, textColor=MVOLA_DARK, spaceAfter=2)
    sub_style = ParagraphStyle("report_subtitle", fontName="Helvetica",
                               fontSize=9, textColor=TEXT_MUTED, spaceAfter=0)

    header_data = [[
        Paragraph("RAPPORT DE TRANSACTIONS", title_style),
        Paragraph(
            f"Compte : <b>{account_number or 'N/A'}</b><br/>"
            f"Type   : <b>{report_type}</b><br/>"
            f"Date   : <b>{_fmt_date_heading(day)}</b><br/>"
            f"Généré le {generated_at}",
            sub_style,
        ),
        Paragraph(
            f"Transactions du jour<br/>"
            f"<font size=18 color='#00A651'><b>{len(rows)}</b></font><br/>"
            f"<font size=8>Total : {_fmt_amount(str(day_total))}</font>",
            kpi_style,
        ),
    ]]
    header_table = Table(header_data, colWidths=["40%", "40%", "20%"])
    header_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (2, 0), (2, 0),   "CENTER"),
        ("LINEBELOW",     (0, 0), (-1, 0),  1, MVOLA_GREEN),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4 * mm))

    # ── Table ─────────────────────────────────────────────────────────────────
    headers    = [h for h in SELECTED_COLS if h in rows[0]]
    tbl_header = [LABELS.get(h, h) for h in headers]
    col_count  = len(headers)
    page_width = landscape(A4)[0] - 30 * mm
    col_widths = [page_width / col_count] * col_count

    cell_style = ParagraphStyle("cell", fontName="Helvetica", fontSize=7,
                                leading=9, wordWrap="LTR")
    hdr_style  = ParagraphStyle("cell_hdr", fontName="Helvetica-Bold", fontSize=7,
                                leading=9, textColor=colors.white, wordWrap="LTR")

    chunks = [rows[i:i + rows_per_page] for i in range(0, len(rows), rows_per_page)]

    for chunk in chunks:
        table_data = [[Paragraph(h, hdr_style) for h in tbl_header]]
        for row in chunk:
            table_row = []
            for h in headers:
                val = str(row.get(h, "") or "")
                if h == "DATE_TRANS":
                    val = _fmt_date(val)
                elif h in AMOUNT_COLS:
                    val = _fmt_amount(val)
                table_row.append(Paragraph(val, cell_style))
            table_data.append(table_row)

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(_day_table_style())
        elements.append(tbl)
        elements.append(Spacer(1, 4 * mm))

    doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
    return filepath


# ── Entry point : CSV → one PDF per day ──────────────────────────────────────

def generate_pdfs_from_csv(
    csv_path: str,
    filename_prefix: str,
    report_type: str,
    output_base_dir: str = "outputs",
    rows_per_page: int = 50,
    account_number: str = "",
    date_col: str = "DATE_TRANS",
    csv_delimiter: str = ";",
) -> Path:
    """
    Read a CSV file, generate one PDF per day, then compress all PDFs into a
    single ZIP file named after the original CSV (prefix replaced by "report_pdf_").

    Parameters
    ----------
    csv_path         : path to the input CSV
    filename_prefix  : prefix for PDF filenames   (e.g. "HABIBO_REPORT_0346137713")
    report_type      : label shown in PDF header  (e.g. "HABIBO_REPORT")
    output_base_dir  : root output folder
    rows_per_page    : max rows per table chunk before page break
    account_number   : account number shown in PDF header
    date_col         : column used to group by day (default "DATE_TRANS")
    csv_delimiter    : CSV field separator          (default ";")

    Returns
    -------
    Path of the generated ZIP file.
    """
    logger = logging.getLogger("send_report")
    logging.basicConfig(level=logging.INFO)

    # ── Read CSV ──────────────────────────────────────────────────────────────
    with open(csv_path, encoding="utf-8") as f:
        data = list(csv.DictReader(f, delimiter=csv_delimiter))

    if not data:
        raise ValueError(f"CSV vide : {csv_path}")

    logger.info(f"CSV chargé : {len(data)} lignes — regroupement par {date_col}")

    # ── Group by day ──────────────────────────────────────────────────────────
    by_date: dict[str, list] = defaultdict(list)
    for row in data:
        by_date[row[date_col][:10]].append(row)

    logger.info(f"{len(by_date)} jour(s) détecté(s) : {sorted(by_date)}")

    # ── One PDF per day ───────────────────────────────────────────────────────
    output_dir = Path(output_base_dir) / report_type
    generated: list[Path] = []

    for day in sorted(by_date.keys()):
        pdf_path = generate_pdf_for_day(
            day=day,
            rows=by_date[day],
            filename_prefix=filename_prefix,
            report_type=report_type,
            output_dir=output_dir,
            rows_per_page=rows_per_page,
            account_number=account_number,
        )
        generated.append(pdf_path)

    logger.info(f"{len(generated)} PDF générés — compression en ZIP…")

    # ── ZIP : même nom que le CSV, préfixe "report_pdf_" ─────────────────────
    csv_stem  = Path(csv_path).stem                        # report_HABIBO_REPORT_…
    zip_stem  = csv_stem.replace("report_", "report_pdf_", 1)
    zip_path  = output_dir / f"{zip_stem}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf in generated:
            zf.write(pdf, arcname=pdf.name)   # store only filename, not full path

    logger.info(f"ZIP créé : {zip_path.resolve()} ({len(generated)} fichiers)")
    return zip_path


# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    zip_file = generate_pdfs_from_csv(
        csv_path="/mnt/user-data/uploads/report_HABIBO_REPORT_0346137713_20260201_20260228_20260412_132606.csv",
        filename_prefix="HABIBO_REPORT_0346137713",
        report_type="HABIBO_REPORT",
        output_base_dir="/home/claude/outputs_by_day",
        account_number="0346137713",
    )
    print(f"ZIP : {zip_file.name}")