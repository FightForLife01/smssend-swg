# FILE: app/deps/db.py
# Scop:
#   - Dependency standard pentru Session SQLAlchemy (per request).
#
# Debug:
#   - Dacă ai conexiuni blocate, verifică dacă requesturile se închid corect
#     și dacă ai vreun while/await care ține session deschis.

from typing import Generator
from sqlalchemy.orm import Session

from ..database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
