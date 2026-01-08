import csv
from pathlib import Path
from datetime import datetime


def generate_csv(data: list[dict], output_dir="outputs") -> Path:
    if not data:
        raise ValueError("Aucune donnée à exporter")

    Path(output_dir).mkdir(exist_ok=True)

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = Path(output_dir) / filename

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    return filepath
