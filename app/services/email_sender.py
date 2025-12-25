# FILE: app/services/email_sender.py
# Scop:
#   - Trimitere email SMTP (TLS) pentru verificare email și resetare parolă.
#
# Debug:
#   - În DEBUG, dacă SMTP_* nu sunt setate, logăm DOAR faptul că am “trimis” (nu blocăm dev).
#   - În PROD, dacă SMTP_HOST/SMTP_FROM lipsesc => ridicăm excepție (altfel funcția e falsă).

import logging
import smtplib
from email.mime.text import MIMEText

from ..config import settings

logger = logging.getLogger(__name__)


def send_email(*, to_email: str, subject: str, body: str) -> None:
    if settings.debug and not settings.smtp_host:
        logger.warning("DEBUG: SMTP neconfigurat. Email către=%s subiect=%s (body neafișat)", to_email, subject)
        return

    if not settings.smtp_host or not settings.smtp_from:
        raise RuntimeError("SMTP_HOST / SMTP_FROM lipsesc. Nu pot trimite email în producție.")

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=12)
    try:
        if settings.smtp_tls:
            server.starttls()

        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)

        server.sendmail(settings.smtp_from, [to_email], msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass
