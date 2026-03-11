"""
Content Scout — Step 3 & 4 of the Autonomous Factory.

Responsibilities:
  - Search YouTube/TikTok for new videos using yt-dlp
  - Filter by view count, duration, and age
  - Deduplicate against processed_source_videos (blacklist)
  - Insert new URLs into discovery_queue with status PENDING
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Config loader
# ─────────────────────────────────────────────────────────────

def load_factory_config() -> Dict:
    config_path = Path(__file__).parent.parent / "factory_config.yaml"
    if not config_path.exists():
        return {}
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ─────────────────────────────────────────────────────────────
# yt-dlp search
# ─────────────────────────────────────────────────────────────

def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


async def search_videos(
    query: str,
    max_results: int = 10,
    language: str = "ru",
) -> List[Dict[str, Any]]:
    """
    Use yt-dlp to search YouTube and return video metadata list.
    Each item: {url, video_id, title, duration, view_count, upload_date}
    """
    search_query = f"ytsearch{max_results}:{query}"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--no-playlist",
        search_query,
    ]

    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "")
    if cookies_file and Path(cookies_file).exists():
        cmd += ["--cookies", cookies_file]

    log.info(f"[scout] Searching: {query!r} (max {max_results})")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        log.warning(f"[scout] Search timed out for: {query}")
        return []
    except Exception as e:
        log.error(f"[scout] Search failed: {e}")
        return []

    results = []
    for line in stdout.decode(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        url = data.get("webpage_url") or data.get("url", "")
        video_id = data.get("id") or _extract_video_id(url)
        if not video_id:
            continue

        results.append({
            "url": url or f"https://www.youtube.com/watch?v={video_id}",
            "video_id": video_id,
            "title": data.get("title", ""),
            "duration": data.get("duration") or 0,
            "view_count": data.get("view_count") or 0,
            "upload_date": data.get("upload_date", ""),  # YYYYMMDD string
        })

    log.info(f"[scout] Found {len(results)} raw results for: {query!r}")
    return results


# ─────────────────────────────────────────────────────────────
# Filters
# ─────────────────────────────────────────────────────────────

def _passes_filters(video: Dict, cfg: Dict) -> bool:
    """Return True if video passes all scout filters."""
    scout_cfg = cfg.get("scout", {})

    duration = video.get("duration", 0) or 0
    min_len = scout_cfg.get("min_video_length", 120)
    max_len = scout_cfg.get("max_video_length", 7200)
    if duration < min_len or duration > max_len:
        log.debug(f"[filter] Skipped {video['video_id']}: duration {duration}s out of [{min_len}, {max_len}]")
        return False

    view_count = video.get("view_count", 0) or 0
    min_views = scout_cfg.get("min_view_count", 50000)
    if view_count < min_views:
        log.debug(f"[filter] Skipped {video['video_id']}: {view_count} views < {min_views}")
        return False

    upload_date_str = video.get("upload_date", "")
    max_age_days = scout_cfg.get("max_age_days", 90)
    if upload_date_str and len(upload_date_str) == 8:
        try:
            upload_date = datetime.strptime(upload_date_str, "%Y%m%d")
            cutoff = datetime.utcnow() - timedelta(days=max_age_days)
            if upload_date < cutoff:
                log.debug(f"[filter] Skipped {video['video_id']}: too old ({upload_date_str})")
                return False
        except ValueError:
            pass

    return True


# ─────────────────────────────────────────────────────────────
# Deduplication
# ─────────────────────────────────────────────────────────────

def _is_already_processed(video_id: str) -> bool:
    """Check processed_source_videos and discovery_queue for this video_id."""
    try:
        from db.session import SessionLocal
        from db.models import ProcessedVideo, DiscoveryQueue
        db = SessionLocal()
        try:
            if db.query(ProcessedVideo).filter(ProcessedVideo.youtube_video_id == video_id).first():
                return True
            if db.query(DiscoveryQueue).filter(DiscoveryQueue.youtube_video_id == video_id).first():
                return True
            return False
        finally:
            db.close()
    except Exception as e:
        log.debug(f"[dedup] DB unavailable ({e}), skipping dedup check")
        return False


# ─────────────────────────────────────────────────────────────
# Queue insertion
# ─────────────────────────────────────────────────────────────

def _insert_to_queue(video: Dict, niche: str, query: str) -> bool:
    """Insert video into discovery_queue as PENDING. Returns True on success."""
    try:
        from db.session import SessionLocal
        from db.models import DiscoveryQueue, DiscoveryStatus
        db = SessionLocal()
        try:
            item = DiscoveryQueue(
                youtube_url=video["url"],
                youtube_video_id=video["video_id"],
                niche=niche,
                search_query=query,
                view_count=video.get("view_count"),
                duration_seconds=video.get("duration"),
                status=DiscoveryStatus.pending,
            )
            db.add(item)
            db.commit()
            log.info(f"[queue] Added: {video['video_id']} ({niche}) — {video.get('title', '')[:60]}")
            return True
        except Exception as e:
            db.rollback()
            log.warning(f"[queue] Insert failed for {video['video_id']}: {e}")
            return False
        finally:
            db.close()
    except Exception as e:
        log.debug(f"[queue] DB unavailable ({e})")
        return False


# ─────────────────────────────────────────────────────────────
# Main scout run
# ─────────────────────────────────────────────────────────────

async def run_content_scout() -> Dict[str, int]:
    """
    Full scout cycle:
      1. Load keywords from factory_config.yaml
      2. Search YouTube for each keyword
      3. Filter by duration/views/age
      4. Deduplicate against DB
      5. Insert new videos into discovery_queue

    Returns stats dict: {searched, found, filtered, duplicates, queued}
    """
    cfg = load_factory_config()
    scout_cfg = cfg.get("scout", {})
    keywords: List[Dict] = cfg.get("keywords", [])

    if not keywords:
        log.warning("[scout] No keywords configured in factory_config.yaml")
        return {"searched": 0, "found": 0, "filtered": 0, "duplicates": 0, "queued": 0}

    max_per_kw = scout_cfg.get("max_per_keyword", 5)
    search_limit = scout_cfg.get("search_results_per_query", 10)

    stats = {"searched": 0, "found": 0, "filtered": 0, "duplicates": 0, "queued": 0}

    for kw in keywords:
        query = kw.get("query", "")
        niche = kw.get("niche", "general")
        if not query:
            continue

        stats["searched"] += 1
        videos = await search_videos(query, max_results=search_limit, language=kw.get("language", "en"))
        stats["found"] += len(videos)

        queued_this_kw = 0
        for video in videos:
            if queued_this_kw >= max_per_kw:
                break

            if not _passes_filters(video, cfg):
                stats["filtered"] += 1
                continue

            if _is_already_processed(video["video_id"]):
                log.debug(f"[scout] Duplicate: {video['video_id']}")
                stats["duplicates"] += 1
                continue

            if _insert_to_queue(video, niche, query):
                stats["queued"] += 1
                queued_this_kw += 1

    log.info(
        f"[scout] Done: {stats['searched']} queries, "
        f"{stats['found']} found, {stats['filtered']} filtered, "
        f"{stats['duplicates']} dupes, {stats['queued']} queued"
    )
    return stats


async def add_url_to_queue(url: str, niche: str = "manual") -> bool:
    """
    Manually add a single URL to the discovery queue.
    Used by API endpoints or Telegram bot commands.
    """
    from services.download_manager import _url_to_id
    video_id = _extract_video_id(url) or _url_to_id(url)

    if _is_already_processed(video_id):
        log.info(f"[scout] URL already queued/processed: {video_id}")
        return False

    video = {
        "url": url,
        "video_id": video_id,
        "title": "",
        "duration": 0,
        "view_count": 0,
        "upload_date": "",
    }
    return _insert_to_queue(video, niche=niche, query="manual")
