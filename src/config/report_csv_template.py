import csv
from pathlib import Path


def generate_report_job_csv_template(
    output_file: str = "report_jobs.csv",
) -> str:
    headers = [
        "to_email",
        "cc",
        "bcc",
        "subject",
        "template_name",
        "report_type",
        "nd",
        "date_debut",
        "date_fin",
        "partition",
    ]

    output_path = Path(output_file)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)

        # ligne exemple
        writer.writerow([
            "client@entreprise.com",
            "manager@entreprise.com|finance@entreprise.com",
            "audit@entreprise.com",
            "Rapport Remittance",
            "remittance.html",
            "remit",
            "ND001",
            "2026-01-01",
            "2026-01-01",
            "P202601",
        ])

    return str(output_path)
