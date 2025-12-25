# FILE: app/services/auth/rotate_refresh_token.py
# Scop:
#   - Refresh endpoint: validează refresh cookie, rotește tokenul, emite access nou.
#
# Debug:
#   - Dacă refresh pică, verifică:
#       - cookie trimis (credentials: "include" în fetch)
#       - token_hash există și nu e revocat/expirat

from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from ...config import settings
from ...models import RefreshToken, User
from ...schemas import TokenOut
from ...security import hash_token, generate_random_token, create_access_token
from ..audit import create_audit_log


def rotate_refresh_token(db: Session, *, request: Request, response: Response, raw_refresh: str) -> TokenOut:
    now = datetime.utcnow()
    th = hash_token(raw_refresh)

    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == th).first()
    if not rt or rt.revoked_at or rt.expires_at <= now:
        _clear_refresh_cookie(response)
        create_audit_log(db, "REFRESH_FAIL", None, request, details={"reason": "missing_or_expired"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesiune invalidă. Reautentifică-te.")

    user = db.query(User).filter(User.id == rt.user_id, User.is_active == True).first()
    if not user or not user.email_verified_at:
        _clear_refresh_cookie(response)
        create_audit_log(db, "REFRESH_FAIL", rt.user_id, request, details={"reason": "user_invalid"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesiune invalidă. Reautentifică-te.")

    # Rotire: revocăm vechiul token și emitem altul
    new_raw = generate_random_token(64)
    new_hash = hash_token(new_raw)

    rt.revoked_at = now
    rt.replaced_by_hash = new_hash

    new_row = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        replaced_by_hash=None,
        created_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        revoked_at=None,
        ip=(request.client.host if request.client else None),
        user_agent=(request.headers.get("user-agent") or "")[:255] or None,
    )

    db.add(new_row)
    db.commit()

    _set_refresh_cookie(response, new_raw)

    access = create_access_token({"sub": str(user.id)})
    create_audit_log(db, "REFRESH_SUCCESS", user.id, request, details=None)

    return TokenOut(access_token=access, user=user)


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
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


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.cookie_refresh_name, path="/api/auth", domain=settings.cookie_domain or None)
