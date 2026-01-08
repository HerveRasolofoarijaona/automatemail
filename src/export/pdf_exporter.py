from pathlib import Path
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def generate_pdf(data: list[dict], output_dir="outputs") -> Path:
    if not data:
        raise ValueError("Aucune donnée à exporter")

    Path(output_dir).mkdir(exist_ok=True)

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = Path(output_dir) / filename

    doc = SimpleDocTemplate(
        str(filepath),  # 🔥 FIX ICI
        pagesize=landscape(A4)
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Rapport automatique", styles["Title"]))
    elements.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["Normal"]
    ))

    headers = list(data[0].keys())
    table_data = [headers]

    for row in data:
        table_data.append([str(row[h]) for h in headers])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    elements.append(table)
    doc.build(elements)

    return filepath
