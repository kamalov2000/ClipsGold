"""
Rate limiting via slowapi + hard quota checks.

Usage in main.py:
    from services.limiter import limiter, rate_limit_handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    @app.post("/upload")
    @limiter.limit("10/hour")
    async def upload(request: Request, ...):
        ...

Notes:
- slowapi is alpha-quality; for edge-level limiting add nginx/Cloudflare rules too.
- Behind a reverse proxy, set TRUST_PROXY=1 in .env so real IP is read from
  X-Forwarded-For (only trust if proxy is under your control).
"""

import os
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _get_key(request: Request) -> str:
    """
    Use authenticated user_id if available, else fall back to IP.
    This prevents a single user from bypassing limits by rotating IPs.
    """
    user = getattr(request.state, "current_user", None)
    if user:
        return f"user:{user.id}"
    # Behind trusted proxy: read real IP from X-Forwarded-For
    if os.getenv("TRUST_PROXY", "0") == "1":
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_key,
    default_limits=["200/minute"],          # global safety net
    application_limits=["2000/hour"],       # per-app ceiling
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}. Please slow down.",
            "retry_after": getattr(exc, "retry_after", None),
        },
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )


# ── Per-endpoint limit strings (import and use in decorators) ─
LIMITS = {
    "upload":     "10/hour",
    "transcribe": "5/hour",
    "analyze":    "10/hour",
    "render":     "20/hour",
    "download":   "100/hour",
    "youtube":    "5/hour",
}
