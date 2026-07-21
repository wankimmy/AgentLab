"""HTTP middleware for metrics and demo read-only enforcement."""

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.session import decode_session_token
from app.models.entities import UserRole
from app.observability.metrics import record_http_request

DEMO_WRITE_ALLOWLIST = {
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
}


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        if request.url.path != "/metrics":
            record_http_request(
                request.method,
                request.url.path,
                response.status_code,
                duration,
            )
        return response


class DemoReadOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        key = (request.method, request.url.path.rstrip("/") or "/")
        if key in DEMO_WRITE_ALLOWLIST or request.url.path.startswith("/api/v1/auth/login"):
            return await call_next(request)
        token = request.cookies.get(settings.session_cookie_name)
        if not token:
            return await call_next(request)
        data = decode_session_token(token)
        if not data:
            return await call_next(request)
        role = data.get("role")
        if role == UserRole.demo.value:
            return JSONResponse(
                status_code=403,
                content={"detail": "Demo account is read-only"},
            )
        return await call_next(request)
