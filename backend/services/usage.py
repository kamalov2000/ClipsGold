"""
Usage tracking: log every expensive action to usage_events table.
This feeds both quota enforcement and Stripe billing.

Cost constants are approximate — update when pricing changes.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db.models import UsageEvent, UsageEventType, User

# ── Approximate unit costs (USD) ─────────────────────────────
COST_PER_WHISPER_MINUTE = float(os.getenv("COST_WHISPER_PER_MIN", "0.006"))   # $0.006/min
COST_PER_GPT4O_1K_TOKENS = float(os.getenv("COST_GPT4O_PER_1K", "0.005"))    # $0.005/1k tokens
COST_PER_RENDER_SECOND = float(os.getenv("COST_RENDER_PER_SEC", "0.0001"))    # $0.0001/sec
COST_PER_STORAGE_GB = float(os.getenv("COST_STORAGE_PER_GB", "0.023"))        # S3 standard


def log_usage(
    db: Session,
    user_id: str,
    event_type: UsageEventType,
    units: float,
    job_id: Optional[str] = None,
    event_meta: Optional[dict] = None,
) -> UsageEvent:
    """
    Record a usage event and update the user's rolling counters.
    Always call inside a request/task that already has a DB session.
    """
    cost = _compute_cost(event_type, units)

    event = UsageEvent(
        user_id=user_id,
        job_id=job_id,
        event_type=event_type,
        units=units,
        cost_usd=cost,
        event_meta=event_meta or {},
    )
    db.add(event)

    # Update rolling counters on User for fast quota checks
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        if event_type == UsageEventType.whisper_minutes:
            user.whisper_minutes_this_month = (user.whisper_minutes_this_month or 0) + units
        elif event_type == UsageEventType.render_seconds:
            user.renders_this_month = (user.renders_this_month or 0) + 1
        elif event_type == UsageEventType.storage_mb:
            user.storage_bytes_used = (user.storage_bytes_used or 0) + int(units * 1024 * 1024)

    db.commit()
    return event


def _compute_cost(event_type: UsageEventType, units: float) -> float:
    if event_type == UsageEventType.whisper_minutes:
        return units * COST_PER_WHISPER_MINUTE
    if event_type == UsageEventType.gpt_tokens:
        return (units / 1000) * COST_PER_GPT4O_1K_TOKENS
    if event_type == UsageEventType.render_seconds:
        return units * COST_PER_RENDER_SECOND
    if event_type == UsageEventType.storage_mb:
        return (units / 1024) * COST_PER_STORAGE_GB
    return 0.0
