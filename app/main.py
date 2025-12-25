# FILE: app/main.py
# Scop:
#   - Entry-point FastAPI (startup, middleware, routers, static, health).
#   - Bootstrap DB DOAR în dev (DB_AUTO_CREATE=true). În prod se trece pe migrații.
#   - În prod: hard-fail dacă lipsesc secrete critice (JWT_SECRET / PEPPER-uri).
#
# Debug / depanare:
#   - Dacă serverul NU pornește:
#       journalctl -u smssend-backend -n 200 --no-pager
#     Caută ImportError / config missing / stacktrace.
#   - Dacă /health merge local dar prin domeniu dă 502:
#       1) curl -i http://127.0.0.1:8000/health
#       2) tail -n 200 /var/log/nginx/<domain>.error.log
#   - Dacă vezi ImportError la `billing`:
#       - trebuie să existe fișierul: app/routes/billing.py
#
# Note:
#   - Nginx servește /static direct din disk în prod, dar păstrăm mount-ul și în FastAPI
#     pentru debugging/compatibilitate (nu strică).
#   - Routerele sunt importate explicit ca module; nu folosi "from .routes import ...".

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from . import models  # asigură înregistrarea modelelor (SQLAlchemy)
from .middleware.security_headers import SecurityHeadersMiddleware

# Routers (module-level)
from .routes import (
    auth,
    orders,
    sms,
    settings as settings_routes,
    product_links as product_links_routes,
    password_reset,
    billing,
)


def _validate_secrets_or_die() -> None:
    """
    Hard fail în producție dacă lipsesc secrete critice.

    De ce:
      - fără JWT_SECRET + peppers corecte, sistemul de auth poate deveni nesigur sau instabil.
    """
    if settings.debug:
        return

    missing: list[str] = []
    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        missing.append("JWT_SECRET (min 32 chars)")
    if not settings.password_pepper or len(settings.password_pepper) < 16:
        missing.append("PASSWORD_PEPPER (min 16 chars)")
    if not settings.token_pepper or len(settings.token_pepper) < 16:
        missing.append("TOKEN_PEPPER (min 16 chars)")

    if missing:
        raise RuntimeError("Config invalidă în PROD: " + ", ".join(missing))


_validate_secrets_or_die()

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Dev bootstrap DB (în prod: migrații)
if settings.db_auto_create:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="eMAG SMS SaaS",
    description="Import comenzi eMAG din Excel, management SMS, multi-tenant, GDPR.",
    version="1.0.0",
)

# Security headers / CSP
app.add_middleware(SecurityHeadersMiddleware, is_debug=settings.debug)

# Routers
app.include_router(auth.router)
app.include_router(password_reset.router)
app.include_router(orders.router)
app.include_router(sms.router)
app.include_router(settings_routes.router)
app.include_router(product_links_routes.router)

# Billing (Stripe) - există ca router (chiar dacă e stub până implementăm complet)
app.include_router(billing.router)

# Static (pentru dev / fallback)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    """
    Healthcheck minimal.
    Folosit de:
      - Nginx proxy test
      - uptime monitor
      - deploy scripts (health check)
    """
    return {"ok": True, "env": "debug" if settings.debug else "prod"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler global:
      - în DEBUG: expune excepția (doar dev/staging)
      - în PROD: răspuns generic (nu leak-uim detalii)
    """
    logger.exception("Unhandled server error at %s %s", request.method, request.url.path)

    if settings.debug:
        return JSONResponse(status_code=500, content={"detail": f"Unhandled error: {exc}"})

    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
