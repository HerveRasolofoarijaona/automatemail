import logging
from pathlib import Path
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def generate_pdf(
    data: list[dict],
    filename_prefix: str,
    report_type: str,
    output_base_dir: str = "outputs",
) -> Path:
    logger = logging.getLogger("send_report")

    if not data:
        logger.warning("Aucune donnée à exporter → PDF non généré")
        raise ValueError("Aucune donnée à exporter")

    # outputs/<report_type>/
    output_dir = Path(output_base_dir) / report_type
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Dossier de sortie PDF : {output_dir.resolve()}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.pdf"
    filepath = output_dir / filename

    logger.info(
        f"Génération PDF en cours | fichier={filename} | lignes={len(data)}"
    )

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()
    elements = []

    # --- Titre ---
    elements.append(Paragraph("Rapport automatique", styles["Title"]))
    elements.append(
        Paragraph(
            f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        )
    )

    # --- Table ---
    headers = list(data[0].keys())
    table_data = [headers]

    for row in data:
        table_data.append([str(row.get(h, "")) for h in headers])

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    elements.append(table)

    doc.build(elements)

    logger.info(f"PDF généré avec succès : {filepath.resolve()}")

    return filepath
