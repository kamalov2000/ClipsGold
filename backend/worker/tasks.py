"""
Celery render task.

Replaces asyncio.Queue + _render_worker from main.py.

Idempotency guarantee:
  - Output S3 key is deterministic from (file_id, clip_index, content_hash, style flags)
  - If the key already exists in S3, the task returns immediately (no double-render)
  - acks_late=True means the task is re-queued if the worker dies mid-render

Progress reporting:
  - Task updates RenderJob.progress in DB every ~5% increment
  - WebSocket endpoint /ws/render-progress/{task_id} polls DB for progress
    (replaces the direct asyncio send — works across multiple API instances)

Queue routing:
  - Paid users (pro/team): enqueue to 'high' queue
  - Free users: enqueue to 'default' queue
  - Call: render_clip_task.apply_async(args=[job], queue='high')
"""

import hashlib
import os
import time
import traceback
from pathlib import Path
from typing import Optional

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

from worker.celery_app import celery_app, REDIS_URL
from db.session import SessionLocal
from db.models import RenderJob, RenderStatus, UsageEventType
from services.usage import log_usage
from services import storage as s3

logger = get_task_logger(__name__)

BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
CLIPS_DIR = BASE_DIR / "clips"

# TTL for the Redis idempotency lock: 2 hours (covers max render time + margin)
_JOB_LOCK_TTL_S = 7200


def _make_job_hash(job: dict) -> str:
    """
    Compute a deterministic hash from the job's identity fields.
    Two jobs with the same (file_id, clip_index, platform, subtitle_style,
    show_hook, enable_jump_cut, enable_sfx) produce the same hash.
    Used as a Redis key for the idempotency lock.
    """
    identity = "|".join(str(job.get(k, "")) for k in (
        "file_id", "clip_index", "platform",
        "subtitle_style", "show_hook", "enable_jump_cut", "enable_sfx",
    ))
    return "render_lock:" + hashlib.sha256(identity.encode()).hexdigest()[:32]


def _acquire_job_lock(redis_client, lock_key: str, task_id: str) -> bool:
    """
    Attempt to acquire an idempotency lock in Redis using SETNX.
    Returns True if the lock was acquired (this worker should proceed).
    Returns False if another worker already holds the lock (duplicate — skip).
    """
    acquired = redis_client.set(lock_key, task_id, nx=True, ex=_JOB_LOCK_TTL_S)
    return bool(acquired)


