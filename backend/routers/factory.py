"""
Factory Router - API endpoints for autonomous AI factory.
Provides endpoints for discovery queue, stats, and scheduler control.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from datetime import datetime, timedelta
from db.session import get_db
from db.models import DiscoveryQueue, ProcessedVideo, DiscoveryStatus, ClipCandidate
from services.auto_scout import run_trend_scout, get_pending_discoveries
from services.autonomous_scheduler import get_scheduler_status
from services.telegram_notifier import send_test_notification
from services.observability import get_logger
from pydantic import BaseModel

log = get_logger(__name__)

router = APIRouter(prefix="/factory", tags=["factory"])


class DiscoveryResponse(BaseModel):
    id: str
    youtube_url: str
    youtube_video_id: str
    niche: str | None
    status: str
    view_count: int | None
    duration_seconds: float | None
    discovered_at: str
    processed_at: str | None
    error_message: str | None


class FactoryStatsResponse(BaseModel):
    total_discovered: int
    total_processed: int
    total_clips: int
    pending_count: int
    processing_count: int
    failed_count: int
    niches: Dict[str, int]


@router.get("/discoveries")
async def get_discoveries(
    limit: int = 20,
    status: str | None = None,
    niche: str | None = None,
    db: Session = Depends(get_db)
):
    """Get discovery queue items with optional filters."""
    query = db.query(DiscoveryQueue)
    
    if status:
        query = query.filter(DiscoveryQueue.status == status)
    if niche:
        query = query.filter(DiscoveryQueue.niche == niche)
    
    items = query.order_by(DiscoveryQueue.discovered_at.desc()).limit(limit).all()
    
    discoveries = []
    for item in items:
        discoveries.append({
            "id": item.id,
            "youtube_url": item.youtube_url,
            "youtube_video_id": item.youtube_video_id,
            "niche": item.niche,
            "status": item.status.value,
            "view_count": item.view_count,
            "duration_seconds": item.duration_seconds,
            "discovered_at": item.discovered_at.isoformat(),
            "processed_at": item.processed_at.isoformat() if item.processed_at else None,
            "error_message": item.error_message,
        })
    
    return {"discoveries": discoveries}


@router.get("/stats")
async def get_factory_stats(db: Session = Depends(get_db)):
    """Get overall factory statistics."""
    
    # Total counts
    total_discovered = db.query(DiscoveryQueue).count()
    total_processed = db.query(ProcessedVideo).count()
    
    # Status counts
    pending_count = db.query(DiscoveryQueue).filter(
        DiscoveryQueue.status == DiscoveryStatus.pending
    ).count()
    
    processing_count = db.query(DiscoveryQueue).filter(
        DiscoveryQueue.status.in_([
            DiscoveryStatus.downloading,
            DiscoveryStatus.transcribing,
            DiscoveryStatus.analyzing,
            DiscoveryStatus.rendering
        ])
    ).count()
    
    failed_count = db.query(DiscoveryQueue).filter(
        DiscoveryQueue.status == DiscoveryStatus.failed
    ).count()
    
    # Total clips generated
    total_clips = db.query(func.sum(ProcessedVideo.clips_generated)).scalar() or 0
    
    # Niche breakdown
    niche_stats = db.query(
        ProcessedVideo.niche,
        func.sum(ProcessedVideo.clips_generated)
    ).group_by(ProcessedVideo.niche).all()
    
    niches = {niche or "unknown": int(count) for niche, count in niche_stats}
    
    return {
        "total_discovered": total_discovered,
        "total_processed": total_processed,
        "total_clips": int(total_clips),
        "pending_count": pending_count,
        "processing_count": processing_count,
        "failed_count": failed_count,
        "niches": niches,
    }


@router.get("/scheduler-status")
async def get_scheduler_status_endpoint():
    """Get current scheduler status and job list."""
    return get_scheduler_status()


@router.post("/run-scout")
async def run_scout_manually(db: Session = Depends(get_db)):
    """Manually trigger trend scout to discover new videos."""
    try:
        stats = run_trend_scout(db)
        return {
            "success": True,
            "message": "Trend scout completed",
            "stats": stats
        }
    except Exception as e:
        log.error(f"Manual scout failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-telegram")
async def test_telegram_notification():
    """Send test Telegram notification."""
    success = send_test_notification()
    if success:
        return {"success": True, "message": "Test notification sent"}
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send notification. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
        )


@router.get("/pending")
async def get_pending_queue(limit: int = 10, db: Session = Depends(get_db)):
    """Get pending videos in discovery queue."""
    pending = get_pending_discoveries(db, limit=limit)
    
    items = []
    for item in pending:
        items.append({
            "id": item.id,
            "youtube_url": item.youtube_url,
            "youtube_video_id": item.youtube_video_id,
            "niche": item.niche,
            "view_count": item.view_count,
            "duration_seconds": item.duration_seconds,
            "discovered_at": item.discovered_at.isoformat(),
        })
    
    return {"pending": items, "count": len(items)}


@router.get("/processed")
async def get_processed_videos(
    limit: int = 20,
    niche: str | None = None,
    db: Session = Depends(get_db)
):
    """Get processed videos with optional niche filter."""
    query = db.query(ProcessedVideo)
    
    if niche:
        query = query.filter(ProcessedVideo.niche == niche)
    
    videos = query.order_by(ProcessedVideo.processed_at.desc()).limit(limit).all()
    
    items = []
    for video in videos:
        items.append({
            "id": video.id,
            "youtube_video_id": video.youtube_video_id,
            "youtube_url": video.youtube_url,
            "file_id": video.file_id,
            "niche": video.niche,
            "clips_generated": video.clips_generated,
            "clips_uploaded": video.clips_uploaded,
            "processed_at": video.processed_at.isoformat(),
        })
    
    return {"processed": items, "count": len(items)}


@router.get("/daily-report")
async def get_daily_report(db: Session = Depends(get_db)):
    """Get daily statistics report."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    # Videos discovered today
    videos_discovered = db.query(DiscoveryQueue).filter(
        DiscoveryQueue.discovered_at >= yesterday
    ).count()
    
    # Videos processed today
    videos_processed = db.query(ProcessedVideo).filter(
        ProcessedVideo.processed_at >= yesterday
    ).count()
    
    # Clips generated today
    processed_today = db.query(ProcessedVideo).filter(
        ProcessedVideo.processed_at >= yesterday
    ).all()
    
    clips_generated = sum(p.clips_generated for p in processed_today)
    clips_uploaded = sum(p.clips_uploaded for p in processed_today)
    
    # Niche breakdown
    niches = {}
    for p in processed_today:
        niche = p.niche or "unknown"
        niches[niche] = niches.get(niche, 0) + p.clips_generated
    
    # Top viral score
    top_score = 0.0
    candidates = db.query(ClipCandidate).join(ProcessedVideo).filter(
        ProcessedVideo.processed_at >= yesterday
    ).all()
    
    if candidates:
        top_score = max(c.virality_score or 0 for c in candidates)
    
    return {
        "period": "last_24_hours",
        "videos_discovered": videos_discovered,
        "videos_processed": videos_processed,
        "clips_generated": clips_generated,
        "clips_uploaded": clips_uploaded,
        "top_viral_score": top_score,
        "niches": niches,
    }
