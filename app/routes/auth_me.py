# FILE: app/routes/auth_me.py
# Endpoint: GET /api/auth/me

from fastapi import APIRouter, Depends

from ..deps.auth import get_current_user
from ..models import User
from ..schemas import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
def me_route(current_user: User = Depends(get_current_user)):
    return current_user
