import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader


load_dotenv()

def get_base_path():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_PATH = get_base_path()
TEMPLATE_DIR = BASE_PATH / "templates"

def send_email_html(
    to_email: str | list[str],
    subject: str,
    template_name: str,
    context: dict,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    attachments: list[str] | None = None,
) -> None:
    host = os.getenv("EMAIL_HOST")
    port = int(os.getenv("EMAIL_PORT", "0"))
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")

    if not all([host, port, user, password]):
        raise RuntimeError("Configuration email incomplète")

    # --- Normalize recipients ---
    to_list = [to_email] if isinstance(to_email, str) else to_email
    cc_list = cc or []
    bcc_list = bcc or []

    # --- HTML rendering ---
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)
    html_content = template.render(**context)

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    msg.set_content("Votre client email ne supporte pas le HTML.")
    msg.add_alternative(html_content, subtype="html")

    # --- Attachments ---
    if attachments:
        for file_path in attachments:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Fichier introuvable : {path}")

            with open(path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=path.name,
                )

    # --- ALL recipients (To + Cc + Bcc) ---
    all_recipients = to_list + cc_list + bcc_list

    # --- Send ---
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(
                msg,
                from_addr=user,
                to_addrs=all_recipients,  # 🔥 BCC ici seulement
            )

    except Exception as e:
        raise RuntimeError(f"Échec envoi email : {e}")
