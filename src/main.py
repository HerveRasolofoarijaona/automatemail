import sys
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# ✅ Pour PyInstaller : chercher le .env à côté de l'exe
if getattr(sys, 'frozen', False):
    # On est dans un exe PyInstaller
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(_file_))

load_dotenv(os.path.join(base_dir, ".env"))


from export.csv_exporter import generate_csv
from services.email_service import send_email_html
from utils.logger import setup_logger
from db.oracle import fetch_reports
from export.pdf_exporter import generate_pdfs_from_csv


CSV_JOBS_FILE = "report_jobs.csv"
DATE_FORMAT = "%Y-%m-%d"

logger = setup_logger(
    log_level=os.getenv("LOG_LEVEL", "INFO")
)

logger.info("Démarrage de l'application")


def parse_emails(value: str | None) -> list[str]:
    if not value:
        return []
    return [e.strip() for e in value.split("|") if e.strip()]


def main():
    csv_path = Path(CSV_JOBS_FILE)
    summary_rows: list[dict] = []

    if not csv_path.exists():
        logger.error(f"Fichier jobs introuvable : {CSV_JOBS_FILE}")
        return

    logger.info("=== Démarrage traitement des jobs ===")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")

        for idx, job in enumerate(reader, start=1):
            try:
                logger.info(f"[JOB {idx}] Début traitement")

                to_email = parse_emails(job["to_email"])
                cc = parse_emails(job.get("cc"))
                bcc = parse_emails(job.get("bcc"))

                subject = job["subject"]
                template_name = job["template_name"]

                report_type = job["report_type"]
                nd = job["nd"]

                # Dates
                date_debut = datetime.strptime(
                    job["date_debut"].strip(), DATE_FORMAT
                )

                # 🔥 FIN À 23:59:59
                date_fin = (
                    datetime.strptime(job["date_fin"].strip(), DATE_FORMAT)
                    + timedelta(days=1)
                    - timedelta(seconds=1)
                )

                partition = job.get("partition", "").strip() or None

                logger.info(
                    f"[JOB {idx}] Paramètres: type={report_type}, nd={nd}, "
                    f"debut={date_debut}, fin={date_fin}, partition={partition}"
                )

                results = fetch_reports(
                    report_type=report_type,
                    nd=nd,
                    date_debut=date_debut,
                    date_fin=date_fin,
                    partition=partition,
                )

                if not results:
                    logger.warning(f"[JOB {idx}] Aucun résultat")
                    continue

                logger.info(f"[JOB {idx}] {len(results)} lignes récupérées")

                date_formatee_debut = date_debut.strftime("%Y%m%d")
                date_formatee_fin = date_fin.strftime("%Y%m%d")

                csv_file = generate_csv(
                    results,
                    filename_prefix=f"report_{subject}_{nd}_{date_formatee_debut}_{date_formatee_fin}",
                    report_type=report_type,
                )

                """
                    pdf_file = generate_pdf(
                        results,
                        filename_prefix=f"{report_type}_{nd}",
                        report_type=report_type,
                    )

                    logger.info(f"[JOB {idx}] Fichiers générés")
                """ 
                pdfs_file = generate_pdfs_from_csv(
                    csv_path=csv_file,
                    filename_prefix=f"{report_type}_{nd}",
                    report_type=report_type,
                    output_base_dir="outputs/pdf",
                    account_number=nd,
                )

                context = {
                    "nd": nd,
                    "report_type": report_type.upper(),
                    "date_debut": date_debut.strftime("%d/%m/%Y"),
                    "date_fin": date_fin.strftime("%d/%m/%Y"),
                    "count": len(results),
                } 

                """
                    send_email_html(
                            to_email=to_email,
                            cc=cc,
                            bcc=bcc,
                            subject=subject,
                            template_name=template_name,
                            context=context,
                            attachments=[csv_file],
                    )

                    logger.info(f"[JOB {idx}] Email envoyé avec succès")
                """
                
                summary_rows.append({
                    "to_email": "|".join(to_email),
                    "csv_files": str(csv_file),
                    "pdf_files": str(pdfs_file)
                })

            except Exception as e:
                logger.error(
                    f"[JOB {idx}] Erreur traitement : {e}",
                    exc_info=True,
                )

    # === CSV RÉCAPITULATIF ===
    if summary_rows:
        today = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        summary_path = Path("outputs") / f"jobs_summary_{today}.csv"
        summary_path.parent.mkdir(exist_ok=True)

        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["to_email", "csv_files","pdf_files"]
            )
            writer.writeheader()
            writer.writerows(summary_rows)

        logger.info(f"CSV récapitulatif généré : {summary_path}")
    else:
        logger.warning("Aucun job traité, CSV récapitulatif non généré")

    logger.info("=== Fin traitement des jobs ===")


if __name__ == "__main__":
    main()
