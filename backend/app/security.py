"""Optional production origin checks; Vercel remains the authentication boundary."""
import os
from urllib.parse import urlsplit
from fastapi.responses import JSONResponse

HEADERS = {"X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff",
           "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}


def origin(value, referer=False):
    try:
        url = urlsplit(value)
        if (url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password
                or url.fragment or (not referer and (url.path or url.query))):
            return None
        if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            return None
        port = url.port or (443 if url.scheme == "https" else 80)
        return url.scheme, url.hostname.lower(), port
    except ValueError:
        return None


def allowed_origins(required=False):
    value = os.environ.get("SIDEQUEST_ALLOWED_ORIGINS")
    if value is None and not required:
        return None
    values = value.split(",") if value else []
    parsed = {origin(item.strip()) for item in values}
    if not parsed or None in parsed:
        raise RuntimeError("SIDEQUEST_ALLOWED_ORIGINS requires explicit HTTPS origins (HTTP loopback allowed locally)")
    return parsed


def install_origin_guard(application, allowed):
    if allowed is None:
        return

    @application.middleware("http")
    async def guard(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origins = request.headers.getlist("origin")
            referers = request.headers.getlist("referer")
            supplied = origin(origins[0]) if len(origins) == 1 else None
            if not origins and len(referers) == 1:
                supplied = origin(referers[0], referer=True)
            if supplied not in allowed or request.headers.get("sec-fetch-site") == "cross-site":
                response = JSONResponse(status_code=403, content={"detail": "Request origin is not allowed"})
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers.update(HEADERS)
        return response
