"""
Trend Scout Service - Autonomous video discovery for AI Factory.
Uses yt-dlp and YouTube Data API to find trending videos by niche.
"""

import os
import yaml
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import yt_dlp
from sqlalchemy.orm import Session
from db.models import DiscoveryQueue, ProcessedVideo, DiscoveryStatus
from services.observability import get_logger

log = get_logger(__name__)


def load_niche_config() -> Dict:
    """Load niche configuration from YAML file."""
    config_path = Path(__file__).parent.parent / "niche_config.yaml"
    if not config_path.exists():
        log.warning("niche_config.yaml not found, using defaults")
        return {"niches": [], "settings": {}}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_video_processed(db: Session, video_id: str) -> bool:
    """Check if video has already been processed (deduplication)."""
    existing = db.query(ProcessedVideo).filter(
        ProcessedVideo.youtube_video_id == video_id
    ).first()
    return existing is not None


def is_video_in_queue(db: Session, video_id: str) -> bool:
    """Check if video is already in discovery queue."""
    existing = db.query(DiscoveryQueue).filter(
        DiscoveryQueue.youtube_video_id == video_id
    ).first()
    return existing is not None


def search_youtube_videos(
    search_query: str,
    max_results: int = 5,
    min_duration: int = 300,
    max_duration: int = 3600,
    min_views: int = 10000,
    upload_date: str = "week",
    sort_by: str = "viewCount"
) -> List[Dict]:
    """
    Search YouTube for videos matching criteria using yt-dlp.
    
    Args:
        search_query: Search term
        max_results: Maximum number of results
        min_duration: Minimum video duration in seconds
        max_duration: Maximum video duration in seconds
        min_views: Minimum view count
        upload_date: Upload date filter (today, week, month, year)
        sort_by: Sort order (relevance, date, rating, viewCount)
    
    Returns:
        List of video metadata dicts
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_generic_extractor': False,
    }
    
    # Build search URL with filters
    search_url = f"ytsearch{max_results}:{search_query}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_url, download=False)
            
            if not result or 'entries' not in result:
                log.warning(f"No results for query: {search_query}")
                return []
            
            videos = []
            for entry in result['entries']:
                if not entry:
                    continue
                
                duration = entry.get('duration', 0)
                view_count = entry.get('view_count', 0)
                
                # Apply filters
                if duration < min_duration or duration > max_duration:
                    continue
                if view_count < min_views:
                    continue
                
                video_id = entry.get('id')
                if not video_id:
                    continue
                
                videos.append({
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'title': entry.get('title', 'Unknown'),
                    'duration': duration,
                    'view_count': view_count,
                    'like_count': entry.get('like_count', 0),
                    'channel': entry.get('channel', 'Unknown'),
                    'upload_date': entry.get('upload_date', ''),
                })
            
            log.info(f"Found {len(videos)} videos for query: {search_query}")
            return videos
    
    except Exception as e:
        log.error(f"YouTube search failed for '{search_query}': {e}")
        return []


def discover_videos_for_niche(
    db: Session,
    niche_config: Dict,
    max_videos: int = 3
) -> int:
    """
    Discover and queue videos for a specific niche.
    
    Args:
        db: Database session
        niche_config: Niche configuration dict
        max_videos: Maximum videos to discover
    
    Returns:
        Number of videos added to queue
    """
    niche_name = niche_config.get('name', 'unknown')
    search_queries = niche_config.get('search_queries', [])
    min_duration = niche_config.get('min_duration', 300)
    max_duration = niche_config.get('max_duration', 3600)
    min_views = niche_config.get('min_views', 10000)
    
    log.info(f"🔍 Discovering videos for niche: {niche_name}")
    
    added_count = 0
    
    for query in search_queries:
        if added_count >= max_videos:
            break
        
        videos = search_youtube_videos(
            search_query=query,
            max_results=max_videos - added_count + 2,  # Extra buffer for filtering
            min_duration=min_duration,
            max_duration=max_duration,
            min_views=min_views,
        )
        
        for video in videos:
            if added_count >= max_videos:
                break
            
            video_id = video['video_id']
            
            # Skip if already processed or in queue
            if is_video_processed(db, video_id):
                log.info(f"⏭ Skipping {video_id} - already processed")
                continue
            
            if is_video_in_queue(db, video_id):
                log.info(f"⏭ Skipping {video_id} - already in queue")
                continue
            
            # Add to discovery queue
            discovery_item = DiscoveryQueue(
                youtube_url=video['url'],
                youtube_video_id=video_id,
                niche=niche_name,
                search_query=query,
                view_count=video['view_count'],
                like_count=video['like_count'],
                duration_seconds=video['duration'],
                status=DiscoveryStatus.pending,
            )
            
            db.add(discovery_item)
            added_count += 1
            
            log.info(f"✅ Added to queue: {video['title'][:50]}... ({video_id})")
    
    db.commit()
    log.info(f"🎯 Added {added_count} videos for niche '{niche_name}'")
    return added_count


def run_trend_scout(db: Session) -> Dict[str, int]:
    """
    Main trend scout function - discovers videos for all enabled niches.
    
    Args:
        db: Database session
    
    Returns:
        Dict with stats: {niche_name: videos_added}
    """
    log.info("🚀 Starting Trend Scout...")
    
    config = load_niche_config()
    niches = config.get('niches', [])
    settings = config.get('settings', {})
    
    max_videos_per_niche = settings.get('max_videos_per_niche', 3)
    max_videos_per_day = settings.get('max_videos_per_day', 15)
    
    stats = {}
    total_added = 0
    
    for niche in niches:
        if not niche.get('enabled', True):
            log.info(f"⏭ Skipping disabled niche: {niche.get('name')}")
            continue
        
        if total_added >= max_videos_per_day:
            log.info(f"🛑 Reached daily limit ({max_videos_per_day})")
            break
        
        remaining = min(max_videos_per_niche, max_videos_per_day - total_added)
        added = discover_videos_for_niche(db, niche, max_videos=remaining)
        
        stats[niche['name']] = added
        total_added += added
    
    log.info(f"✅ Trend Scout complete: {total_added} videos added")
    log.info(f"📊 Stats: {stats}")
    
    return stats


def get_pending_discoveries(db: Session, limit: int = 10) -> List[DiscoveryQueue]:
    """Get pending videos from discovery queue."""
    return db.query(DiscoveryQueue).filter(
        DiscoveryQueue.status == DiscoveryStatus.pending
    ).order_by(DiscoveryQueue.discovered_at).limit(limit).all()


def mark_discovery_status(
    db: Session,
    discovery_id: str,
    status: DiscoveryStatus,
    file_id: Optional[str] = None,
    error_message: Optional[str] = None
):
    """Update discovery queue item status."""
    item = db.query(DiscoveryQueue).filter(DiscoveryQueue.id == discovery_id).first()
    if item:
        item.status = status
        if file_id:
            item.file_id = file_id
        if error_message:
            item.error_message = error_message
        if status in [DiscoveryStatus.complete, DiscoveryStatus.failed, DiscoveryStatus.skipped]:
            item.processed_at = datetime.utcnow()
        db.commit()


def mark_video_processed(
    db: Session,
    youtube_video_id: str,
    youtube_url: str,
    file_id: str,
    niche: str,
    clips_generated: int = 0
):
    """Mark video as processed in deduplication database."""
    processed = ProcessedVideo(
        youtube_video_id=youtube_video_id,
        youtube_url=youtube_url,
        file_id=file_id,
        niche=niche,
        clips_generated=clips_generated,
        clips_uploaded=0,
    )
    db.add(processed)
    db.commit()
    log.info(f"✅ Marked {youtube_video_id} as processed")
