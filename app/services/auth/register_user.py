# FILE: app/services/auth/register_user.py
# Scop:
#   - Register enterprise: validări + dedup email + token verify + audit.
#
# Anti-enumerare:
#   - Dacă email există, returnăm mesaj generic (nu confirmăm).
#
# Debug:
#   - Dacă primești IntegrityError pe email_normalized, verifică normalize_email() + UNIQUE.

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import Request

from ...config import settings
from ...models import User
from ...schemas import UserRegisterIn, RegisterOut
from ...security import hash_password
from ..audit import create_audit_log

from .normalize_email import normalize_email
from .validate_password import validate_password_or_raise
from .enforce_rate_limit import enforce_rate_limit_or_raise
from .create_email_verification_token import create_email_verification_token
from .send_verification_email import send_verification_email


def register_user(db: Session, *, data: UserRegisterIn, request: Request) -> RegisterOut:
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent")

    # Rate limit pe IP (register)
    enforce_rate_limit_or_raise(
        db,
        key=f"register:ip:{ip}",
        max_count=settings.register_max_attempts_ip,
        window_seconds=settings.register_window_seconds_ip,
        block_seconds=settings.register_block_seconds_ip,
    )

    email_norm = normalize_email(data.email)

    # Parolă enterprise
    validate_password_or_raise(
        data.password,
        email=email_norm,
        first_name=data.first_name,
        last_name=data.last_name,
    )

    # Dacă există deja => mesaj generic (anti-enumerare)
    existing = db.query(User).filter(User.email_normalized == email_norm).first()
    if existing:
        create_audit_log(db, "REGISTER_DUPLICATE", existing.id, request, details={"email": email_norm})
        return RegisterOut(
            ok=True,
            message="Dacă emailul este valid, vei primi instrucțiuni. Dacă ai deja cont, folosește login/resetare parolă.",
        )

    now = datetime.utcnow()

    user = User(
        email=email_norm,  # stocăm consistent
        email_normalized=email_norm,
        password_hash=hash_password(data.password),

        first_name=data.first_name,
        last_name=data.last_name,

        company_name=(data.company_name or None),
        company_cui=(data.company_cui or None),

        street=data.street,
        street_no=data.street_no,
        locality=data.locality,
        county=data.county,
        postal_code=data.postal_code,
        country=data.country,

        role="user",
        is_active=True,
        email_verified_at=None,

        failed_login_count=0,
        locked_until=None,

        policy_version=settings.policy_version,
        policy_accepted_at=now,
        created_at=now,
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # și aici răspuns generic (anti-enumerare)
        create_audit_log(db, "REGISTER_RACE_DUPLICATE", None, request, details={"email": email_norm})
        return RegisterOut(
            ok=True,
            message="Dacă emailul este valid, vei primi instrucțiuni. Dacă ai deja cont, folosește login/resetare parolă.",
        )

    db.refresh(user)

    # token verificare email
    token = create_email_verification_token(db, user_id=user.id)

    # trimitem email (în prod obligatoriu să funcționeze)
    send_verification_email(to_email=user.email, token=token)

    create_audit_log(
        db,
        "REGISTER",
        user.id,
        request,
        details={"email": email_norm, "ip": ip, "ua": ua},
    )

    return RegisterOut(
        ok=True,
        message="Cont creat. Verifică emailul pentru confirmare înainte de login.",
    )
