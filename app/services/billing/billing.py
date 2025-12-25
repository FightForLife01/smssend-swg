# FILE: app/routes/billing.py
# Scop:
#   - API Billing (Stripe) - Pasul 2.1: Checkout Session pentru subscriptions.
#
# Debug:
#   - Test din /docs:
#       1) login -> copiază access_token
#       2) Authorize (Bearer <token>)
#       3) POST /api/billing/checkout {"plan":"starter"}
#   - Dacă primești 500 "Stripe neconfigurat" => verifică .env (STRIPE_SECRET_KEY + URL-uri).
#   - Dacă primești 500 "no such column users.stripe_customer_id" => ALTER TABLE (vezi pașii).
#   - Dacă primești 502 => Stripe a răspuns cu eroare (price/keys/cont).

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..deps.auth import get_current_user
from ..deps.db import get_db
from ..models import User
from ..schemas import BillingCheckoutIn, BillingCheckoutOut
from ..services.audit import create_audit_log
from ..services.billing.create_checkout import create_checkout_session

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger(__name__)


@router.post("/checkout", response_model=BillingCheckoutOut)
def billing_checkout(
    data: BillingCheckoutIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        res = create_checkout_session(db, user=current_user, plan=data.plan)

        create_audit_log(
            db,
            "BILLING_CHECKOUT_CREATE",
            current_user.id,
            request,
            details={
                "plan": data.plan,
                "stripe_customer_id": current_user.stripe_customer_id,
                "checkout_session_id": res.session_id,
            },
        )

        return BillingCheckoutOut(ok=True, url=res.url, session_id=res.session_id)

    except stripe.error.StripeError as exc:
        logger.exception("Stripe error la checkout user_id=%s plan=%s", current_user.id, data.plan)
        create_audit_log(
            db,
            "BILLING_CHECKOUT_FAIL",
            current_user.id,
            request,
            details={"plan": data.plan, "error": str(exc)[:500]},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Eroare la procesatorul de plăți. Reîncearcă.",
        )

    except Exception as exc:
        logger.exception("Eroare internă la billing checkout user_id=%s plan=%s", current_user.id, data.plan)
        create_audit_log(
            db,
            "BILLING_CHECKOUT_FAIL",
            current_user.id,
            request,
            details={"plan": data.plan, "error": str(exc)[:500]},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eroare internă. Verifică setările și încearcă din nou.",
        )
