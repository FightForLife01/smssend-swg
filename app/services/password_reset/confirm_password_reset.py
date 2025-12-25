# FILE: app/services/password_reset/confirm_password_reset.py
# Scop:
#   - POST /api/auth/reset-password
#   - Validează cod + email + TTL, schimbă parola, marchează token folosit.
#
# Security:
#   - Rate-limit pe IP + email (anti brute-force pe cod).
#   - one-time use: used_at.
#   - opțional: revocă refresh tokens dacă tabela există (compatibilitate).
#
# Debug:
#   - “Cod invalid/expirat”: verifică expirare, used_at, TOKEN_PEPPER, și că emailul e corect.

import re
from datetime import datetime

from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from ...config import settings
from ...models import User, PasswordResetToken
from ...security import hash_token, hash_password
from ..audit import create_audit_log
from ..rate_limit import enforce_rate_limit_or_raise


def _validate_new_password_or_raise(password: str, *, email: str) -> None:
    pw = str(password or "")

    if len(pw) < 12 or len(pw) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola trebuie să aibă 12-128 caractere.")
    if pw.strip() != pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola nu poate începe/termina cu spații.")

    has_lower = bool(re.search(r"[a-z]", pw))
    has_upper = bool(re.search(r"[A-Z]", pw))
    has_digit = bool(re.search(r"\d", pw))
    has_sym = bool(re.search(r"[^A-Za-z0-9]", pw))
    if sum([has_lower, has_upper, has_digit, has_sym]) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parola trebuie să conțină cel puțin 3 din: litere mici, litere mari, cifre, simboluri.",
        )

    local = (email or "").split("@")[0].lower()
    if local and local in pw.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola nu poate conține emailul.")


def confirm_password_reset(
    db: Session,
    *,
    email: str,
    code: str,
    password: str,
    confirm_password: str,
    request: Request,
) -> dict:
    ip = request.client.host if request.client else "unknown"
    email_norm = (email or "").strip().lower()
    code_norm = (code or "").strip().upper()

    # rate limit: IP + email
    enforce_rate_limit_or_raise(
        db,
        key=f"reset:ip:{ip}",
        max_count=settings.reset_password_max_attempts_ip,
        window_seconds=settings.reset_password_window_seconds_ip,
        block_seconds=settings.reset_password_block_seconds_ip,
    )
    enforce_rate_limit_or_raise(
        db,
        key=f"reset:email:{email_norm}",
        max_count=settings.reset_password_max_attempts_email,
        window_seconds=settings.reset_password_window_seconds_email,
        block_seconds=settings.reset_password_block_seconds_email,
    )

    if not code_norm or len(code_norm) < 6 or len(code_norm) > 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cod invalid sau expirat.")

    if password != confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parolele nu coincid.")

    _validate_new_password_or_raise(password, email=email_norm)

    # compatibil cu model vechi/nou (email sau email_normalized)
    q = db.query(User)
    if hasattr(User, "email_normalized"):
        q = q.filter(User.email_normalized == email_norm)
    else:
        q = q.filter(User.email == email_norm)

    user = q.first()
    if not user or not getattr(user, "is_active", True):
        create_audit_log(db, "PWD_RESET_CONFIRM_FAIL", None, request, details={"email": email_norm, "ip": ip})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cod invalid sau expirat.")

    now = datetime.utcnow()
    code_hash = hash_token(code_norm)

    tok = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.token_hash == code_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).first()

    if not tok:
        create_audit_log(db, "PWD_RESET_CONFIRM_FAIL", user.id, request, details={"reason": "token_invalid", "ip": ip})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cod invalid sau expirat.")

    # schimbare parolă + token one-time
    user.password_hash = hash_password(password)
    tok.used_at = now

    # dacă ai câmpuri de lockout, le resetăm fără să crape pe model vechi
    if hasattr(user, "failed_login_count"):
        user.failed_login_count = 0
    if hasattr(user, "locked_until"):
        user.locked_until = None

    # Revocăm refresh tokens dacă modelul există (compatibil)
    try:
        from ...models import RefreshToken  # type: ignore
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": now})
    except Exception:
        pass

    db.commit()

    create_audit_log(db, "PWD_RESET_SUCCESS", user.id, request, details={"ip": ip})
    return {"ok": True, "message": "Parola a fost schimbată. Te poți autentifica."}
