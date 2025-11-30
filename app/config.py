# FILE: app/config.py
# Scop:
#   - Centralizează setările aplicației (DB, SMS, policy).
#   - Citește .env și expune "settings" folosit în restul codului.

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # încarcă .env din root-ul proiectului


@dataclass
class Settings:
    # DB – pentru dev folosim SQLite; ușor de mutat ulterior pe Postgres/MariaDB.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

    # Folder bază pentru fișiere temporare (upload Excel).
    uploads_tmp_dir: str = os.getenv("UPLOADS_TMP_DIR", "./data/tmp")

    # Fallback global SMSAPI (opțional, dacă userul nu are propriile credențiale).
    smsapi_token: str = os.getenv("SMSAPI_TOKEN", "")
    smsapi_sender: str = os.getenv("SMSAPI_SENDER", "")

    # Politica aplicației (versiune)
    policy_version: str = os.getenv("POLICY_VERSION", "1.0")

    # Debug flag
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
