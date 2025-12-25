# FILE: app/routes/password_reset.py
# Endpoint-uri:
#   - POST /api/auth/forgot-password
#   - POST /api/auth/reset-password
#
# Debug:
#   - Dacă primești 500, verifică dacă există tabelele:
#       - password_reset_tokens
#       - rate_limits

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..deps.db import get_db
from ..services.password_reset.request_password_reset import request_password_reset
from ..services.password_reset.confirm_password_reset import confirm_password_reset

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=32)
    password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str = Field(..., min_length=12, max_length=128)


@router.post("/forgot-password")
def forgot_password_route(data: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    return request_password_reset(db, email=str(data.email), request=request)


@router.post("/reset-password")
def reset_password_route(data: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    return confirm_password_reset(
        db,
        email=str(data.email),
        code=data.code,
        password=data.password,
        confirm_password=data.confirm_password,
        request=request,
    )
