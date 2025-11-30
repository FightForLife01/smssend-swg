# FILE: app/excel_loader.py
# Scop:
#   - Să citească toate fișierele .xlsx din ORDERS_FOLDER.
#   - Să mapeze coloanele exacte din Excel pe chei interne.
#   - Să întoarcă toate comenzile ca listă de dict-uri (tabel unificat),
#     fără valori NaN / pd.NA / Timestamp → convertite la tipuri JSON-safe.
#
# Debug:
#   - Dacă /local-orders dă 500 cu "NaN not JSON compliant", problema era aici.
#   - Acum orice NaN este convertit în None, iar datele de tip dată în ISO string.

from pathlib import Path
from typing import Any, Dict, List
import logging
import math
import datetime as dt

import pandas as pd

from .config import settings

logger = logging.getLogger(__name__)

# Mapare: nume coloană Excel → nume câmp intern în API
COLUMN_MAP: Dict[str, str] = {
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

# Ordinea câmpurilor în răspuns
CANONICAL_FIELDS: List[str] = list(COLUMN_MAP.values())


def _get_orders_folder() -> Path:
    """
    Returnează Path către folderul cu fișierele Excel.

    Ridică FileNotFoundError dacă folderul nu există,
    ca să vezi imediat problema în log / HTTP 500.
    """
    folder = Path(settings.orders_folder).resolve()
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folderul pentru comenzi nu există: {folder}")
    return folder


def get_excel_files() -> List[Path]:
    """
    Găsește toate fișierele .xlsx din ORDERS_FOLDER.
    Returnează o listă sortată de Path.
    """
    folder = _get_orders_folder()
    files = sorted(folder.glob("*.xlsx"))
    logger.info("Găsite %d fișiere .xlsx în %s", len(files), folder)
    return files


def _normalize_value(value: Any) -> Any:
    """
    Normalizează valorile din Pandas la ceva JSON-safe:

    - NaN / pd.NA / None → None
    - datetime / Timestamp → string ISO (ex: "2025-11-29T12:00:00")
    - restul sunt returnate ca atare (str, int, float etc.)
    """
    # direct None
    if value is None:
        return None

    # NaN float (clasica problemă)
    if isinstance(value, float) and math.isnan(value):
        return None

    # pd.NA / NaT / alte null-uri Pandas
    try:
        if pd.isna(value):
            return None
    except Exception:
        # dacă pd.isna dă eroare pe tipuri exotice, lăsăm valoarea așa
        pass

    # Datetime / Timestamp → ISO string
    if isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        return value.isoformat()

    return value


def load_orders_from_file(path: Path) -> List[Dict[str, Any]]:
    """
    Încarcă UN fișier Excel și îl transformă în listă de dict-uri.

    - Folosește header-ul de pe primul rând (exact coloanele date de tine).
    - Renumește coloanele conform COLUMN_MAP.
    - Returnează doar câmpurile CANONICAL_FIELDS.
    - Toate valorile sunt normalizate cu _normalize_value (fără NaN).
    """
    logger.info("Încarc fișierul Excel: %s", path)

    try:
        df = pd.read_excel(path)
    except Exception as exc:
        logger.error("Eroare la citirea fișierului %s: %s", path, exc)
        raise RuntimeError(f"Eroare la citirea fișierului {path}: {exc}")

    # Normalizăm numele coloanelor (strip spații)
    df.columns = [str(c).strip() for c in df.columns]

    # Detectăm coloane lipsă
    missing_cols = [col for col in COLUMN_MAP.keys() if col not in df.columns]
    if missing_cols:
        logger.warning(
            "Fișierul %s nu conține toate coloanele așteptate. Lipsesc: %s",
            path,
            ", ".join(missing_cols),
        )

    # Renumim coloanele existente după mapare
    rename_map = {
        col_excel: COLUMN_MAP[col_excel]
        for col_excel in COLUMN_MAP
        if col_excel in df.columns
    }
    df = df.rename(columns=rename_map)

    records: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        rec: Dict[str, Any] = {}
        for field in CANONICAL_FIELDS:
            raw_value = row.get(field, None)
            rec[field] = _normalize_value(raw_value)
        records.append(rec)

    logger.info("Fișierul %s → %d rânduri procesate", path.name, len(records))
    return records


def load_all_orders() -> List[Dict[str, Any]]:
    """
    Încarcă toate fișierele .xlsx din ORDERS_FOLDER și concatenează rândurile.

    Dacă un fișier e corupt sau nu se poate citi → excepție,
    ca să vezi imediat în API unde e problema.
    """
    all_rows: List[Dict[str, Any]] = []
    files = get_excel_files()

    for path in files:
        rows = load_orders_from_file(path)
        all_rows.extend(rows)

    logger.info("Total rânduri agregate din toate fișierele: %d", len(all_rows))
    return all_rows
