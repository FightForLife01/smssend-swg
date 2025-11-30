# FILE: app/main.py

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .config import settings
from . import models  # asigură înregistrarea modelelor
from .routes import auth, orders, sms, settings as settings_routes, product_links as product_links_routes

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="eMAG SMS SaaS",
    description="Import comenzi eMAG din Excel, management SMS, multi-tenant, GDPR.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(sms.router)
app.include_router(settings_routes.router)
app.include_router(product_links_routes.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {
        "ok": True,
        "env": "debug" if settings.debug else "prod",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error at %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unhandled error: {exc}"},
    )
