# FILE: app/routes/auth_refresh.py
# Endpoint: POST /api/auth/refresh

from fastapi import APIRouter, Depends, Request, Response, Cookie
from sqlalchemy.orm import Session

from ..deps.db import get_db
from ..config import settings
from ..schemas import TokenOut
from ..services.auth.rotate_refresh_token import rotate_refresh_token

router = APIRouter()


@router.post("/refresh", response_model=TokenOut)
def refresh_route(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.cookie_refresh_name),
    db: Session = Depends(get_db),
):
    # refresh_token cookie este HttpOnly; JS nu-l citește, doar îl trimite.
    if not refresh_token:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesiune invalidă. Reautentifică-te.")
    return rotate_refresh_token(db, request=request, response=response, raw_refresh=refresh_token)
