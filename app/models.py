# FILE: app/models.py
# Scop:
#   - Modele DB: User, Order, ProductLink, SmsLog, AuditLog + auth tokens + rate-limit state.
#
# Observații enterprise:
#   - email_normalized are UNIQUE => previne dubluri (case-insensitive).
#   - firmă/CUI: CHECK => fie ambele NULL, fie ambele NOT NULL.
#   - refresh/email tokens: stocăm doar HASH (nu token brut).
#
# Stripe:
#   - user.stripe_customer_id este pivotul pentru Checkout/Portal/Webhooks.
#   - dacă DB existentă nu are coloana, trebuie ALTER TABLE (vezi pașii de după cod).

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    DECIMAL,
    Boolean,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(company_name IS NULL AND company_cui IS NULL) OR (company_name IS NOT NULL AND company_cui IS NOT NULL)",
            name="ck_users_company_pair",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Email
    email = Column(String(255), unique=True, nullable=False, index=True)
    email_normalized = Column(String(255), unique=True, nullable=False, index=True)

    # Parolă (argon2 hash)
    password_hash = Column(String(255), nullable=False)

    # Identitate
    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)

    # Firma (opțional) – cu constrângere CHECK
    company_name = Column(String(255), nullable=True)
    company_cui = Column(String(32), nullable=True)

    # Adresă (cerută la register)
    street = Column(String(255), nullable=False)
    street_no = Column(String(32), nullable=False)
    locality = Column(String(128), nullable=False)
    county = Column(String(128), nullable=False)
    postal_code = Column(String(32), nullable=False)
    country = Column(String(64), nullable=False)

    # Security / status
    role = Column(String(32), default="user", nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified_at = Column(DateTime, nullable=True)

    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Politică / GDPR
    policy_version = Column(String(16), nullable=True)
    policy_accepted_at = Column(DateTime, nullable=True)

    # Config SMS per user
    smsapi_token = Column(String(255), nullable=True)
    smsapi_sender = Column(String(32), nullable=True)
    sms_company_name = Column(String(255), nullable=True)

    # =========================
    # Stripe (Billing)
    # =========================
    # stripe_customer_id:
    # - creat o singură dată în Stripe pentru fiecare user
    # - reutilizat pentru Checkout/Portal/Webhooks mapping
    #
    # Debug:
    # - dacă "no such column users.stripe_customer_id" => nu ai făcut ALTER TABLE.
    stripe_customer_id = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    orders = relationship("Order", back_populates="user")
    sms_logs = relationship("SmsLog", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    product_links = relationship("ProductLink", back_populates="user")

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    email_verification_tokens = relationship("EmailVerificationToken", back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    replaced_by_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)

    ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    token_hash = Column(String(64), unique=True, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="email_verification_tokens")


class RateLimitState(Base):
    """
    Rate limit simplu, DB-backed.
    Key examples:
      - "login:ip:1.2.3.4"
      - "login:email:user@example.com"
      - "register:ip:1.2.3.4"
    """
    __tablename__ = "rate_limits"

    key = Column(String(160), primary_key=True)

    window_started_at = Column(DateTime, nullable=False)
    count = Column(Integer, nullable=False, default=0)

    blocked_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    order_number = Column(String(64), index=True)
    order_date = Column(DateTime, nullable=True)
    awb_number = Column(String(64), nullable=True)
    product_name = Column(Text, nullable=True)
    product_code = Column(String(64), nullable=True)
    pnk = Column(String(64), nullable=True)
    serial_numbers = Column(Text, nullable=True)

    quantity = Column(DECIMAL(10, 2), nullable=True)
    unit_price_without_vat = Column(DECIMAL(10, 2), nullable=True)
    total_price_with_vat = Column(DECIMAL(10, 2), nullable=True)
    currency = Column(String(8), nullable=True)
    vat = Column(DECIMAL(5, 2), nullable=True)

    order_status = Column(String(64), nullable=True)
    payment_method = Column(String(64), nullable=True)
    delivery_method = Column(String(64), nullable=True)
    delivery_point_external_id = Column(String(64), nullable=True)
    delivery_point_name = Column(String(255), nullable=True)
    payment_status = Column(String(64), nullable=True)

    max_completion_date = Column(DateTime, nullable=True)
    max_handover_date = Column(DateTime, nullable=True)

    customer_name = Column(String(255), nullable=True)
    legal_person = Column(String(64), nullable=True)
    vat_number = Column(String(64), nullable=True)
    phone_number = Column(String(64), nullable=True)

    delivery_name = Column(String(255), nullable=True)
    delivery_phone = Column(String(64), nullable=True)
    delivery_address = Column(Text, nullable=True)
    delivery_postal_code = Column(String(32), nullable=True)

    billing_name = Column(String(255), nullable=True)
    billing_address = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    sms_logs = relationship("SmsLog", back_populates="order")


class ProductLink(Base):
    __tablename__ = "product_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pnk = Column(String(64), nullable=False)
    review_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="product_links")


class SmsLog(Base):
    __tablename__ = "sms_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    phone = Column(String(64), nullable=False)
    message_id = Column(String(128), nullable=True)
    status = Column(String(32), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sms_logs")
    order = relationship("Order", back_populates="sms_logs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


class PasswordResetToken(Base):
    """
    Token de resetare parolă (stocăm doar hash).
    - token brut: 8 caractere (A-Z, 2-9 fără caractere ambigue)
    - TTL scurt (ex: 15 minute)
    - one-time use (used_at)
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    token_hash = Column(String(64), unique=True, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True, index=True)
