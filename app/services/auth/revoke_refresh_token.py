# FILE: app/services/auth/revoke_refresh_token.py
# Scop:
#   - Logout: revocă refresh token curent și șterge cookie.

from datetime import datetime
from fastapi import Request, Response
from sqlalchemy.orm import Session

from ...config import settings
from ...models import RefreshToken
from ...security import hash_token
from ..audit import create_audit_log


def revoke_refresh_token(db: Session, *, request: Request, response: Response, raw_refresh: str | None) -> None:
    _clear_refresh_cookie(response)

    if not raw_refresh:
        create_audit_log(db, "LOGOUT_NO_COOKIE", None, request, details=None)
        return

    th = hash_token(raw_refresh)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == th).first()
    if not rt or rt.revoked_at:
        create_audit_log(db, "LOGOUT_ALREADY_REVOKED", None, request, details=None)
        return

    rt.revoked_at = datetime.utcnow()
    db.commit()
    create_audit_log(db, "LOGOUT", rt.user_id, request, details=None)


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.cookie_refresh_name, path="/api/auth", domain=settings.cookie_domain or None)
