# FILE: app/routes/product_links.py
# Scop:
#   - CRUD simplu pentru maparea PNK → URL recenzie (per user).
#   - Validări stricte: PNK curat, URL sigur (fără script-uri).
#   - Pentru un PNK la un user există UN SINGUR rând.
#     La salvare se șterg toate mapările anterioare pentru acel PNK și se inserează una nouă.
#   - DELETE șterge complet asocierea PNK → URL pentru userul curent.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import User, ProductLink
from ..schemas import ProductLinkIn, ProductLinkOut, ProductLinksListOut
from .auth import get_current_user, get_db

router = APIRouter(prefix="/api/product-links", tags=["product-links"])


def _validate_pnk(pnk: str):
    if not pnk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PNK nu poate fi gol.",
        )
    if not all(ch.isalnum() for ch in pnk):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PNK poate conține doar litere și cifre (A-Z, 0-9).",
        )


def _validate_url(url: str):
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL trebuie să înceapă cu http:// sau https://",
        )
    lower_url = url.lower()
    if lower_url.startswith(("javascript:", "data:", "vbscript:")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL invalid.",
        )
    if "<" in url or ">" in url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL nu poate conține caractere HTML (< sau >).",
        )


@router.get("", response_model=ProductLinksListOut)
def list_product_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listă cu ultimele 10 mapări PNK → URL pentru userul curent.
    Folosită de UI în cardul de mapări.
    """
    links = (
        db.query(ProductLink)
        .filter(ProductLink.user_id == current_user.id)
        .order_by(ProductLink.created_at.desc())
        .limit(10)
        .all()
    )
    out = [ProductLinkOut.from_orm(l) for l in links]
    return ProductLinksListOut(ok=True, links=out)


@router.post("", response_model=ProductLinkOut)
def upsert_product_link(
    data: ProductLinkIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Salvează maparea PNK → URL recenzie pentru userul curent.
    Reguli:
      - PNK se normalizează la UPPERCASE.
      - Pentru (user_id, PNK) există EXACT un rând.
      - La salvare se șterg toate mapările existente pentru acel PNK și se inserează una nouă.
    """
    pnk = data.pnk.strip().upper()
    url = data.review_url.strip()

    _validate_pnk(pnk)
    _validate_url(url)

    # Ștergem toate mapările anterioare pentru acest user + PNK
    db.query(ProductLink).filter(
        ProductLink.user_id == current_user.id,
        ProductLink.pnk == pnk,
    ).delete()

    # Inserăm o singură mapare curentă
    link = ProductLink(
        user_id=current_user.id,
        pnk=pnk,
        review_url=url,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return ProductLinkOut.from_orm(link)


@router.delete("/{pnk}")
def delete_product_link(
    pnk: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Șterge complet asocierea PNK → URL pentru userul curent.
    """
    norm_pnk = pnk.strip().upper()
    _validate_pnk(norm_pnk)

    deleted = db.query(ProductLink).filter(
        ProductLink.user_id == current_user.id,
        ProductLink.pnk == norm_pnk,
    ).delete()

    db.commit()

    if deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nu există mapare pentru PNK {norm_pnk}.",
        )

    return {"ok": True, "deleted": deleted}
