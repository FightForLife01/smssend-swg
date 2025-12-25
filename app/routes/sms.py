# FILE: app/routes/sms.py
# Scop:
#   - Trimite SMS pentru o comandă folosind linkul de recenzie mapat la PNK.
#   - Textul SMS include numele firmei din setări.
#   - NU permite mai mult de un SMS de recenzie pentru aceeași pereche (telefon, PNK).
#   - Statistici globale SMS per user.

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import User, Order, SmsLog, ProductLink
from ..deps.auth import get_current_user
from ..deps.db import get_db
from ..services.sms_service import send_sms_for_order
from ..services.audit import create_audit_log
from ..schemas import SmsStatsOut

router = APIRouter(prefix="/api/sms", tags=["sms"])


@router.post("/order/{order_id}")
def send_sms_for_order_route(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trimite un SMS pentru comanda dată.
    Reguli:
      - Comanda trebuie să aibă PNK.
      - User-ul trebuie să aibă nume firmă setat.
      - Trebuie să existe mapare PNK → URL recenzie în ProductLink.
      - NU trimitem SMS dacă pentru acest telefon + PNK există deja un SMS de recenzie
        cu status 'success' (ca să nu bombardăm clientul cu solicitări pentru același produs).
    """
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comanda nu există",
        )

    if not order.pnk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comanda nu are PNK, nu pot identifica produsul.",
        )

    if not current_user.sms_company_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Nu poți trimite SMS-uri până nu setezi numele firmei pentru mesaj. "
                "Adaugă numele firmei tale în cardul 'Setări SMSAPI'."
            ),
        )

    # Telefonul folosit în SMS
    phone = order.phone_number or order.delivery_phone
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comanda nu are număr de telefon, nu pot trimite SMS.",
        )

    # Mapare PNK → URL recenzie
    link = (
        db.query(ProductLink)
        .filter(
            ProductLink.user_id == current_user.id,
            ProductLink.pnk == order.pnk,
        )
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nu există link de recenzie configurat pentru produsul cu PNK {order.pnk}. "
                "Adaugă-l în cardul 'Linkuri produse eMAG (PNK → URL recenzie)'."
            ),
        )

    # Verificare anti-spam: a mai primit acest client (telefon) SMS de recenzie pentru acest PNK?
    already_sent_for_product = (
        db.query(SmsLog)
        .join(Order, SmsLog.order_id == Order.id)
        .filter(
            SmsLog.user_id == current_user.id,
            SmsLog.phone == str(phone),
            SmsLog.status == "success",
            Order.pnk == order.pnk,
        )
        .count()
    )
    if already_sent_for_product > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Această combinație client + produs a mai primit deja un SMS de recenzie "
                f"(telefon {phone}, PNK {order.pnk}). "
                "Nu trimitem SMS-uri de recenzie duplicate pentru același produs."
            ),
        )

    review_url = link.review_url
    company = current_user.sms_company_name

    message_text = (
        f"Bună ziua, suntem echipa de la {company} și vă mulțumim pentru comanda dvs. "
        "Recent ați cumpărat un produs de la noi și ne-ar ajuta mult feedback-ul dvs. despre produs. "
        f"Puteți lăsa o recenzie aici: [%goto:{review_url}%] "
        "Acest mesaj este trimis punctual doar clienților care au plasat comenzi, nu este o campanie generală de marketing."
    )

    success, info = send_sms_for_order(db, current_user, order, message_text)

    create_audit_log(
        db,
        "SEND_SMS",
        current_user.id,
        request,
        details={
            "order_id": order_id,
            "success": success,
            "info": info,
            "review_url": review_url,
            "company_name": company,
            "phone": str(phone),
            "pnk": order.pnk,
        },
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Eroare SMS: {info}",
        )

    return {"ok": True, "message_id": info}


@router.get("/stats", response_model=SmsStatsOut)
def sms_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_q = db.query(SmsLog).filter(SmsLog.user_id == current_user.id)
    total_success = base_q.filter(SmsLog.status == "success").count()
    total_error = base_q.filter(SmsLog.status == "error").count()
    last_sent_at = (
        db.query(func.max(SmsLog.created_at))
        .filter(SmsLog.user_id == current_user.id)
        .scalar()
    )

    return SmsStatsOut(
        total_sent_success=total_success,
        total_sent_error=total_error,
        last_sent_at=last_sent_at,
    )
