# FILE: app/services/auth/verify_email.py
# Scop:
#   - Confirmare email pe baza tokenului.
#
# Debug:
#   - Dacă token invalid: verifică hash_token + TOKEN_PEPPER + expirare + used_at.

from datetime import datetime
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from ...models import EmailVerificationToken, User
from ...security import hash_token
from ..audit import create_audit_log


def verify_email(db: Session, *, request: Request, token: str) -> None:
    if not token or len(token) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid.")

    now = datetime.utcnow()
    th = hash_token(token)

    row = db.query(EmailVerificationToken).filter(EmailVerificationToken.token_hash == th).first()
    if not row or row.used_at or row.expires_at <= now:
        create_audit_log(db, "EMAIL_VERIFY_FAIL", None, request, details={"reason": "invalid_or_expired"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid sau expirat.")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or not user.is_active:
        create_audit_log(db, "EMAIL_VERIFY_FAIL", row.user_id, request, details={"reason": "user_invalid"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalid.")

    if user.email_verified_at:
        # idempotent: dacă e deja verificat, doar marcăm tokenul ca folosit
        row.used_at = now
        db.commit()
        create_audit_log(db, "EMAIL_VERIFY_ALREADY", user.id, request, details=None)
        return

    user.email_verified_at = now
    row.used_at = now
    db.commit()

    create_audit_log(db, "EMAIL_VERIFY_SUCCESS", user.id, request, details={"email": user.email})
