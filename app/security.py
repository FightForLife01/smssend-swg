# FILE: app/security.py
# Scop:
#   - Parole: Argon2 + pepper (secret separat de DB).
#   - JWT access token scurt (15m default), cu issuer/audience + jti.
#   - Token hashing pentru refresh/verify (stocăm DOAR hash în DB).
#
# Debug avansat:
#   - verify_password suportă "legacy" (fără pepper) ca să nu-ți blochezi userii existenți.
#   - dacă JWT decode eșuează frecvent, verifică JWT_SECRET + clock drift pe VPS.

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from uuid import uuid4

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def _pepper_password(password: str) -> str:
    """
    Concatenează pepper la parolă.
    Pepper = secret din env (NU în DB).
    """
    if not isinstance(password, str):
        password = str(password)
    return f"{password}{settings.password_pepper}"


def hash_password(password: str) -> str:
    """
    Hash Argon2 pentru parolă, folosind pepper.
    """
    return pwd_context.hash(_pepper_password(password))


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verificare parolă cu fallback legacy (fără pepper).
    Motiv:
      - tranziție sigură pentru useri existenți.
    """
    try:
        # Primul încercăm varianta nouă (cu pepper).
        if settings.password_pepper and pwd_context.verify(_pepper_password(plain_password), password_hash):
            return True
    except Exception:
        pass

    # Legacy fallback (DB vechi, fără pepper).
    try:
        return pwd_context.verify(str(plain_password), password_hash)
    except Exception:
        return False


def needs_password_rehash(password_hash: str) -> bool:
    """
    Dacă parametrii Argon2 s-au schimbat, putem rehash-ui la următorul login.
    """
    try:
        return pwd_context.needs_update(password_hash)
    except Exception:
        return False


JWT_ALGORITHM = "HS256"


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Creează JWT access token.
    În payload punem:
      - sub: user_id
      - jti: id unic (audit/revocare viitoare)
      - iss/aud: protecție anti token reuse între sisteme
      - iat/exp: timp
    """
    to_encode = dict(data)
    now = datetime.utcnow()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    exp = now + expires_delta
    to_encode.update(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": str(uuid4()),
            "typ": "access",
        }
    )

    return jwt.encode(to_encode, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode + verify JWT.
    Returnează payload sau None dacă invalid/expirat.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
        return payload
    except JWTError:
        return None


def generate_random_token(length: int = 64) -> str:
    """
    Token random URL-safe.
    Folosit pentru refresh tokens și email verification tokens.
    """
    # secrets.token_urlsafe(n) ≈ n bytes; pentru ~64 chars, dăm 48 bytes.
    return secrets.token_urlsafe(max(32, length))


def hash_token(token: str) -> str:
    """
    Hash SHA-256(token + TOKEN_PEPPER).
    În DB salvăm doar hash-ul.
    """
    raw = f"{token}{settings.token_pepper}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    """
    Comparație constant-time (evită timing leaks).
    """
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
