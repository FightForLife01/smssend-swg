# FILE: app/routes/orders.py
# Scop:
#   - Upload Excel (import).
#   - Listare comenzi pentru user curent cu info SMS:
#       * sms_sent (pentru comanda curentă)
#       * previous_sms_count = câte SMS-uri de recenzie am trimis
#         pentru ACELAȘI telefon + ACELAȘI PNK (produs).

import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..models import User, Order, SmsLog
from ..schemas import OrdersListOut, OrderOut
from .auth import get_current_user, get_db
from ..services.orders_import import import_orders_from_excel
from ..services.audit import create_audit_log

router = APIRouter(prefix="/api/orders", tags=["orders"])

logger = logging.getLogger(__name__)


@router.post("/import")
def import_orders(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    try:
        inserted = import_orders_from_excel(db, user_id, file)
        create_audit_log(
            db,
            "UPLOAD_EXCEL",
            user_id,
            request,
            details={"inserted": inserted, "filename": file.filename},
        )
        return {"ok": True, "inserted": inserted}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Eroare la import_orders pentru user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import error: {exc}",
        )


@router.get("", response_model=OrdersListOut)
def list_orders(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 50

    q = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.id.desc())
    )
    total = q.count()
    orders = q.offset((page - 1) * page_size).limit(page_size).all()

    rows: list[OrderOut] = []
    for o in orders:
        # SMS trimis pentru comanda curentă (există log 'success' pentru acest order_id)
        sms_sent = any(log.status == "success" for log in o.sms_logs)

        phone = o.phone_number
        pnk = o.pnk
        previous_sms_count = 0

        # Istoric SMS recenzie = câte SMS-uri de succes pentru ACELAȘI telefon + ACELAȘI PNK
        if phone and pnk:
            total_for_phone_pnk = (
                db.query(SmsLog)
                .join(Order, SmsLog.order_id == Order.id)
                .filter(
                    SmsLog.user_id == current_user.id,
                    SmsLog.phone == str(phone),
                    SmsLog.status == "success",
                    Order.pnk == pnk,
                )
                .count()
            )
            # dacă pentru comanda curentă tocmai avem sms_sent=True, "previous" = total - 1
            previous_sms_count = max(0, total_for_phone_pnk - (1 if sms_sent else 0))

        row = OrderOut(
            id=o.id,
            order_number=o.order_number,
            order_date=o.order_date,
            product_name=o.product_name,
            pnk=o.pnk,
            phone_number=o.phone_number,
            order_status=o.order_status,
            payment_status=o.payment_status,
            sms_sent=sms_sent,
            previous_sms_count=previous_sms_count,
        )
        rows.append(row)

    return OrdersListOut(ok=True, total=total, rows=rows)
