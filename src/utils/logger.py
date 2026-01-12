import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os
from datetime import datetime


def setup_logger(
    name: str = "send_report",
    log_level: str | None = None,
) -> logging.Logger:
    """
    Configure un logger fichier + console.
    """

    # Dossier logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Niveau de log
    level = (
        getattr(logging, log_level.upper())
        if log_level
        else logging.INFO
    )

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Évite les doublons
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"send_report_{timestamp}.log"

    # ---- File handler (rotation)
    file_handler = RotatingFileHandler(
        log_dir / filename,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # ---- Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
