# FILE: app/schemas.py

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class UserRegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    accept_policy: bool


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    policy_version: Optional[str]
    policy_accepted_at: Optional[datetime]

    class Config:
        from_attributes = True


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OrderOut(BaseModel):
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

    class Config:
        from_attributes = True


class OrdersListOut(BaseModel):
    ok: bool
    total: int
    rows: List[OrderOut]


class SmsSettingsIn(BaseModel):
    token: str = Field(..., min_length=10, max_length=255)
    sender: str = Field(..., min_length=3, max_length=32)
    company_name: str = Field(..., min_length=2, max_length=255)


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
    id: int
    pnk: str
    review_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProductLinksListOut(BaseModel):
    ok: bool
    links: List[ProductLinkOut]
