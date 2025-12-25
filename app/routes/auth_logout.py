# FILE: app/routes/auth_logout.py
# Endpoint: POST /api/auth/logout

from fastapi import APIRouter, Depends, Request, Response, Cookie
from sqlalchemy.orm import Session

from ..deps.db import get_db
from ..config import settings
from ..services.auth.revoke_refresh_token import revoke_refresh_token

router = APIRouter()


@router.post("/logout")
def logout_route(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.cookie_refresh_name),
    db: Session = Depends(get_db),
):
    revoke_refresh_token(db, request=request, response=response, raw_refresh=refresh_token)
    return {"ok": True}
