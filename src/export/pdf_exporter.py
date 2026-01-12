import logging
from pathlib import Path
from datetime import datetime
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    PageBreak
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def generate_pdf(
    data: list[dict],
    filename_prefix: str,
    report_type: str,
    output_base_dir: str = "outputs",
    rows_per_page: int = 50,
) -> Path:

    logger = logging.getLogger("send_report")

    if not data:
        raise ValueError("Aucune donnée à exporter")

    # ---------- PATH ----------
    output_dir = Path(output_base_dir) / report_type
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{filename_prefix}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    filepath = output_dir / filename

    logger.info(
        f"Génération PDF paginée | fichier={filename} | lignes={len(data)}"
    )

    # ---------- DOCUMENT ----------
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---------- HEADER ----------
    elements.append(Paragraph("Rapport automatique", styles["Title"]))
    elements.append(Paragraph(
        f"Généré le {datetime.now():%d/%m/%Y %H:%M}",
        styles["Normal"]
    ))
    elements.append(Paragraph(
        f"Type: {report_type} — Total lignes: {len(data)}",
        styles["Italic"]
    ))
    elements.append(PageBreak())

    # ---------- TABLE ----------
    headers = list(data[0].keys())
    col_count = len(headers)

    col_widths = [doc.width / col_count] * col_count

    def table_style():
        return TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ])

    # ---------- PAGINATION ----------
    for start in range(0, len(data), rows_per_page):
        chunk = data[start:start + rows_per_page]

        table_data = [headers]
        for row in chunk:
            table_data.append([str(row[h]) for h in headers])

        table = Table(
            table_data,
            colWidths=col_widths,
            repeatRows=1
        )
        table.setStyle(table_style())

        elements.append(table)
        elements.append(PageBreak())

        if start % (rows_per_page * 20) == 0:
            logger.debug(f"PDF progression : {start}/{len(data)} lignes")

    # ---------- BUILD ----------
    doc.build(elements)

    logger.info(f"PDF généré avec succès : {filepath.resolve()}")

    return filepath
