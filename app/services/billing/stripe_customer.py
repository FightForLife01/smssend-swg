# FILE: app/services/billing/stripe_customer.py
# Scop:
#   - Creează / recuperează Stripe Customer pentru user (1:1).
#   - Persistă stripe_customer_id în DB pe tabela users.
#
# De ce așa:
#   - Portalul Stripe și webhooks au nevoie de "customer" ca pivot.
#   - Evităm să lucrăm cu customer_email ca identitate (email se poate schimba).
#
# Debug / depanare:
#   - Dacă Stripe dă eroare, verifică STRIPE_SECRET_KEY și conectivitatea.
#   - Dacă în DB rămâne NULL, verifică dacă ai rulat ALTER TABLE pe users.
#   - Dacă ai customers multipli pentru același user, verifică audit logs.

import stripe
from sqlalchemy.orm import Session

from ...config import settings
from ...models import User


def get_or_create_stripe_customer_id(db: Session, *, user: User) -> str:
    """
    Returnează stripe_customer_id din DB sau creează un customer nou în Stripe.

    IMPORTANT:
      - setăm stripe.api_key din settings la fiecare apel (claritate și izolare).
      - commit DB imediat după creare, ca să nu pierdem mapping-ul dacă ulterior checkout eșuează.
    """
    if user.stripe_customer_id:
        return str(user.stripe_customer_id)

    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe neconfigurat: lipsește STRIPE_SECRET_KEY.")

    stripe.api_key = settings.stripe_secret_key

    full_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() or None

    customer = stripe.Customer.create(
        email=str(user.email),
        name=full_name,
        metadata={
            "app_user_id": str(user.id),
            "app": "smssend-by-swg",
        },
    )

    user.stripe_customer_id = str(customer.id)
    db.commit()
    db.refresh(user)

    return str(customer.id)
