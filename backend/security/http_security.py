import os
import secrets
from typing import Iterable

from fastapi import HTTPException, Request, status


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def attach_security_headers(response) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'"
    )


def issue_csrf_cookie(response, token: str | None = None) -> str:
    token = token or secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        secure=os.getenv("ENVIRONMENT", "development") == "production",
        samesite="strict",
        max_age=60 * 60 * 8,
    )
    return token


def validate_csrf(request: Request, exempt_paths: Iterable[str]) -> None:
    if request.method.upper() not in UNSAFE_METHODS:
        return

    path = request.url.path
    if any(path.startswith(prefix) for prefix in exempt_paths):
        return

    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")

    # Enforce CSRF for cookie-session flows only.
    if not cookie_token:
        return

    if not header_token or cookie_token != header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
