import csv
import os
from datetime import datetime
from pathlib import Path
from export.csv_exporter import generate_csv
from export.pdf_exporter import generate_pdf
from services.email_service import send_email_html
from utils.logger import setup_logger
from db.oracle import fetch_reports


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
                
                # Assurez-vous que les bonnes colonnes sont parsées
                date_debut_str = job["date_debut"].strip()
                date_fin_str = job["date_fin"].strip()
                
                # Log pour déboguer
                logger.info(f"[JOB {idx}] date_debut brute: '{date_debut_str}'")
                logger.info(f"[JOB {idx}] date_fin brute: '{date_fin_str}'")
                
                date_debut = datetime.strptime(date_debut_str, DATE_FORMAT)
                date_fin = datetime.strptime(date_fin_str, DATE_FORMAT)
                
                # La partition doit être récupérée telle quelle, pas parsée comme une date
                partition = job.get("partition", "").strip() or None

                logger.debug(f"Contenu de job: {job}")
                logger.debug(f"date_debut = '{job['date_debut']}'")
                logger.debug(f"date_fin = '{job['date_fin']}'")
                logger.debug(f"partition = '{job.get('partition')}'")

                logger.info(f"[JOB {idx}] Paramètres: type={report_type}, nd={nd}, "
                           f"debut={date_debut}, fin={date_fin}, partition={partition}")

                results = fetch_reports(
                    report_type=report_type,
                    nd=nd,
                    date_debut=date_debut,
                    date_fin=date_fin,
                    partition=partition,
                )

                if not results:
                    logger.warning(
                        f"[JOB {idx}] Aucun résultat (ND={nd}, type={report_type})"
                    )
                    continue

                logger.info(f"[JOB {idx}] {len(results)} lignes récupérées")

                csv_file = generate_csv(
                    results,
                    filename_prefix=f"{report_type}_{nd}",
                    report_type=report_type,
                )

                pdf_file = generate_pdf(
                    results,
                    filename_prefix=f"{report_type}_{nd}",
                )

                logger.info(f"[JOB {idx}] Fichiers générés")

                context = {
                    "nd": nd,
                    "report_type": report_type.upper(),
                    "date_debut": date_debut.strftime("%d/%m/%Y"),
                    "date_fin": date_fin.strftime("%d/%m/%Y"),
                    "count": len(results),
                }

                send_email_html(
                    to_email=to_email,
                    cc=cc,
                    bcc=bcc,
                    subject=subject,
                    template_name=template_name,
                    context=context,
                    attachments=[csv_file, pdf_file],
                )

                logger.info(f"[JOB {idx}] Email envoyé avec succès")

            except Exception as e:
                logger.error(
                    f"[JOB {idx}] Erreur traitement : {e}",
                    exc_info=True,
                )

    logger.info("=== Fin traitement des jobs ===")


if __name__ == "__main__":
    main()
