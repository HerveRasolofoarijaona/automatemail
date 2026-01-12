import csv
import logging
from pathlib import Path
from datetime import datetime


def generate_csv(
    data: list[dict],
    filename_prefix: str,
    report_type: str,
    output_base_dir: str = "outputs",
) -> Path:
    logger = logging.getLogger("send_report")

    if not data:
        logger.warning("Aucune donnée à exporter → CSV non généré")
        raise ValueError("Aucune donnée à exporter")

    # outputs/<report_type>/
    output_dir = Path(output_base_dir) / report_type
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Dossier de sortie CSV : {output_dir.resolve()}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"
    filepath = output_dir / filename

    logger.info(
        f"Génération CSV en cours | fichier={filename} | lignes={len(data)}"
    )

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=data[0].keys(),
            delimiter=";"
        )
        writer.writeheader()
        writer.writerows(data)

    logger.info(f"CSV généré avec succès : {filepath.resolve()}")

    return filepath