def _release_job_lock(redis_client, lock_key: str, task_id: str) -> None:
    """
    Release the lock only if this task still owns it.
    Uses a Lua script for atomic check-and-delete.
    """
    lua = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """
    redis_client.eval(lua, 1, lock_key, task_id)


def _get_redis_client():
    """Return a redis.Redis client using the same URL as Celery broker."""
    import redis
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


# ── Helper: update job status in DB ──────────────────────────

def _update_job(db, task_id: str, **kwargs) -> Optional[RenderJob]:
    job = db.query(RenderJob).filter_by(task_id=task_id).first()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.commit()
    return job


# ── Main Celery task ──────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="worker.tasks.render_clip_task",
    acks_late=True,
    max_retries=3,
    default_retry_delay=30,
)
def render_clip_task(self: Task, job: dict) -> dict:
    """
    Render a single clip end-to-end:
      1. Download source video from S3 (or use local path in dev)
      2. Run two-pass FFmpeg render (existing pipeline)
      3. Upload output clip to S3
      4. Update RenderJob in DB
      5. Log usage event
      6. Return result dict

    job dict keys:
      task_id, file_id, clip_index, platform, owner_id,
      subtitle_style, show_hook, enable_jump_cut, enable_sfx,
      manual_crop_x (optional)
    """
    task_id = job["task_id"]
    file_id = job["file_id"]
    owner_id = job["owner_id"]
    clip_index = job["clip_index"]

    # ── R5: Check-before-work idempotency lock ──────────────────────────
    # With acks_late=True, if a worker dies mid-render the task is re-queued.
    # Without a lock, two workers could render the same clip simultaneously.
    # SETNX (set-if-not-exists) ensures only one worker proceeds per job_hash.
    lock_key = _make_job_hash(job)
    redis_client = _get_redis_client()
    lock_acquired = _acquire_job_lock(redis_client, lock_key, task_id)
    if not lock_acquired:
        existing_owner = redis_client.get(lock_key)
        logger.info(
            "render_duplicate_skipped",
            extra={"task_id": task_id, "lock_key": lock_key, "owner": existing_owner},
        )
        return {"task_id": task_id, "skipped": True, "reason": "duplicate_lock"}

    db = SessionLocal()
    start_time = time.time()

    try:
        logger.info(
            "render_start",
            extra={"task_id": task_id, "file_id": file_id, "owner_id": owner_id},
        )
        _update_job(db, task_id, status=RenderStatus.processing, progress=5)

        # ── 1. Resolve input file ─────────────────────────────
        local_input = UPLOAD_DIR / f"{file_id}.mp4"

        if not local_input.exists() and s3.is_s3_enabled():
            logger.info("Downloading source from S3", extra={"task_id": task_id})
            _update_job(db, task_id, progress=10)
            s3_key = s3.upload_key(owner_id, file_id)
            s3.download_file(s3_key, local_input)

        if not local_input.exists():
            raise FileNotFoundError(f"Source video not found: {local_input}")

        # ── 2. Load candidates + transcription from disk/DB ──
        import json

        candidates_file = OUTPUT_DIR / f"{file_id}_viral_analysis.json"
        transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"

        if not candidates_file.exists():
            raise FileNotFoundError("Clip candidates not found. Run /analyze first.")

        with candidates_file.open("r", encoding="utf-8") as f:
            candidates = json.load(f)

        transcription_data = None
        if transcription_file.exists():
            with transcription_file.open("r", encoding="utf-8") as f:
                transcription_data = json.load(f)

        _update_job(db, task_id, progress=15)

        # ── 3. Check idempotency: skip if output already in S3 ─
        import hashlib
        content_parts = []
        if transcription_data:
            clip = candidates[clip_index] if clip_index < len(candidates) else {}
            for seg in transcription_data.get("segments", []):
                seg_start = seg.get("start", 0)
                seg_end = seg.get("end", 0)
                if seg_end >= clip.get("start_time", 0) and seg_start <= clip.get("end_time", 999999):
                    content_parts.append(seg.get("text", ""))
        content_hash = hashlib.md5("|".join(content_parts).encode()).hexdigest()[:6]

        hook_flag = "h1" if job.get("show_hook", True) else "h0"
        style_flag = job.get("subtitle_style", "hormozi")[:2]
        clip_filename = f"{file_id}_clip_{clip_index + 1}_{hook_flag}_{style_flag}_s{content_hash}_VIRAL_GOLD.mp4"
        clip_path = CLIPS_DIR / clip_filename

        output_s3_key = s3.clip_key(owner_id, clip_filename)

        if s3.is_s3_enabled() and s3.object_exists(output_s3_key):
            logger.info("Idempotency hit: clip already rendered", extra={"task_id": task_id})
            _update_job(
                db, task_id,
                status=RenderStatus.complete,
                progress=100,
                output_s3_key=output_s3_key,
                output_filename=clip_filename,
            )
            return {"task_id": task_id, "clip_filename": clip_filename, "skipped": True}

        # ── 4. Run render pipeline ────────────────────────────
        _update_job(db, task_id, progress=20)

        # Import here to avoid circular imports at module load
        import asyncio
        from render_single_clip import render_single_clip_with_progress

        # Build a minimal in-memory store for the existing pipeline
        candidates_store = {file_id: candidates}
        transcription_store_local = {file_id: transcription_data} if transcription_data else {}

        # Progress callback: update DB every time render reports progress
        async def _progress_callback(pct: int):
            _update_job(db, task_id, progress=min(20 + int(pct * 0.75), 95))

        # Run the async render function in a new event loop (Celery worker is sync)
        loop = asyncio.new_event_loop()
        try:
            # Patch cut_video_segment_enhanced to report progress to DB
            from main import cut_video_segment_enhanced
            result = loop.run_until_complete(
                render_single_clip_with_progress(
                    file_id=file_id,
                    clip_index=clip_index,
                    platform=job.get("platform", "tiktok"),
                    task_id=task_id,
                    clip_candidates_store=candidates_store,
                    UPLOAD_DIR=UPLOAD_DIR,
                    CLIPS_DIR=CLIPS_DIR,
                    OUTPUT_DIR=OUTPUT_DIR,
                    transcription_store=transcription_store_local,
                    cut_video_segment_enhanced_func=cut_video_segment_enhanced,
                    manual_crop_x=job.get("manual_crop_x"),
                    show_hook=job.get("show_hook", True),
                    subtitle_style=job.get("subtitle_style", "hormozi"),
                    enable_jump_cut=job.get("enable_jump_cut", False),
                    enable_sfx=job.get("enable_sfx", True),
                )
            )
        finally:
            loop.close()

        _update_job(db, task_id, progress=95)

        # ── 5. Upload output to S3 ────────────────────────────
        if clip_path.exists() and s3.is_s3_enabled():
            logger.info("Uploading clip to S3", extra={"task_id": task_id})
            s3.upload_file(clip_path, output_s3_key, content_type="video/mp4")
            output_size = clip_path.stat().st_size
        else:
            output_s3_key = None
            output_size = clip_path.stat().st_size if clip_path.exists() else 0

        # ── 6. Log usage event ────────────────────────────────
        render_seconds = time.time() - start_time
        log_usage(
            db=db,
            user_id=owner_id,
            event_type=UsageEventType.render_seconds,
            units=render_seconds,
            job_id=None,
            metadata={"file_id": file_id, "clip_index": clip_index, "platform": job.get("platform")},
        )

        # ── 7. Finalise job in DB ─────────────────────────────
        _update_job(
            db, task_id,
            status=RenderStatus.complete,
            progress=100,
            output_s3_key=output_s3_key,
            output_filename=clip_filename,
            output_size_bytes=output_size,
            render_seconds=render_seconds,
            social_meta=result.get("meta"),
        )

        logger.info(
            "render_complete",
            extra={
                "task_id": task_id,
                "duration_s": round(render_seconds, 1),
                "clip": clip_filename,
            },
        )
        return {
            "task_id": task_id,
            "clip_id": clip_index + 1,
            "filename": clip_filename,
            "output_s3_key": output_s3_key,
            "render_seconds": render_seconds,
            "meta": result.get("meta"),
        }

    except SoftTimeLimitExceeded:
        logger.error("render_timeout", extra={"task_id": task_id})
        _update_job(db, task_id, status=RenderStatus.error, error_message="Render timed out (30 min limit)")
        raise

    except Exception as exc:
        err = str(exc) or repr(exc)
        logger.error("render_error", extra={"task_id": task_id, "error": err})
        traceback.print_exc()
        _update_job(db, task_id, status=RenderStatus.error, error_message=err[:1000])

        # Retry with exponential backoff (up to max_retries=3)
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)
        except self.MaxRetriesExceededError:
            logger.error("render_max_retries_exceeded", extra={"task_id": task_id})
            raise

    finally:
        db.close()
        # Release the idempotency lock so a future re-submission can proceed.
        # We release on ALL exits (success, timeout, max-retries-exceeded).
        # During active retries the lock is intentionally kept so the
        # re-queued attempt is still deduplicated against concurrent workers.
        try:
            _release_job_lock(redis_client, lock_key, task_id)
        except Exception:
            pass
        # Clean up temp local files if S3 is enabled
        if s3.is_s3_enabled():
            for tmp in [local_input if not local_input.exists() else None]:
                if tmp and tmp.exists():
                    try:
                        tmp.unlink()
                    except Exception:
                        pass
