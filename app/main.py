# FILE: app/main.py

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .config import settings
from . import models  # asigură înregistrarea modelelor
from .middleware.security_headers import SecurityHeadersMiddleware
from .routes import auth, orders, sms, settings as settings_routes, product_links as product_links_routes, password_reset, billing


def _validate_secrets_or_die():
    """
    Hard fail în producție dacă lipsesc secrete critice.
    Debug:
      - dacă moare la startup, verifică .env pe VPS.
    """
    if settings.debug:
        return

    missing = []
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

app.add_middleware(SecurityHeadersMiddleware, is_debug=settings.debug)

app.include_router(auth.router)
app.include_router(password_reset.router)
app.include_router(orders.router)
app.include_router(sms.router)
app.include_router(settings_routes.router)
app.include_router(product_links_routes.router)

# Billing (Stripe) - Pasul 2.1: Checkout
app.include_router(billing.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"ok": True, "env": "debug" if settings.debug else "prod"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error at %s %s", request.method, request.url.path)
    # Nu leak-uim detalii în prod
    if settings.debug:
        return JSONResponse(status_code=500, content={"detail": f"Unhandled error: {exc}"})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
