# FILE: app/routes/auth_register.py
# Endpoint: POST /api/auth/register

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ..deps.db import get_db
from ..schemas import UserRegisterIn, RegisterOut
from ..services.auth.register_user import register_user

router = APIRouter()


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_202_ACCEPTED)
def register_route(data: UserRegisterIn, request: Request, db: Session = Depends(get_db)):
    return register_user(db, data=data, request=request)
