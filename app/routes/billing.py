# FILE: app/routes/billing.py
# Scop:
#   - Router /api/billing.
#   - În acest moment este STUB (minim) ca aplicația să pornească stabil.
#   - Implementarea reală Stripe (BILL-03..BILL-06) o facem pas cu pas.
#
# Debug:
#   - Dacă primești ImportError în app/main.py legat de `billing`,
#     înseamnă că acest fișier lipsește sau nu e inclus în repo.

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..deps.db import get_db
from ..deps.auth import get_current_user
from ..models import User
from ..services.audit import create_audit_log

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/me")
def billing_me(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Status billing pentru userul curent.
    Stub stabil până implementăm Stripe.
    """
    create_audit_log(db, "BILLING_ME", current_user.id, request, details=None)
    return {
        "ok": True,
        "subscription": None,
        "usage": None,
        "note": "Billing API stub. Implementarea Stripe urmează (Checkout/Portal/Webhook).",
    }


@router.post("/checkout")
def billing_checkout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    create_audit_log(db, "BILLING_CHECKOUT_STUB", current_user.id, request, details=None)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Billing checkout nu este implementat încă (BILL-04).",
    )


@router.post("/portal")
def billing_portal(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    create_audit_log(db, "BILLING_PORTAL_STUB", current_user.id, request, details=None)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Billing portal nu este implementat încă (BILL-05).",
    )


@router.post("/webhook")
async def billing_webhook(request: Request):
    """
    Stripe webhook endpoint (BILL-06).
    Va deveni endpoint public cu signature verify + dedup.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Stripe webhook nu este implementat încă (BILL-06).",
    )
