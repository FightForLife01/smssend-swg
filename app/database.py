# FILE: app/database.py
# Scop:
#   - Creează engine SQLAlchemy și SessionLocal.
#   - Asigură directorul data/ există pentru SQLite.

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

# Asigurăm folderul data/
data_dir = Path("./data")
data_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
