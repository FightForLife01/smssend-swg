# FILE: app/security.py
# Scop:
#   - Gestionare parole (hash + verificare) folosind Argon2.
#   - Generare și validare token-uri JWT pentru autentificare.
#
# Mecanism:
#   - hash_password(parola_raw) -> Argon2
#   - verify_password(parola_raw, hash) -> True/False
#
# JWT:
#   - HS256, secret din .env (JWT_SECRET)
#   - expirare 12 ore (configurabilă)

import os
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

# ==========================
# Config parole – Argon2
# ==========================

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
  """
  Generează hash pentru parolă folosind Argon2.
  Acceptă parole lungi și complexe fără limitări artificiale.
  """
  if not isinstance(password, str):
      password = str(password)
  return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
  """
  Verifică o parolă brută față de hash-ul salvat.
  """
  if not isinstance(plain_password, str):
      plain_password = str(plain_password)
  return pwd_context.verify(plain_password, password_hash)


# ==========================
# Config JWT
# ==========================

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PROD")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 ore


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
  """
  Creează un JWT cu payload-ul dat.
  - data: dicționar cu câmpuri custom (ex: {"sub": user_id}).
  - expires_delta: override pentru expirare; dacă nu, folosește 12h default.
  """
  to_encode = data.copy()
  now = datetime.utcnow()
  if expires_delta is None:
      expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  expire = now + expires_delta

  to_encode.update({"exp": expire, "iat": now})
  encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
  return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
  """
  Decodează și validează un JWT.
  - Returnează payload-ul dacă token-ul este valid și neexpirat.
  - Returnează None dacă este invalid / expirat.
  """
  try:
      payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
      return payload
  except JWTError:
      return None
