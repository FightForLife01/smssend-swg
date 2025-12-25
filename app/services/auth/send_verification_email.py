# FILE: app/services/auth/send_verification_email.py
# Scop:
#   - Trimite email de verificare via SMTP.
#
# În prod:
#   - SMTP_* trebuie setat. Dacă nu, registration trebuie să eșueze (altfel blochezi userul).
#
# Debug:
#   - În DEBUG fără SMTP, logăm linkul (doar local).

import logging
import smtplib
from email.mime.text import MIMEText

from ...config import settings

logger = logging.getLogger(__name__)


def send_verification_email(*, to_email: str, token: str) -> None:
    verify_url = f"{settings.app_base_url.rstrip('/')}/api/auth/verify-email?token={token}"

    subject = "Confirmare email - SMSsend By SWG"
    body = (
        "Salut,\n\n"
        "Te rugăm să confirmi adresa de email accesând linkul:\n"
        f"{verify_url}\n\n"
        "Dacă nu ai cerut tu acest cont, ignoră acest mesaj.\n"
    )

    # În debug, dacă nu ai SMTP setat, nu blocăm development-ul.
    if settings.debug and not settings.smtp_host:
        logger.warning("DEBUG MODE: SMTP neconfigurat. Link verificare email: %s", verify_url)
        return

    # În prod, SMTP trebuie să existe.
    if not settings.smtp_host or not settings.smtp_from:
        raise RuntimeError("SMTP_HOST / SMTP_FROM lipsesc în producție.")

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    if settings.smtp_tls:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        server.starttls()
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)

    try:
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, [to_email], msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass
