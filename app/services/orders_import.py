# FILE: app/services/orders_import.py
# Scop:
#   - Importă Excel-ul eMAG în tabela Orders, pentru user-ul curent.
#   - Verifică fișierul, normalizează datele și șterge fișierul temporar.

from pathlib import Path

import logging
import math
import datetime as dt

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Order

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "Nr. comanda": "order_number",
    "Data comenzii": "order_date",
    "Numar AWB": "awb_number",
    "Nume produs": "product_name",
    "Cod produs": "product_code",
    "PNK": "pnk",
    "Serial numbers": "serial_numbers",
    "Cantitate": "quantity",
    "Pret fara TVA/buc": "unit_price_without_vat",
    "Pret total cu TVA": "total_price_with_vat",
    "Moneda": "currency",
    "TVA": "vat",
    "Status comanda": "order_status",
    "Mod plata": "payment_method",
    "Mod livrare": "delivery_method",
    "ID extern punct de livrare": "delivery_point_external_id",
    "Denumire punct de livrare": "delivery_point_name",
    "Status plata": "payment_status",
    "Data maxima finalizare": "max_completion_date",
    "Data maxima de predare": "max_handover_date",
    "Nume client": "customer_name",
    "Persoana juridica": "legal_person",
    "Numar VAT": "vat_number",
    "Numar telefon": "phone_number",
    "Nume livrare": "delivery_name",
    "Telefon livrare": "delivery_phone",
    "Adresa de livrare": "delivery_address",
    "Cod postal de livrare": "delivery_postal_code",
    "Nume facturare": "billing_name",
    "Adresa de facturare": "billing_address",
}

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB


def _save_tmp_file(upload: UploadFile) -> Path:
    uploads_dir = Path(settings.uploads_tmp_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = uploads_dir / upload.filename
    content = upload.file.read()
    size = len(content)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fișier prea mare (> {MAX_UPLOAD_BYTES} bytes)",
        )
    with tmp_path.open("wb") as f:
        f.write(content)
    upload.file.seek(0)
    return tmp_path


def _normalize_datetime(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time())
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        try:
            return pd.to_datetime(v).to_pydatetime()
        except Exception:
            return None
    return None


def _clean_number(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _clean_text(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    s = str(value).strip()
    return s or None


def import_orders_from_excel(db: Session, user_id: int, upload: UploadFile) -> int:
    if not upload.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Acceptăm doar fișiere .xlsx",
        )

    tmp_path: Path | None = None
    try:
        tmp_path = _save_tmp_file(upload)
        df = pd.read_excel(tmp_path)
        df.columns = [str(c).strip() for c in df.columns]

        # verificăm formule
        for col in df.columns:
            if df[col].dtype == "object":
                if df[col].astype(str).str.startswith("=").any():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Fișierul conține formule în coloana '{col}'. Exportă din eMAG fără formule.",
                    )

        rename_map = {col: COLUMN_MAP[col] for col in COLUMN_MAP if col in df.columns}
        df = df.rename(columns=rename_map)

        db.query(Order).filter(Order.user_id == user_id).delete()

        inserted = 0
        for _, row in df.iterrows():
            o = Order(
                user_id=user_id,
                order_number=_clean_text(row.get("order_number")),
                order_date=_normalize_datetime(row.get("order_date")),
                awb_number=_clean_text(row.get("awb_number")),
                product_name=_clean_text(row.get("product_name")),
                product_code=_clean_text(row.get("product_code")),
                pnk=_clean_text(row.get("pnk")),
                serial_numbers=_clean_text(row.get("serial_numbers")),
                quantity=_clean_number(row.get("quantity")),
                unit_price_without_vat=_clean_number(row.get("unit_price_without_vat")),
                total_price_with_vat=_clean_number(row.get("total_price_with_vat")),
                currency=_clean_text(row.get("currency")),
                vat=_clean_number(row.get("vat")),
                order_status=_clean_text(row.get("order_status")),
                payment_method=_clean_text(row.get("payment_method")),
                delivery_method=_clean_text(row.get("delivery_method")),
                delivery_point_external_id=_clean_text(row.get("delivery_point_external_id")),
                delivery_point_name=_clean_text(row.get("delivery_point_name")),
                payment_status=_clean_text(row.get("payment_status")),
                max_completion_date=_normalize_datetime(row.get("max_completion_date")),
                max_handover_date=_normalize_datetime(row.get("max_handover_date")),
                customer_name=_clean_text(row.get("customer_name")),
                legal_person=_clean_text(row.get("legal_person")),
                vat_number=_clean_text(row.get("vat_number")),
                phone_number=_clean_text(row.get("phone_number")),
                delivery_name=_clean_text(row.get("delivery_name")),
                delivery_phone=_clean_text(row.get("delivery_phone")),
                delivery_address=_clean_text(row.get("delivery_address")),
                delivery_postal_code=_clean_text(row.get("delivery_postal_code")),
                billing_name=_clean_text(row.get("billing_name")),
                billing_address=_clean_text(row.get("billing_address")),
            )
            db.add(o)
            inserted += 1

        db.commit()
        logger.info("Import Excel reușit: user_id=%s, inserted=%s", user_id, inserted)
        return inserted

    finally:
        try:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            logger.warning("Nu am putut șterge fișierul temporar %s: %s", tmp_path, e)
