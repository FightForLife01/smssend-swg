# FILE: app/services/password_reset/request_password_reset.py
# Scop:
#   - POST /api/auth/forgot-password
#   - Generează cod scurt (8 chars), stochează hash, trimite pe email.
#
# Security:
#   - Răspuns anti-enumerare: același mesaj indiferent dacă userul există.
#   - Rate-limit DB-backed pe IP.
#   - Un singur token activ per user (ștergem nefolositele).
#
# Debug:
#   - Dacă userul nu primește email: verifică SMTP_* sau logul în DEBUG.
#   - Dacă token nu se găsește: verifică TOKEN_PEPPER și tabela password_reset_tokens.

import secrets
from datetime import datetime, timedelta

from fastapi import Request
from sqlalchemy.orm import Session

from ...config import settings
from ...models import User, PasswordResetToken
from ...security import hash_token
from ..audit import create_audit_log
from ..email_sender import send_email
from ..rate_limit import enforce_rate_limit_or_raise

_RESET_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _generate_reset_code(length: int = 8) -> str:
    return "".join(secrets.choice(_RESET_ALPHABET) for _ in range(length))


def request_password_reset(db: Session, *, email: str, request: Request) -> dict:
    ip = request.client.host if request.client else "unknown"
    email_norm = (email or "").strip().lower()

    # rate limit pe IP
    enforce_rate_limit_or_raise(
        db,
        key=f"forgot:ip:{ip}",
        max_count=settings.forgot_password_max_attempts_ip,
        window_seconds=settings.forgot_password_window_seconds_ip,
        block_seconds=settings.forgot_password_block_seconds_ip,
    )

    # compatibil cu model vechi/nou (email sau email_normalized)
    q = db.query(User)
    if hasattr(User, "email_normalized"):
        q = q.filter(User.email_normalized == email_norm)
    else:
        q = q.filter(User.email == email_norm)

    user = q.first()

    # Anti-enumerare: răspuns identic
    generic = {"ok": True, "message": "Dacă emailul există, vei primi un cod de resetare."}

    if not user or not getattr(user, "is_active", True):
        create_audit_log(db, "PWD_RESET_REQUEST_UNKNOWN", None, request, details={"email": email_norm, "ip": ip})
        return generic

    now = datetime.utcnow()
    code = _generate_reset_code(8)
    code_hash = hash_token(code)

    expires = now + timedelta(minutes=settings.password_reset_expire_minutes)

    # 1 token activ per user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete()

    row = PasswordResetToken(
        user_id=user.id,
        token_hash=code_hash,
        created_at=now,
        expires_at=expires,
        used_at=None,
    )
    db.add(row)
    db.commit()

    subject = "Resetare parolă - SMSsend By SWG"
    body = (
        "Salut,\n\n"
        "Ai cerut resetarea parolei.\n\n"
        f"Codul tău (valabil {settings.password_reset_expire_minutes} minute): {code}\n\n"
        "Dacă nu ai cerut tu această resetare, ignoră acest email.\n"
    )
    send_email(to_email=user.email, subject=subject, body=body)

    create_audit_log(db, "PWD_RESET_REQUEST", user.id, request, details={"ip": ip})
    return generic
