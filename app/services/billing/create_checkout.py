# FILE: app/services/billing/create_checkout.py
# Scop:
#   - Creează Stripe Checkout Session (mode=subscription) pentru planul ales.
#   - Leagă sesiunea de Stripe Customer (stocat în DB).
#
# Notes:
#   - Trial (7 zile) se aplică DOAR pentru growth/pro și vine din env STRIPE_TRIAL_DAYS.
#   - success_url/cancel_url sunt controlate din env (nu hardcodăm).
#
# Debug / depanare:
#   - "Stripe neconfigurat" => lipsește STRIPE_SECRET_KEY sau URL-urile.
#   - "No such price" => price id greșit sau cont greșit (TEST vs LIVE).
#   - "no such column stripe_customer_id" => ALTER TABLE lipsă.

from __future__ import annotations

from dataclasses import dataclass

import stripe
from sqlalchemy.orm import Session

from ...config import settings
from ...models import User
from .stripe_customer import get_or_create_stripe_customer_id


@dataclass(frozen=True)
class CheckoutResult:
    session_id: str
    url: str


def _ensure_session_id_placeholder(url: str) -> str:
    """
    Recomandare Stripe: success_url să includă {CHECKOUT_SESSION_ID}.
    Dacă lipsește, îl adăugăm ca query param session_id.

    IMPORTANT:
      - Nu modificăm dacă placeholder există deja.
      - Nu stricăm query params existenți.
    """
    if not url:
        return url
    if "CHECKOUT_SESSION_ID" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}session_id={{CHECKOUT_SESSION_ID}}"


def _get_price_id_for_plan(plan: str) -> str:
    mapping = {
        "starter": settings.stripe_price_starter,
        "growth": settings.stripe_price_growth,
        "pro": settings.stripe_price_pro,
    }
    price_id = (mapping.get(plan) or "").strip()
    if not price_id:
        raise RuntimeError(f"Stripe neconfigurat: lipsește STRIPE_PRICE pentru plan={plan}.")
    return price_id


def create_checkout_session(db: Session, *, user: User, plan: str) -> CheckoutResult:
    """
    Creează Checkout Session pentru un plan.
    Returnează (session_id, url) pentru redirect din UI.
    """
    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe neconfigurat: lipsește STRIPE_SECRET_KEY.")
    if not settings.stripe_checkout_success_url or not settings.stripe_checkout_cancel_url:
        raise RuntimeError("Stripe neconfigurat: lipsește STRIPE_CHECKOUT_SUCCESS_URL / STRIPE_CHECKOUT_CANCEL_URL.")

    stripe.api_key = settings.stripe_secret_key

    price_id = _get_price_id_for_plan(plan)
    customer_id = get_or_create_stripe_customer_id(db, user=user)

    success_url = _ensure_session_id_placeholder(settings.stripe_checkout_success_url.strip())
    cancel_url = settings.stripe_checkout_cancel_url.strip()

    # Trial doar pentru Growth/Pro (controlat din env)
    trial_days = int(settings.stripe_trial_days or 0) if plan in ("growth", "pro") else 0

    subscription_data: dict = {
        "metadata": {
            "app_user_id": str(user.id),
            "plan": plan,
        }
    }
    if trial_days > 0:
        subscription_data["trial_period_days"] = trial_days

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=str(user.id),
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "app_user_id": str(user.id),
            "plan": plan,
        },
        subscription_data=subscription_data,
    )

    if not session.url:
        raise RuntimeError("Stripe checkout URL missing (session.url is empty).")

    return CheckoutResult(session_id=str(session.id), url=str(session.url))
