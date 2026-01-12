import os
import sys
import smtplib
import logging
from pathlib import Path
from email.message import EmailMessage
from email.utils import make_msgid
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from typing import List


# ============================================================
# ENV & LOGGER
# ============================================================

load_dotenv()
logger = logging.getLogger("send_report")


# ============================================================
# PATH MANAGEMENT (DEV + EXE SAFE)
# ============================================================

def get_base_path() -> Path:
    """
    Retourne le chemin racine pour les ressources embarquées
    - DEV  : dossier src/
    - EXE  : sys._MEIPASS
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


BASE_PATH = get_base_path()
TEMPLATE_DIR = BASE_PATH / "templates"


# ============================================================
# VALIDATION HELPERS
# ============================================================

def _normalize_emails(emails: str | List[str] | None) -> List[str]:
    if not emails:
        return []
    if isinstance(emails, str):
        return [emails]
    return emails


# ============================================================
# MAIN EMAIL FUNCTION
# ============================================================

def send_email_html(
    to_email: str | List[str],
    subject: str,
    template_name: str,
    context: dict,
    cc: List[str] | None = None,
    bcc: List[str] | None = None,
    attachments: List[str | Path] | None = None,
) -> None:
    """
    Envoi d'un email HTML avec pièces jointes
    Compatible PyInstaller / EXE
    """

    # ---------------- ENV ----------------
    host = os.getenv("EMAIL_HOST")
    port = int(os.getenv("EMAIL_PORT", 0))
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")

    if not all([host, port, user, password]):
        raise RuntimeError("Configuration EMAIL_* incomplète (.env)")

    # ---------------- RECIPIENTS ----------------
    to_list = _normalize_emails(to_email)
    cc_list = _normalize_emails(cc)
    bcc_list = _normalize_emails(bcc)

    if not to_list:
        raise ValueError("Aucun destinataire principal (To)")

    # ---------------- TEMPLATE ----------------
    if not TEMPLATE_DIR.exists():
        raise RuntimeError(f"Dossier templates introuvable : {TEMPLATE_DIR}")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True
    )

    try:
        template = env.get_template(template_name)
    except Exception as e:
        logger.error(f"Template introuvable : {template_name}")
        raise

    html_content = template.render(**context)

    # ---------------- MESSAGE ----------------
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid()

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    msg.set_content("Votre client email ne supporte pas le HTML.")
    msg.add_alternative(html_content, subtype="html")

    # ---------------- ATTACHMENTS ----------------
    attached_files = []

    if attachments:
        for file in attachments:
            path = Path(file)
            if not path.exists():
                logger.warning(f"PJ introuvable ignorée : {path}")
                continue

            with open(path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=path.name,
                )

            attached_files.append(path.name)

    # ---------------- SEND ----------------
    recipients = to_list + cc_list + bcc_list

    logger.info(
        f"Envoi email → To={to_list} | Cc={cc_list} | "
        f"Bcc={len(bcc_list)} | PJ={attached_files}"
    )

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg, to_addrs=recipients)

        logger.info("Email envoyé avec succès")

    except Exception:
        logger.exception("Erreur lors de l'envoi de l'email")
        raise
