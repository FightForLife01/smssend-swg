# FILE: app/middleware/security_headers.py
# Scop:
#   - Headere de securitate + CSP strict (merge pentru UI static fără inline scripts).
#
# IMPORTANT:
#   - CSP strict cere ca UI să nu folosească inline handlers / innerHTML cu script.

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, is_debug: bool):
        super().__init__(app)
        self.is_debug = is_debug

    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)

        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # CSP: strict, fără inline
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
        )

        # HSTS doar dacă rulezi HTTPS în spate (în prod)
        if not self.is_debug and request.url.scheme == "https":
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return resp
