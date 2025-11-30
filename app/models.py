# FILE: app/models.py
# Scop:
#   - Modele DB: User, Order, ProductLink, SmsLog, AuditLog.

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
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)

    # Politică / GDPR
    policy_version = Column(String(16), nullable=True)
    policy_accepted_at = Column(DateTime, nullable=True)

    # Config SMS per user
    smsapi_token = Column(String(255), nullable=True)
    smsapi_sender = Column(String(32), nullable=True)
    sms_company_name = Column(String(255), nullable=True)  # numele firmei folosit în textul SMS

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    orders = relationship("Order", back_populates="user")
    sms_logs = relationship("SmsLog", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    product_links = relationship("ProductLink", back_populates="user")


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
    status = Column(String(32), nullable=True)  # success / error / etc.
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
