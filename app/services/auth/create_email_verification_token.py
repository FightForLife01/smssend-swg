# FILE: app/services/auth/create_email_verification_token.py
# Scop:
#   - Creează token de verificare email (token brut trimis pe email, hash în DB).
#
# Debug:
#   - Dacă userul nu poate verifica, caută în DB:
#       SELECT * FROM email_verification_tokens WHERE user_id=...

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ...config import settings
from ...models import EmailVerificationToken
from ...security import generate_random_token, hash_token


def create_email_verification_token(db: Session, *, user_id: int) -> str:
    raw = generate_random_token(64)
    th = hash_token(raw)

    now = datetime.utcnow()
    expires = now + timedelta(minutes=settings.email_verify_token_expire_minutes)

    # curățăm token-uri vechi nefolosite pentru user (reduci suprafața)
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user_id,
        EmailVerificationToken.used_at.is_(None),
    ).delete()

    row = EmailVerificationToken(
        user_id=user_id,
        token_hash=th,
        created_at=now,
        expires_at=expires,
        used_at=None,
    )
    db.add(row)
    db.commit()

    return raw
