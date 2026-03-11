"""
Observability: structured JSON logging + Sentry + correlation ID middleware.

Setup in main.py:
    from services.observability import configure_logging, configure_sentry, CorrelationIdMiddleware
    configure_logging()
    configure_sentry(app)
    app.add_middleware(CorrelationIdMiddleware)

Every log line automatically includes request_id, user_id, job_id from context vars.
"""

import logging
import os
import uuid
from contextvars import ContextVar
from typing import Optional

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ── Context variables (propagated through async tasks) ────────
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_user_id_var: ContextVar[str] = ContextVar("user_id", default="")
_job_id_var: ContextVar[str] = ContextVar("job_id", default="")


def set_context(request_id: str = "", user_id: str = "", job_id: str = "") -> None:
    if request_id:
        _request_id_var.set(request_id)
    if user_id:
        _user_id_var.set(user_id)
    if job_id:
        _job_id_var.set(job_id)


def _add_context_fields(logger, method, event_dict):
    """structlog processor: inject correlation IDs into every log record."""
    event_dict["request_id"] = _request_id_var.get() or None
    event_dict["user_id"] = _user_id_var.get() or None
    event_dict["job_id"] = _job_id_var.get() or None
    return event_dict


def _drop_sensitive_fields(logger, method, event_dict):
    """
    Scrub fields that must never appear in logs.
    OWASP: do not log auth tokens, passwords, cookie values, or raw transcripts.
    """
    _SENSITIVE = {
        "password", "hashed_password", "token", "access_token", "refresh_token",
        "authorization", "cookie", "x-api-key", "secret", "api_key",
        "transcript_text", "raw_text",  # can be large + PII
    }
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for JSON output.
    Call once at application startup.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_context_fields,
            _drop_sensitive_fields,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def configure_sentry(app=None) -> None:
    """
    Initialise Sentry SDK for FastAPI + Celery.
    Set SENTRY_DSN in .env to enable.
    """
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("APP_VERSION", "0.1.0"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            CeleryIntegration(monitor_beat_tasks=False),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
        ],
        # Never send raw user content to Sentry
        before_send=_scrub_sentry_event,
    )


# Keys whose values must never reach Sentry (case-insensitive match)
_SCRUB_KEYS: frozenset = frozenset({
    "password", "hashed_password",
    "token", "access_token", "refresh_token", "id_token",
    "authorization", "cookie", "x-api-key", "api_key", "secret",
    "presigned_url", "presigned", "download_url", "upload_url",
    "email", "phone", "full_name", "username",
    "transcript_text", "raw_text", "corrected_text",
})

# URL patterns that indicate a presigned S3/R2 URL — scrub entire value
import re as _re
_PRESIGNED_URL_RE = _re.compile(
    r"https?://[^\s]+(?:X-Amz-Signature|x-id=GetObject|X-Goog-Signature)[^\s]*",
    _re.IGNORECASE,
)


def _scrub_dict(d: dict) -> dict:
    """Recursively scrub sensitive keys from a dict."""
    if not isinstance(d, dict):
        return d
    result = {}
    for k, v in d.items():
        if k.lower() in _SCRUB_KEYS:
            result[k] = "[Filtered]"
        elif isinstance(v, str) and _PRESIGNED_URL_RE.search(v):
            result[k] = "[Filtered:PresignedURL]"
        elif isinstance(v, dict):
            result[k] = _scrub_dict(v)
        elif isinstance(v, list):
            result[k] = [_scrub_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


def _scrub_sentry_event(event: dict, hint: dict) -> dict:
    """
    Strip PII, auth tokens, presigned URLs, and sensitive transcript data
    from every Sentry event before it leaves the process.

    Scrubs:
      - request.headers  (Authorization, Cookie, X-Api-Key)
      - request.data / request.body
      - extra / contexts dicts
      - breadcrumb data payloads
    """
    # Scrub request headers and body
    request = event.get("request", {})
    if "headers" in request:
        request["headers"] = _scrub_dict(request["headers"])
    if "data" in request:
        if isinstance(request["data"], dict):
            request["data"] = _scrub_dict(request["data"])
        elif isinstance(request["data"], str) and _PRESIGNED_URL_RE.search(request["data"]):
            request["data"] = "[Filtered:PresignedURL]"

    # Scrub extra / contexts
    for section in ("extra", "contexts"):
        if section in event and isinstance(event[section], dict):
            event[section] = _scrub_dict(event[section])

    # Scrub breadcrumb data payloads
    breadcrumbs = event.get("breadcrumbs", {})
    values = breadcrumbs.get("values", []) if isinstance(breadcrumbs, dict) else []
    for crumb in values:
        if isinstance(crumb.get("data"), dict):
            crumb["data"] = _scrub_dict(crumb["data"])
        # Scrub presigned URLs embedded in breadcrumb message strings
        if isinstance(crumb.get("message"), str):
            crumb["message"] = _PRESIGNED_URL_RE.sub("[Filtered:PresignedURL]", crumb["message"])

    return event


# ── Correlation ID middleware ─────────────────────────────────

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Attach a unique request_id to every request.
    - Reads X-Request-ID header if provided by upstream proxy
    - Otherwise generates a new UUID
    - Adds X-Request-ID to the response for client-side tracing
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        _request_id_var.set(request_id)

        # Inject user_id if auth middleware has already resolved it
        user = getattr(request.state, "current_user", None)
        if user:
            _user_id_var.set(str(user.id))

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ── Convenience logger ────────────────────────────────────────

def get_logger(name: str = __name__):
    return structlog.get_logger(name)
