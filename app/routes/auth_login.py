# FILE: app/routes/auth_login.py
# Endpoint: POST /api/auth/login

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..deps.db import get_db
from ..schemas import LoginIn, TokenOut
from ..services.auth.login_user import login_user

router = APIRouter()


@router.post("/login", response_model=TokenOut)
def login_route(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    return login_user(db, data=data, request=request, response=response)
