# FILE: app/config.py
# Scop:
#   - Setări centralizate, fără fallback-uri periculoase în producție.
#   - Control pentru cookies, JWT, SMTP, rate-limit și lockout.
#   - Stripe Billing (Checkout/Portal/Webhooks) - pas cu pas.
#
# Debug avansat:
#   - Dacă pornește prod fără JWT_SECRET / TOKEN_PEPPER / PASSWORD_PEPPER => blocăm startup.
#   - Dacă Stripe nu merge: verifică STRIPE_SECRET_KEY + price IDs + URL-urile success/cancel.

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # încarcă .env din root-ul proiectului


def _get_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() == "true"


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return int(default)


@dataclass
class Settings:
    # DB
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

    # DEV bootstrap (în prod: false + migrații)
    db_auto_create: bool = _get_bool("DB_AUTO_CREATE", "true")

    # Uploads
    uploads_tmp_dir: str = os.getenv("UPLOADS_TMP_DIR", "./data/tmp")

    # Pentru excel_loader.py (dacă îl folosești vreodată)
    orders_folder: str = os.getenv("ORDERS_FOLDER", "./data/orders")

    # SMS
    smsapi_token: str = os.getenv("SMSAPI_TOKEN", "")
    smsapi_sender: str = os.getenv("SMSAPI_SENDER", "")

    # =========================
    # Stripe Billing (Subscriptions)
    # =========================
    # IMPORTANT:
    # - staging: chei TEST (sk_test_...)
    # - prod: chei LIVE (sk_live_...)
    #
    # Debug:
    # - Dacă primești "Stripe neconfigurat", verifică .env + load_dotenv() (rulezi din root).
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")  # folosit mai târziu la webhooks

    stripe_price_starter: str = os.getenv("STRIPE_PRICE_STARTER", "")
    stripe_price_growth: str = os.getenv("STRIPE_PRICE_GROWTH", "")
    stripe_price_pro: str = os.getenv("STRIPE_PRICE_PRO", "")

    stripe_checkout_success_url: str = os.getenv("STRIPE_CHECKOUT_SUCCESS_URL", "")
    stripe_checkout_cancel_url: str = os.getenv("STRIPE_CHECKOUT_CANCEL_URL", "")
    stripe_portal_return_url: str = os.getenv("STRIPE_PORTAL_RETURN_URL", "")  # folosit mai târziu la portal

    stripe_trial_days: int = _get_int("STRIPE_TRIAL_DAYS", 7)

    # Policy/GDPR
    policy_version: str = os.getenv("POLICY_VERSION", "1.0")

    # Debug
    debug: bool = _get_bool("DEBUG", "false")

    # JWT / tokens
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "smssend-by-swg")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "smssend-web")

    access_token_expire_minutes: int = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    refresh_token_expire_days: int = _get_int("REFRESH_TOKEN_EXPIRE_DAYS", 30)

    # Secrete (pepper) – OBLIGATORII în prod
    password_pepper: str = os.getenv("PASSWORD_PEPPER", "")
    token_pepper: str = os.getenv("TOKEN_PEPPER", "")

    # Cookies (refresh token)
    cookie_secure: bool = _get_bool("COOKIE_SECURE", "true")
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "strict")
    cookie_domain: str = os.getenv("COOKIE_DOMAIN", "")  # optional
    cookie_refresh_name: str = os.getenv("COOKIE_REFRESH_NAME", "refresh_token")

    # Email verification
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    email_verify_token_expire_minutes: int = _get_int("EMAIL_VERIFY_TOKEN_EXPIRE_MINUTES", 60 * 24)

    # SMTP (în prod trebuie setat)
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = _get_int("SMTP_PORT", 587)
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_tls: bool = _get_bool("SMTP_TLS", "true")

    # =========================
    # Reset password (enterprise)
    # =========================
    password_reset_expire_minutes: int = _get_int("PASSWORD_RESET_EXPIRE_MINUTES", 15)

    # Rate limit reset password (DB-backed)
    forgot_password_max_attempts_ip: int = _get_int("FORGOT_PASSWORD_MAX_ATTEMPTS_IP", 10)
    forgot_password_window_seconds_ip: int = _get_int("FORGOT_PASSWORD_WINDOW_SECONDS_IP", 3600)
    forgot_password_block_seconds_ip: int = _get_int("FORGOT_PASSWORD_BLOCK_SECONDS_IP", 3600)

    reset_password_max_attempts_ip: int = _get_int("RESET_PASSWORD_MAX_ATTEMPTS_IP", 30)
    reset_password_window_seconds_ip: int = _get_int("RESET_PASSWORD_WINDOW_SECONDS_IP", 3600)
    reset_password_block_seconds_ip: int = _get_int("RESET_PASSWORD_BLOCK_SECONDS_IP", 3600)

    reset_password_max_attempts_email: int = _get_int("RESET_PASSWORD_MAX_ATTEMPTS_EMAIL", 10)
    reset_password_window_seconds_email: int = _get_int("RESET_PASSWORD_WINDOW_SECONDS_EMAIL", 3600)
    reset_password_block_seconds_email: int = _get_int("RESET_PASSWORD_BLOCK_SECONDS_EMAIL", 3600)

    # Rate limit (DB-backed)
    # - login: IP + email
    login_max_attempts_ip: int = _get_int("LOGIN_MAX_ATTEMPTS_IP", 30)
    login_window_seconds_ip: int = _get_int("LOGIN_WINDOW_SECONDS_IP", 300)
    login_block_seconds_ip: int = _get_int("LOGIN_BLOCK_SECONDS_IP", 900)

    login_max_attempts_email: int = _get_int("LOGIN_MAX_ATTEMPTS_EMAIL", 10)
    login_window_seconds_email: int = _get_int("LOGIN_WINDOW_SECONDS_EMAIL", 300)
    login_block_seconds_email: int = _get_int("LOGIN_BLOCK_SECONDS_EMAIL", 900)

    # - register: IP
    register_max_attempts_ip: int = _get_int("REGISTER_MAX_ATTEMPTS_IP", 10)
    register_window_seconds_ip: int = _get_int("REGISTER_WINDOW_SECONDS_IP", 3600)
    register_block_seconds_ip: int = _get_int("REGISTER_BLOCK_SECONDS_IP", 3600)

    # Lockout cont (per user)
    lockout_fail_threshold: int = _get_int("LOCKOUT_FAIL_THRESHOLD", 10)
    lockout_seconds: int = _get_int("LOCKOUT_SECONDS", 900)


settings = Settings()
