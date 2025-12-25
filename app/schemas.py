# FILE: app/schemas.py
# Scop:
#   - Schemas Pydantic (FastAPI).
#   - Validări enterprise pentru register (confirm password, firmă⇒CUI).
#
# Billing:
#   - Adăugăm schema pentru /api/billing/checkout (Pasul 2.1).
#
# Debug:
#   - Validările critice se fac SERVER-SIDE. Front-ul doar ajută UX-ul.

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator, field_validator


class RegisterOut(BaseModel):
    ok: bool = True
    message: str


class UserRegisterIn(BaseModel):
    email: EmailStr

    first_name: str = Field(..., min_length=2, max_length=128)
    last_name: str = Field(..., min_length=2, max_length=128)

    # Firma (opțional)
    company_name: Optional[str] = Field(default=None, max_length=255)
    company_cui: Optional[str] = Field(default=None, max_length=32)

    # Adresă (obligatorie)
    street: str = Field(..., min_length=2, max_length=255)
    street_no: str = Field(..., min_length=1, max_length=32)
    locality: str = Field(..., min_length=2, max_length=128)
    county: str = Field(..., min_length=2, max_length=128)
    postal_code: str = Field(..., min_length=2, max_length=32)
    country: str = Field(..., min_length=2, max_length=64)

    # Parolă
    password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str = Field(..., min_length=12, max_length=128)

    accept_policy: bool

    @field_validator(
        "first_name",
        "last_name",
        "company_name",
        "company_cui",
        "street",
        "street_no",
        "locality",
        "county",
        "postal_code",
        "country",
        mode="before",
    )
    @classmethod
    def _strip_strings(cls, v):
        if v is None:
            return None
        return str(v).strip()

    @model_validator(mode="after")
    def _validate_register_rules(self):
        if not self.accept_policy:
            raise ValueError("Trebuie să accepți politica aplicației pentru a continua.")

        if self.password != self.confirm_password:
            raise ValueError("Parolele nu coincid.")

        # Regula firmă ⇒ CUI (și invers, ca să evităm stări invalide)
        if (self.company_name and not self.company_cui) or (self.company_cui and not self.company_name):
            raise ValueError("Dacă completezi firma, CUI este obligatoriu (și invers).")

        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("password", mode="before")
    @classmethod
    def _strip_pw(cls, v):
        return str(v) if v is not None else ""


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr

    first_name: str
    last_name: str

    company_name: Optional[str]
    company_cui: Optional[str]

    street: str
    street_no: str
    locality: str
    county: str
    postal_code: str
    country: str

    role: str
    is_active: bool
    email_verified_at: Optional[datetime]

    policy_version: Optional[str]
    policy_accepted_at: Optional[datetime]

    created_at: datetime
    last_login_at: Optional[datetime]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: Optional[str | int | float]
    order_date: Optional[datetime | str]
    product_name: Optional[str]
    pnk: Optional[str]
    phone_number: Optional[str | int | float]
    order_status: Optional[str]
    payment_status: Optional[str]
    sms_sent: bool = False
    previous_sms_count: int = 0


class OrdersListOut(BaseModel):
    ok: bool
    total: int
    rows: List[OrderOut]


class SmsSettingsIn(BaseModel):
    # token poate fi None/"" la update dacă e deja setat (backend decide)
    token: Optional[str] = Field(default=None, max_length=255)
    sender: str = Field(..., min_length=3, max_length=32)
    company_name: str = Field(..., min_length=2, max_length=255)

    @field_validator("token", mode="before")
    @classmethod
    def _strip_token(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @field_validator("sender", "company_name", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return str(v).strip()


class SmsSettingsOut(BaseModel):
    has_token: bool
    sender: Optional[str]
    company_name: Optional[str]


class SmsBalanceOut(BaseModel):
    ok: bool
    points: Optional[float] = None
    error: Optional[str] = None


class SmsStatsOut(BaseModel):
    total_sent_success: int
    total_sent_error: int
    last_sent_at: Optional[datetime]


class ProductLinkIn(BaseModel):
    pnk: str = Field(..., min_length=3, max_length=64)
    review_url: str = Field(..., min_length=10)


class ProductLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pnk: str
    review_url: str
    created_at: datetime


class ProductLinksListOut(BaseModel):
    ok: bool
    links: List[ProductLinkOut]


# =========================
# Billing (Stripe) - Pasul 2.1
# =========================
class BillingCheckoutIn(BaseModel):
    """
    Cerere creare Stripe Checkout Session (subscription).

    plan:
      - starter: fără trial
      - growth/pro: trial (configurat din env: STRIPE_TRIAL_DAYS)
    """
    plan: Literal["starter", "growth", "pro"]


class BillingCheckoutOut(BaseModel):
    """
    Răspuns minimal pentru UI:
      - url: redirect la Stripe Checkout hosted page
      - session_id: util pentru debug/audit
    """
    ok: bool = True
    url: str
    session_id: str
