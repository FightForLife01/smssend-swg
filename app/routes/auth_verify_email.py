# FILE: app/routes/auth_verify_email.py
# Endpoint: GET /api/auth/verify-email?token=...

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..deps.db import get_db
from ..services.auth.verify_email import verify_email

router = APIRouter()


@router.get("/verify-email")
def verify_email_route(token: str, request: Request, db: Session = Depends(get_db)):
    verify_email(db, request=request, token=token)
    return {"ok": True, "message": "Email confirmat. Te poți autentifica."}
