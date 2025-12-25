# FILE: app/routes/auth.py
# Router principal /api/auth, include endpoint-uri din fișiere separate.
#
# Debug:
#   - Dacă /docs nu arată un endpoint, verifică include_router().

from fastapi import APIRouter

from .auth_register import router as register_router
from .auth_login import router as login_router
from .auth_refresh import router as refresh_router
from .auth_logout import router as logout_router
from .auth_me import router as me_router
from .auth_verify_email import router as verify_email_router

router = APIRouter(prefix="/api/auth", tags=["auth"])

router.include_router(register_router)
router.include_router(login_router)
router.include_router(refresh_router)
router.include_router(logout_router)
router.include_router(me_router)
router.include_router(verify_email_router)
