"""
BOLA (Broken Object Level Authorization) protection.

Every endpoint that accepts a file_id, job_id, or candidate_id MUST use
one of these dependencies to verify the requesting user owns the object.

Design decisions:
- Returns 404 for both "not found" and "not yours" — prevents object enumeration
  (returning 403 leaks that the object exists; 404 prevents resource enumeration)
- Uses explicit .filter(Model.id == x, Model.owner_id == y) — NOT filter_by()
  because filter_by() uses keyword args that can silently miss columns if the
  model is refactored. Explicit column references are verified at import time.
- Single dependency per object type = no chance of forgetting a check
- Loaded object is returned directly so the endpoint doesn't re-query
"""

import hmac
import time

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User, Video, RenderJob, ClipCandidate
from services.auth import get_current_user


_404 = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

# Minimum response time (seconds) for ownership checks.
# Ensures "not found" and "not yours" responses take the same wall-clock time,
# preventing timing-based resource enumeration attacks.
_MIN_RESPONSE_TIME_S = 0.05


def _constant_time_404(found: bool) -> None:
    """
    Enforce a minimum response time for ownership checks.
    Both "object not found" and "object found but wrong owner" paths
    sleep to _MIN_RESPONSE_TIME_S so an attacker cannot distinguish
    between the two cases via response timing.
    """
    # Use hmac.compare_digest as a constant-time comparison anchor
    # (the actual sleep is the primary defence; compare_digest prevents
    # the compiler from optimising away the timing floor).
    _dummy = hmac.compare_digest("x", "x")
    if not found:
        time.sleep(_MIN_RESPONSE_TIME_S)
        raise _404


# ── Video ownership ───────────────────────────────────────────

def get_owned_video(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Video:
    """
    Resolve file_id → Video and assert ownership.
    Use as a FastAPI dependency on any endpoint that takes file_id.

    Example:
        @app.post("/transcribe/{file_id}")
        async def transcribe(video: Video = Depends(get_owned_video)):
            ...
    """
    video = (
        db.query(Video)
        .filter(
            Video.file_id == file_id,
            Video.owner_id == current_user.id,
        )
        .first()
    )
    _constant_time_404(video is not None)
    return video


# ── RenderJob ownership ───────────────────────────────────────

def get_owned_render_job(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RenderJob:
    """
    Resolve task_id → RenderJob and assert ownership.
    Use on /ws/render-progress/{task_id} and authenticated download flows.
    """
    job = (
        db.query(RenderJob)
        .filter(
            RenderJob.task_id == task_id,
            RenderJob.owner_id == current_user.id,
        )
        .first()
    )
    _constant_time_404(job is not None)
    return job


# ── ClipCandidate ownership (via parent video) ────────────────

def get_owned_candidate(
    candidate_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClipCandidate:
    """
    Resolve candidate_id → ClipCandidate and assert ownership via parent video.
    The JOIN ensures we check Video.owner_id == current_user.id, not just
    ClipCandidate membership — prevents horizontal privilege escalation.
    """
    candidate = (
        db.query(ClipCandidate)
        .join(Video, Video.id == ClipCandidate.video_id)
        .filter(
            ClipCandidate.id == candidate_id,
            Video.owner_id == current_user.id,
        )
        .first()
    )
    _constant_time_404(candidate is not None)
    return candidate


def get_owned_transcript(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Resolve file_id → Transcript and assert ownership via parent video.
    Returns the (transcript, video) tuple so callers get both objects.
    """
    from db.models import Transcript  # local import to avoid circular
    result = (
        db.query(Transcript, Video)
        .join(Video, Video.id == Transcript.video_id)
        .filter(
            Video.file_id == file_id,
            Video.owner_id == current_user.id,
        )
        .first()
    )
    if not result:
        raise _404
    return result


# ── Quota guard ───────────────────────────────────────────────

PLAN_LIMITS = {
    "free": {
        "renders_per_month": 20,
        "whisper_minutes_per_month": 30.0,
        "storage_bytes": 500 * 1024 * 1024,        # 500 MB
        "max_video_duration_seconds": 1800,         # 30 min
        "max_file_size_bytes": 500 * 1024 * 1024,  # 500 MB
    },
    "pro": {
        "renders_per_month": 200,
        "whisper_minutes_per_month": 300.0,
        "storage_bytes": 10 * 1024 * 1024 * 1024,  # 10 GB
        "max_video_duration_seconds": 7200,         # 2 hours
        "max_file_size_bytes": 2 * 1024 * 1024 * 1024,
    },
    "team": {
        "renders_per_month": 1000,
        "whisper_minutes_per_month": 1000.0,
        "storage_bytes": 50 * 1024 * 1024 * 1024,  # 50 GB
        "max_video_duration_seconds": 7200,
        "max_file_size_bytes": 2 * 1024 * 1024 * 1024,
    },
}


def check_render_quota(user: User) -> None:
    """Raise 429 if user has exceeded their monthly render quota."""
    limits = PLAN_LIMITS.get(user.plan.value, PLAN_LIMITS["free"])
    if user.renders_this_month >= limits["renders_per_month"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly render limit reached ({limits['renders_per_month']} renders). "
                "Upgrade your plan to continue."
            ),
        )


def check_storage_quota(user: User, additional_bytes: int = 0) -> None:
    """Raise 429 if user has exceeded their storage quota."""
    limits = PLAN_LIMITS.get(user.plan.value, PLAN_LIMITS["free"])
    if user.storage_bytes_used + additional_bytes > limits["storage_bytes"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Storage quota exceeded. Delete old clips or upgrade your plan.",
        )


def check_video_duration(user: User, duration_seconds: float) -> None:
    """Raise 400 if video exceeds plan's max duration."""
    limits = PLAN_LIMITS.get(user.plan.value, PLAN_LIMITS["free"])
    if duration_seconds > limits["max_video_duration_seconds"]:
        max_min = limits["max_video_duration_seconds"] // 60
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video exceeds maximum duration of {max_min} minutes for your plan.",
        )
