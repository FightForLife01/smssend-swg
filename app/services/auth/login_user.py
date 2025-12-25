# FILE: app/services/auth/login_user.py
# Scop:
#   - Login enterprise: rate-limit (IP+email), lockout, email verify, refresh cookie.
#
# Debug:
#   - Dacă userul zice "corect dar nu merge", verifică:
#       - email_verified_at
#       - locked_until
#       - rate_limits table

from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from ...config import settings
from ...models import User, RefreshToken
from ...schemas import LoginIn, TokenOut
from ...security import verify_password, needs_password_rehash, hash_password, create_access_token, generate_random_token, hash_token
from ..audit import create_audit_log
from .normalize_email import normalize_email
from .enforce_rate_limit import enforce_rate_limit_or_raise


def login_user(db: Session, *, data: LoginIn, request: Request, response: Response) -> TokenOut:
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent")

    email_norm = normalize_email(data.email)

    # Rate limit: IP + email
    enforce_rate_limit_or_raise(
        db,
        key=f"login:ip:{ip}",
        max_count=settings.login_max_attempts_ip,
        window_seconds=settings.login_window_seconds_ip,
        block_seconds=settings.login_block_seconds_ip,
    )
    enforce_rate_limit_or_raise(
        db,
        key=f"login:email:{email_norm}",
        max_count=settings.login_max_attempts_email,
        window_seconds=settings.login_window_seconds_email,
        block_seconds=settings.login_block_seconds_email,
    )

    user = db.query(User).filter(User.email_normalized == email_norm).first()

    # Anti-enumerare: răspuns identic pentru user inexistent
    if not user or not user.is_active:
        create_audit_log(db, "LOGIN_FAIL", None, request, details={"email": email_norm, "ip": ip})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credențiale invalide.")

    now = datetime.utcnow()

    # Lockout
    if user.locked_until and user.locked_until > now:
        create_audit_log(db, "LOGIN_LOCKED", user.id, request, details={"until": user.locked_until.isoformat()})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Cont temporar blocat. Reîncearcă mai târziu.")

    # Email verification required
    if not user.email_verified_at:
        create_audit_log(db, "LOGIN_EMAIL_NOT_VERIFIED", user.id, request, details={"email": email_norm})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email neverificat. Verifică inbox și confirmă emailul.")

    # Verify password
    ok = verify_password(data.password, user.password_hash)
    if not ok:
        user.failed_login_count = int(user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.lockout_fail_threshold:
            user.locked_until = now + timedelta(seconds=settings.lockout_seconds)
        db.commit()

        create_audit_log(db, "LOGIN_FAIL", user.id, request, details={"email": email_norm, "ip": ip})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credențiale invalide.")

    # Upgrade hash dacă e cazul (argon2 params / pepper legacy)
    if settings.password_pepper and needs_password_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()

    # Access token scurt
    access = create_access_token({"sub": str(user.id)})

    # Refresh token (random) + DB hash
    raw_refresh = generate_random_token(64)
    refresh_hash = hash_token(raw_refresh)
    refresh_expires = now + timedelta(days=settings.refresh_token_expire_days)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        replaced_by_hash=None,
        created_at=now,
        expires_at=refresh_expires,
        revoked_at=None,
        ip=ip,
        user_agent=ua[:255] if ua else None,
    )
    db.add(rt)
    db.commit()

    _set_refresh_cookie(response, raw_refresh)

    create_audit_log(db, "LOGIN_SUCCESS", user.id, request, details={"ip": ip})

    return TokenOut(access_token=access, user=user)


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    """
    Cookie HttpOnly => JS nu îl poate citi.
    SameSite=strict => CSRF defense by default (SPA same-site).
    """
    kwargs = {
        "key": settings.cookie_refresh_name,
        "value": raw_refresh,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/api/auth",
        "max_age": settings.refresh_token_expire_days * 24 * 3600,
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain

    response.set_cookie(**kwargs)
