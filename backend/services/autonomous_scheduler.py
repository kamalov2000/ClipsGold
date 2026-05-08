"""
Autonomous Scheduler - Orchestrates the AI Factory pipeline.
Uses APScheduler to run: Scout -> Download -> Analyze -> Render -> Notify
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import DiscoveryQueue, DiscoveryStatus, ProcessedVideo, ClipCandidate
import yaml

log = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def load_factory_config() -> Dict:
    """Load factory_config.yaml (primary) with niche_config.yaml fallback."""
    for name in ("factory_config.yaml", "niche_config.yaml"):
        config_path = Path(__file__).parent.parent / name
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


# Keep old name as alias for backwards compat
load_niche_config = load_factory_config


def _mark_status(db: Session, item_id: str, status: DiscoveryStatus, **kwargs) -> None:
    """Update discovery_queue status safely."""
    try:
        row = db.query(DiscoveryQueue).filter(DiscoveryQueue.id == item_id).first()
        if not row:
            return
        row.status = status
        for k, v in kwargs.items():
            if hasattr(row, k):
                setattr(row, k, v)
        if status in (DiscoveryStatus.complete, DiscoveryStatus.failed, DiscoveryStatus.skipped):
            row.processed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        log.warning(f"[scheduler] Status update failed: {e}")
        db.rollback()


def _mark_processed(db: Session, video_id: str, url: str, file_id: str, niche: str, clips: int) -> None:
    """Insert/update processed_videos dedup table."""
    try:
        existing = db.query(ProcessedVideo).filter(ProcessedVideo.youtube_video_id == video_id).first()
        if existing:
            existing.clips_generated += clips
        else:
            db.add(ProcessedVideo(
                youtube_video_id=video_id,
                youtube_url=url,
                file_id=file_id,
                niche=niche,
                clips_generated=clips,
            ))
        db.commit()
    except Exception as e:
        log.warning(f"[scheduler] processed_videos update failed: {e}")
        db.rollback()


async def process_discovery_item(
    db: Session,
    discovery: DiscoveryQueue,
    download_func,
    transcribe_func,
    analyze_func,
    render_func,
) -> bool:
    """
    Full pipeline for one discovery item:
      Download (audio-first) → Transcribe → Analyze → Auto-approve → Render → Cleanup → Notify
    """
    from services.telegram_bot import notify_clip_ready, notify_error

    cfg = load_factory_config()
    proc_cfg = cfg.get("processing", {})
    notif_cfg = cfg.get("notifications", {})

    auto_threshold: float = proc_cfg.get("auto_approve_threshold", 8.5)
    max_clips: int = proc_cfg.get("max_clips_per_video", 5)
    auto_cleanup: bool = proc_cfg.get("auto_cleanup_source", True)
    notify_threshold: float = notif_cfg.get("notify_threshold", 8.0)
    telegram_enabled: bool = notif_cfg.get("telegram_enabled", True)

    url = discovery.youtube_url
    vid_id = discovery.youtube_video_id
    niche = discovery.niche or "unknown"
    source_video_path: Optional[Path] = None

    try:
        log.info(f"[pipeline] Start: {url}")

        # ── Step 1: Download (Audio-First) ──────────────────────
        _mark_status(db, discovery.id, DiscoveryStatus.downloading)

        transcript_result = {}
        transcript_error: Optional[str] = None
        audio_path: Optional[Path] = None

        async def _on_audio_ready(ap: Path):
            nonlocal audio_path, transcript_result, transcript_error
            audio_path = ap
            size = ap.stat().st_size if ap.exists() else 0
            if not ap.exists() or size < 10_000:
                transcript_error = f"Audio file invalid ({size} bytes): {ap.name}"
                log.error(f"[pipeline] {transcript_error}")
                return
            log.info(f"[pipeline] Audio ready ({size/1024/1024:.1f} MB), transcribing...")
            _mark_status(db, discovery.id, DiscoveryStatus.transcribing)
            try:
                transcript_result = await transcribe_func(str(ap))
            except Exception as e:
                transcript_error = str(e)
                log.error(f"[pipeline] Transcription failed: {e}")

        from services.download_manager import UniversalDownloader
        downloader = UniversalDownloader()
        dl_result = await downloader.download_audio_first(url, on_audio_ready=_on_audio_ready)
        source_video_path = dl_result.get("video")

        _mark_status(db, discovery.id, DiscoveryStatus.downloaded)

        if not transcript_result:
            err_detail = transcript_error or "empty result (no speech detected)"
            _mark_status(db, discovery.id, DiscoveryStatus.failed, error_message=f"Transcription failed: {err_detail}")
            log.warning(f"[pipeline] Transcription failed for {url}: {err_detail}")
            return False

        log.info(f"[pipeline] Transcribed: {len(transcript_result.get('text', ''))} chars")

        # ── Step 2: Analyze ─────────────────────────────────────
        _mark_status(db, discovery.id, DiscoveryStatus.analyzing)
        file_id = vid_id  # use video_id as file_id reference
        candidates = await analyze_func(file_id, transcript=transcript_result)

        if not candidates:
            log.warning(f"[pipeline] No viral clips found for {url}")
            _mark_status(db, discovery.id, DiscoveryStatus.skipped,
                         error_message="No viral clips found")
            _mark_processed(db, vid_id, url, file_id, niche, 0)
            _cleanup_source(source_video_path, audio_path)
            return False

        log.info(f"[pipeline] Found {len(candidates)} candidates")

        # ── Step 3: Auto-Approval Engine ────────────────────────
        approved = [
            c for c in candidates
            if (c.get("virality_score") or c.get("viral_score") or 0) >= auto_threshold
        ][:max_clips]

        if not approved:
            log.info(f"[pipeline] No clips >= {auto_threshold} threshold, skipping render")
            _mark_status(db, discovery.id, DiscoveryStatus.skipped,
                         error_message=f"No clips >= {auto_threshold} score")
            _mark_processed(db, vid_id, url, file_id, niche, 0)
            _cleanup_source(source_video_path, audio_path)
            return False

        log.info(f"[pipeline] Auto-approved {len(approved)}/{len(candidates)} clips (threshold {auto_threshold})")

        # ── Step 4: Render ──────────────────────────────────────
        _mark_status(db, discovery.id, DiscoveryStatus.rendering)
        rendered_count = 0
        source_title = getattr(discovery, "title", url)

        for clip in approved:
            try:
                result = await render_func(
                    file_id,
                    clip,
                    source_video_path=source_video_path,
                )
                if result:
                    rendered_count += 1
                    clip_path = Path(result) if isinstance(result, str) else None
                    score = clip.get("virality_score") or clip.get("viral_score") or 0
                    log.info(f"[pipeline] Rendered #{rendered_count}: {clip.get('title', '')[:50]} (score {score})")

                    # ── Telegram notification ───────────────────
                    if telegram_enabled and score >= notify_threshold:
                        notify_clip_ready(
                            source_title=str(source_title)[:80],
                            clip_title=clip.get("title", "Untitled")[:80],
                            hook=clip.get("hook", ""),
                            viral_score=score,
                            clip_path=clip_path,
                            source_url=url,
                        )
            except Exception as e:
                log.error(f"[pipeline] Render failed for clip: {e}")

        # ── Step 5: Complete ────────────────────────────────────
        _mark_status(db, discovery.id, DiscoveryStatus.complete)
        _mark_processed(db, vid_id, url, file_id, niche, rendered_count)
        log.info(f"[pipeline] Complete: {rendered_count} clips from {url}")

        # ── Step 6: Auto-cleanup source file ────────────────────
        if auto_cleanup and rendered_count > 0:
            _cleanup_source(source_video_path, audio_path)

        return True

    except Exception as e:
        log.error(f"[pipeline] Error for {url}: {e}")
        try:
            _mark_status(db, discovery.id, DiscoveryStatus.failed, error_message=str(e)[:500])
        except Exception:
            pass
        from services.telegram_bot import notify_error
        notify_error("pipeline", str(e)[:300], url)
        return False


def _cleanup_source(video_path: Optional[Path], audio_path: Optional[Path]) -> None:
    """Delete source video and audio files to free disk space."""
    for p in (video_path, audio_path):
        if p and Path(p).exists():
            try:
                Path(p).unlink()
                log.info(f"[cleanup] Deleted: {p}")
            except Exception as e:
                log.warning(f"[cleanup] Could not delete {p}: {e}")


async def run_factory_cycle(
    download_func=None,
    transcribe_func=None,
    analyze_func=None,
    render_func=None,
    max_videos: int = None,
):
    """Process pending discovery_queue items through the full pipeline."""
    from services.telegram_bot import notify_factory_cycle

    cfg = load_factory_config()
    if max_videos is None:
        max_videos = cfg.get("processing", {}).get("max_videos_per_cycle", 5)

    log.info(f"[factory] Starting cycle (max {max_videos} videos)...")
    db = next(get_db())

    try:
        pending = (
            db.query(DiscoveryQueue)
            .filter(DiscoveryQueue.status == DiscoveryStatus.pending)
            .limit(max_videos)
            .all()
        )

        if not pending:
            log.info("[factory] No pending videos in queue")
            return

        log.info(f"[factory] Processing {len(pending)} items...")
        success_count = 0
        failed_count = 0
        total_clips = 0

        for discovery in pending:
            success = await process_discovery_item(
                db, discovery,
                download_func or _noop_async,
                transcribe_func or _noop_async,
                analyze_func or _noop_async,
                render_func or _noop_async,
            )
            if success:
                success_count += 1
            else:
                failed_count += 1

        log.info(f"[factory] Cycle done: {success_count} ok, {failed_count} failed")
        if success_count > 0:
            notify_factory_cycle(success_count, failed_count, total_clips)
    finally:
        db.close()


async def _noop_async(*args, **kwargs):
    """Placeholder for unset pipeline functions."""
    return None


async def run_content_scout_job():
    """Scheduled job: search for new videos and add to discovery_queue."""
    from services.scout import run_content_scout
    from services.telegram_bot import notify_scout_complete

    log.info("[scout] Running scheduled content scout...")
    try:
        stats = await run_content_scout()
        log.info(f"[scout] Done: {stats}")
    except Exception as e:
        log.error(f"[scout] Scout job failed: {e}")


async def run_daily_report_job():
    """Scheduled job: send daily Telegram summary."""
    from services.telegram_bot import notify_daily_report

    log.info("[report] Generating daily report...")
    db = next(get_db())
    try:
        yesterday = datetime.utcnow() - timedelta(days=1)

        videos_discovered = db.query(DiscoveryQueue).filter(
            DiscoveryQueue.discovered_at >= yesterday
        ).count()

        videos_processed = db.query(ProcessedVideo).filter(
            ProcessedVideo.processed_at >= yesterday
        ).count()

        processed = db.query(ProcessedVideo).filter(
            ProcessedVideo.processed_at >= yesterday
        ).all()

        clips_generated = sum(p.clips_generated for p in processed)
        niches: Dict[str, int] = {}
        for p in processed:
            k = p.niche or "unknown"
            niches[k] = niches.get(k, 0) + p.clips_generated

        top_score = 0.0
        recent_candidates = db.query(ClipCandidate).all()
        if recent_candidates:
            top_score = max((c.virality_score or 0) for c in recent_candidates)

        notify_daily_report(
            discovered=videos_discovered,
            processed=videos_processed,
            clips=clips_generated,
            top_score=top_score,
            niches=niches,
        )
        log.info("[report] Daily report sent")
    finally:
        db.close()


def start_autonomous_scheduler(
    download_func=None,
    transcribe_func=None,
    analyze_func=None,
    render_func=None,
    enable_scout: bool = True,
    enable_factory_cycle: bool = True,
    enable_daily_report: bool = True,
    # Legacy param names kept for backwards compat
    enable_trend_scout: bool = True,
):
    """
    Start the autonomous factory scheduler.

    Jobs:
      - Content Scout   : every 6 hours (configurable in factory_config.yaml)
      - Factory Cycle   : 3x daily at 9:00, 15:00, 21:00
      - Daily Report    : 23:00 via Telegram
    """
    global scheduler

    cfg = load_factory_config()
    scout_hours: int = cfg.get("scout", {}).get("schedule_hours", 6)

    if scheduler and scheduler.running:
        log.warning("[scheduler] Already running")
        return

    scheduler = AsyncIOScheduler(timezone="UTC")

    # Job 1: Content Scout — every N hours
    if enable_scout and enable_trend_scout:
        scheduler.add_job(
            run_content_scout_job,
            IntervalTrigger(hours=scout_hours),
            id="content_scout",
            name=f"Content Scout (every {scout_hours}h)",
            replace_existing=True,
            next_run_time=datetime.utcnow(),  # Run immediately on start
        )
        log.info(f"[scheduler] Scout: every {scout_hours}h")

    # Job 2: Factory Cycle — 9:00, 15:00, 21:00 UTC
    if enable_factory_cycle:
        for hour in [9, 15, 21]:
            # Capture hour in closure correctly
            def _make_cycle(h):
                async def _job():
                    await run_factory_cycle(download_func, transcribe_func, analyze_func, render_func)
                return _job
            scheduler.add_job(
                _make_cycle(hour),
                CronTrigger(hour=hour, minute=0),
                id=f"factory_cycle_{hour}",
                name=f"Factory Cycle {hour}:00 UTC",
                replace_existing=True,
            )
        log.info("[scheduler] Factory cycle: 09:00, 15:00, 21:00 UTC")

    # Job 3: Daily Report — 23:00 UTC
    if enable_daily_report:
        scheduler.add_job(
            run_daily_report_job,
            CronTrigger(hour=23, minute=0),
            id="daily_report",
            name="Daily Report 23:00 UTC",
            replace_existing=True,
        )
        log.info("[scheduler] Daily report: 23:00 UTC")

    scheduler.start()
    log.info("[scheduler] Autonomous Factory started")


def stop_autonomous_scheduler():
    """Stop the autonomous scheduler."""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        log.info("🛑 Autonomous Scheduler stopped")
    else:
        log.warning("Scheduler not running")


def get_scheduler_status() -> Dict:
    """Get current scheduler status and job list."""
    global scheduler
    
    if not scheduler:
        return {"running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs
    }
