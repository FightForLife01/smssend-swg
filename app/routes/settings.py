# FILE: app/routes/settings.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..models import User
from ..schemas import SmsSettingsIn, SmsSettingsOut, SmsBalanceOut
from ..deps.auth import get_current_user
from ..deps.db import get_db
from ..services.audit import create_audit_log
from ..services.sms_service import get_sms_balance_for_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/sms", response_model=SmsSettingsOut)
def get_sms_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SmsSettingsOut(
        has_token=bool(current_user.smsapi_token),
        sender=current_user.smsapi_sender,
        company_name=current_user.sms_company_name,
    )


@router.post("/sms", response_model=SmsSettingsOut)
def update_sms_settings(
    data: SmsSettingsIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # token poate fi None/"" dacă userul nu vrea să îl schimbe
    token = (data.token or "").strip()
    sender = data.sender.strip()
    company_name = data.company_name.strip()

    if not sender:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expeditorul (sender) nu poate fi gol.",
        )
    if not company_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numele firmei pentru SMS nu poate fi gol.",
        )

    # Token obligatoriu doar dacă nu există deja salvat
    if token:
        current_user.smsapi_token = token
    elif not current_user.smsapi_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token SMSAPI este obligatoriu prima dată.",
        )

    current_user.smsapi_sender = sender
    current_user.sms_company_name = company_name
    db.commit()
    db.refresh(current_user)

    create_audit_log(
        db,
        "UPDATE_SMS_SETTINGS",
        current_user.id,
        request,
        details={
            "sender": sender,
            "company_name": company_name,
            "token_updated": bool(token),
        },
    )

    return SmsSettingsOut(
        has_token=bool(current_user.smsapi_token),
        sender=current_user.smsapi_sender,
        company_name=current_user.sms_company_name,
    )


@router.get("/sms/balance", response_model=SmsBalanceOut)
def get_sms_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok, points, error = get_sms_balance_for_user(current_user)
    if not ok:
        return SmsBalanceOut(ok=False, points=None, error=error)
    return SmsBalanceOut(ok=True, points=points, error=None)
