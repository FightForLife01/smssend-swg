# FILE: app/services/sms_service.py
# Scop:
#   - Trimite SMS via SMSAPI.ro.
#   - Folosește token + sender per user (din DB), cu fallback global din .env dacă există.
#   - Obține soldul (points) din SMSAPI /profile pentru dashboard.
#
# GDPR:
#   - Nu logăm textul complet al mesajului.
#   - Nu expunem token-ul în răspunsuri sau loguri.

import logging
from typing import Tuple, Optional

import requests
from sqlalchemy.orm import Session

from ..config import settings
from ..models import SmsLog, Order, User

logger = logging.getLogger(__name__)


def send_sms_for_order(db: Session, user: User, order: Order, message_text: str) -> Tuple[bool, str]:
    token = user.smsapi_token or settings.smsapi_token
    sender = user.smsapi_sender or settings.smsapi_sender

    if not token:
        return False, "Lipsește token-ul SMSAPI în contul tău (Setări SMS)."
    if not sender:
        return False, "Lipsește expeditorul SMS (sender) în contul tău (Setări SMS)."

    phone = order.phone_number or order.delivery_phone
    if not phone:
        return False, "Comanda nu are număr de telefon."

    url = "https://api.smsapi.ro/sms.do"
    payload = {
        "to": str(phone),
        "message": message_text,
        "from": sender,
        "format": "json",
    }
    headers = {
        "Authorization": f"Bearer {token}",
    }

    success = False
    msg_id = ""
    error_msg = ""

    try:
        resp = requests.post(url, data=payload, headers=headers, timeout=10)
        data = resp.json()
    except Exception as e:
        logger.error("Eroare la apelul SMSAPI: %s", e)
        error_msg = str(e)
    else:
        if data.get("error"):
            error_msg = data.get("message", "Eroare SMSAPI")
        else:
            lst = data.get("list") or []
            msg_id = lst[0].get("id") if lst else ""
            success = True

    sms_log = SmsLog(
        user_id=user.id,
        order_id=order.id,
        phone=str(phone),
        message_id=msg_id,
        status="success" if success else "error",
        error_message=error_msg,
    )
    db.add(sms_log)
    db.commit()

    if success:
        return True, msg_id
    else:
        return False, error_msg or "Eroare la trimiterea SMS-ului."


def get_sms_balance_for_user(user: User) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Obține soldul (points) pentru contul SMSAPI al userului.
    - Folosește token-ul userului; dacă nu are, fallback la global (dacă există).
    - Returnează (ok, points, error).
    """
    token = user.smsapi_token or settings.smsapi_token
    if not token:
        return False, None, "Lipsește token-ul SMSAPI (Setări SMS)."

    url = "https://api.smsapi.ro/profile"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
    except Exception as e:
        logger.error("Eroare la apelul SMSAPI /profile: %s", e)
        return False, None, str(e)

    if resp.status_code != 200:
        msg = data.get("message") if isinstance(data, dict) else str(data)
        return False, None, f"Eroare SMSAPI profile: {msg}"

    points = data.get("points")
    try:
        points_val = float(points) if points is not None else None
    except Exception:
        points_val = None

    return True, points_val, None
