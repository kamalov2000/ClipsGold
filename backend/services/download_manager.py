"""
UniversalDownloader — Smart video acquisition module.

Features:
  1. Auto-detects source (yt-dlp for social media, aria2c/requests for direct URLs)
  2. Smart Compression: auto-downscales 4K → 1080p @ 5Mbps via FFmpeg
  3. Audio-First: extracts .m4a immediately for Whisper; video downloads in background
  4. Proxy & User-Agent Rotation from .env
  5. Autonomous Queue: picks from discovery_queue, updates status to downloaded
"""

import asyncio
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Callable, Awaitable
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", "downloads"))
DOWNLOADS_DIR.mkdir(exist_ok=True)

MAX_VIDEO_HEIGHT = 1080       # Auto-compress anything above this
TARGET_BITRATE_VIDEO = "5M"   # 5 Mbps for compressed video
TARGET_BITRATE_AUDIO = "192k"

# Social media domains that require yt-dlp
_YTDLP_DOMAINS = {
    "youtube.com", "youtu.be",
    "tiktok.com", "vm.tiktok.com",
    "instagram.com", "instagr.am",
    "twitter.com", "x.com",
    "vimeo.com",
    "twitch.tv",
    "facebook.com", "fb.watch",
    "reddit.com",
    "bilibili.com",
}

# User-Agent pool for rotation
_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _load_proxies() -> List[str]:
    """Load proxy list from .env. Format: PROXIES=http://p1:port,http://p2:port"""
    raw = os.getenv("PROXIES", "")
    return [p.strip() for p in raw.split(",") if p.strip()]


def _random_proxy() -> Optional[str]:
    proxies = _load_proxies()
    return random.choice(proxies) if proxies else None


def _is_social_url(url: str) -> bool:
    """Return True if URL belongs to a social media platform (needs yt-dlp)."""
    try:
        host = urlparse(url).hostname or ""
        host = host.lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in _YTDLP_DOMAINS)
    except Exception:
        return False


def _get_video_height(path: Path) -> int:
    """Use ffprobe to get video height. Returns 0 on failure."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=height", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=15
        )
        return int(result.stdout.strip()) if result.stdout.strip() else 0
    except Exception:
        return 0


def _compress_to_1080p(src: Path, dst: Path) -> Path:
    """
    If src height > MAX_VIDEO_HEIGHT, re-encode to 1080p @ TARGET_BITRATE_VIDEO.
    Returns dst if compressed, src if no compression needed.
    """
    height = _get_video_height(src)
    if height <= MAX_VIDEO_HEIGHT:
        log.info(f"[compress] {src.name} is {height}p — no compression needed")
        return src

    log.info(f"[compress] {src.name} is {height}p — compressing to {MAX_VIDEO_HEIGHT}p")
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", f"scale=-2:{MAX_VIDEO_HEIGHT}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-b:v", TARGET_BITRATE_VIDEO,
        "-c:a", "aac", "-b:a", TARGET_BITRATE_AUDIO,
        str(dst)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired:
        log.warning(f"[compress] Timeout after 1800s, using original: {src.name}")
        return src
    if result.returncode != 0:
        log.error(f"[compress] FFmpeg failed: {result.stderr.decode()[:300]}")
        return src  # fallback to original
    src.unlink(missing_ok=True)
    log.info(f"[compress] Done: {dst.stat().st_size / 1024 / 1024:.1f} MB")
    return dst


# ─────────────────────────────────────────────────────────────
# Core downloader
# ─────────────────────────────────────────────────────────────

class UniversalDownloader:
    """
    Accepts any video URL, determines the best download strategy,
    and provides Audio-First processing for Whisper.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or DOWNLOADS_DIR

    # ── Public API ────────────────────────────────────────────

    async def download_audio_first(
        self,
        url: str,
        on_audio_ready: Optional[Callable[[Path], Awaitable[None]]] = None,
        on_video_ready: Optional[Callable[[Path], Awaitable[None]]] = None,
    ) -> dict:
        """
        Audio-First strategy:
          1. Extract audio (.m4a) immediately → call on_audio_ready(audio_path)
          2. Download full video in background → call on_video_ready(video_path)

        Returns: {"audio": Path, "video": Path}
        """
        log.info(f"[download] Audio-first for: {url}")
        audio_path = await self._extract_audio(url)

        if on_audio_ready:
            await on_audio_ready(audio_path)

        video_path = await self._download_video(url)

        if on_video_ready:
            await on_video_ready(video_path)

        return {"audio": audio_path, "video": video_path}

    async def download_video_only(self, url: str) -> Path:
        """Download full video, apply compression if needed."""
        return await self._download_video(url)

    async def download_audio_only(self, url: str) -> Path:
        """Download audio only (.m4a)."""
        return await self._extract_audio(url)

    # ── Internal: audio extraction ────────────────────────────

    async def _extract_audio(self, url: str) -> Path:
        uid = _url_to_id(url)
        audio_path = self.output_dir / f"{uid}_audio.m4a"
        if audio_path.exists():
            log.info(f"[audio] Cache hit: {audio_path}")
            return audio_path

        if _is_social_url(url):
            return await self._ytdlp_audio(url, audio_path)
        else:
            # For direct URLs: download video then extract audio
            video_path = await self._download_video(url)
            return await self._ffmpeg_extract_audio(video_path, audio_path)

    async def _ytdlp_audio(self, url: str, out: Path) -> Path:
        cmd = self._build_ytdlp_cmd(url, audio_only=True, output=out)
        log.info(f"[yt-dlp audio] {url}")
        await _run_async(cmd, timeout=600)
        actual = _find_output_file(out)
        size = actual.stat().st_size if actual.exists() else 0
        if not actual.exists() or size < 10_000:
            raise RuntimeError(f"Audio file missing or too small ({size} bytes): {actual.name}")
        log.info(f"[yt-dlp audio] Saved: {actual} ({size/1024/1024:.1f} MB)")
        return actual

    async def _ffmpeg_extract_audio(self, video: Path, out: Path) -> Path:
        cmd = ["ffmpeg", "-y", "-i", str(video), "-vn",
               "-c:a", "aac", "-b:a", TARGET_BITRATE_AUDIO, str(out)]
        await _run_async(cmd, timeout=300)
        return out

    # ── Internal: video download ──────────────────────────────

    async def _download_video(self, url: str) -> Path:
        uid = _url_to_id(url)
        video_path = self.output_dir / f"{uid}_video.mp4"
        if video_path.exists():
            log.info(f"[video] Cache hit: {video_path}")
            return video_path

        if _is_social_url(url):
            result = await self._ytdlp_video(url, video_path)
        else:
            result = await self._aria2c_or_requests(url, video_path)

        # Smart compression: downscale 4K → 1080p
        compressed_path = self.output_dir / f"{uid}_video_1080p.mp4"
        final = _compress_to_1080p(result, compressed_path)
        return final

    async def _ytdlp_video(self, url: str, out: Path) -> Path:
        cmd = self._build_ytdlp_cmd(url, audio_only=False, output=out)
        log.info(f"[yt-dlp video] {url}")
        await _run_async(cmd, timeout=600)
        actual = _find_output_file(out)
        log.info(f"[yt-dlp video] Saved: {actual} ({actual.stat().st_size / 1024 / 1024:.1f} MB)")
        return actual

    async def _aria2c_or_requests(self, url: str, out: Path) -> Path:
        """Use aria2c if available (multi-connection), else fall back to requests."""
        if shutil.which("aria2c"):
            return await self._aria2c_download(url, out)
        else:
            return await self._requests_download(url, out)

    async def _aria2c_download(self, url: str, out: Path) -> Path:
        proxy = _random_proxy()
        cmd = [
            "aria2c",
            "--split=8", "--max-connection-per-server=8",
            "--min-split-size=5M",
            "--file-allocation=none",
            f"--user-agent={_random_ua()}",
            f"--dir={out.parent}", f"--out={out.name}",
        ]
        if proxy:
            cmd += [f"--all-proxy={proxy}"]
        cmd.append(url)
        log.info(f"[aria2c] Downloading: {url}")
        await _run_async(cmd, timeout=600)
        return out

    async def _requests_download(self, url: str, out: Path) -> Path:
        import httpx
        proxy = _random_proxy()
        headers = {"User-Agent": _random_ua()}
        proxies = {"http://": proxy, "https://": proxy} if proxy else None
        log.info(f"[requests] Downloading: {url}")
        async with httpx.AsyncClient(headers=headers, proxies=proxies, timeout=600, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(out, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
        log.info(f"[requests] Saved: {out} ({out.stat().st_size / 1024 / 1024:.1f} MB)")
        return out

    # ── yt-dlp command builder ─────────────────────────────────

    def _build_ytdlp_cmd(self, url: str, audio_only: bool, output: Path) -> List[str]:
        proxy = _random_proxy()
        ua = _random_ua()
        cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "")
        cookies_raw = os.getenv("YOUTUBE_COOKIES", "")

        cmd = ["yt-dlp"]

        if audio_only:
            cmd += [
                "--format", "bestaudio/best",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
            ]
        else:
            # Prefer 4K → 1440p → 1080p, always with best audio, merged to mp4
            cmd += [
                "-f", (
                    "bestvideo[height>=2160][ext=mp4]+bestaudio[ext=m4a]"
                    "/bestvideo[height>=1440][ext=mp4]+bestaudio[ext=m4a]"
                    "/bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]"
                    "/best[ext=mp4]/best"
                ),
                "--merge-output-format", "mp4",
            ]

        cmd += [
            "--user-agent", ua,
            "--no-playlist",
            "--socket-timeout", "30",
            "--retries", "5",
            "--fragment-retries", "10",
            "--no-warnings",
            "-o", str(output),
        ]

        if not audio_only:
            cmd += ["--max-filesize", "1G", "--match-filter", "duration < 7200"]

        if proxy:
            cmd += ["--proxy", proxy]

        if cookies_file and Path(cookies_file).exists():
            cmd += ["--cookies", cookies_file]
        elif cookies_raw:
            cmd += ["--add-header", f"Cookie:{cookies_raw}"]

        cmd.append(url)
        return cmd


# ─────────────────────────────────────────────────────────────
# Autonomous Queue Worker
# ─────────────────────────────────────────────────────────────

async def run_download_queue_worker(
    on_audio_ready: Optional[Callable[[str, Path], Awaitable[None]]] = None,
    on_video_ready: Optional[Callable[[str, Path, Path], Awaitable[None]]] = None,
    poll_interval: int = 30,
):
    """
    Autonomous worker: polls discovery_queue for pending items,
    downloads them, updates status to 'downloaded'.

    Args:
        on_audio_ready: async callback(youtube_url, audio_path) — called right after audio extracted
        on_video_ready: async callback(youtube_url, audio_path, video_path) — called after full video ready
        poll_interval: seconds between queue polls
    """
    log.info("[queue worker] Starting download queue worker...")
    downloader = UniversalDownloader()

    while True:
        try:
            items = _fetch_pending_queue_items()
            if not items:
                log.debug(f"[queue worker] No pending items, sleeping {poll_interval}s")
                await asyncio.sleep(poll_interval)
                continue

            for item in items:
                url = item.get("url", "")
                item_id = item.get("id")
                if not url:
                    continue

                log.info(f"[queue worker] Processing item {item_id}: {url}")
                _update_queue_status(item_id, "downloading")

                try:
                    audio_path = None
                    video_path = None

                    async def _audio_cb(ap: Path):
                        nonlocal audio_path
                        audio_path = ap
                        log.info(f"[queue worker] Audio ready: {ap}")
                        if on_audio_ready:
                            await on_audio_ready(url, ap)

                    async def _video_cb(vp: Path):
                        nonlocal video_path
                        video_path = vp
                        log.info(f"[queue worker] Video ready: {vp}")

                    result = await downloader.download_audio_first(
                        url,
                        on_audio_ready=_audio_cb,
                        on_video_ready=_video_cb,
                    )

                    _update_queue_status(item_id, "downloaded", video_path=str(result["video"]))
                    log.info(f"[queue worker] Item {item_id} → downloaded")

                    if on_video_ready and audio_path and video_path:
                        await on_video_ready(url, audio_path, video_path)

                except Exception as e:
                    log.error(f"[queue worker] Item {item_id} failed: {e}")
                    _update_queue_status(item_id, "error", error=str(e))

        except Exception as e:
            log.error(f"[queue worker] Worker error: {e}")

        await asyncio.sleep(poll_interval)


def _fetch_pending_queue_items() -> List[dict]:
    """Fetch pending items from discovery_queue via DB or env-based fallback."""
    try:
        from db.session import SessionLocal
        from db.models import DiscoveryQueue, DiscoveryStatus
        db = SessionLocal()
        try:
            rows = (
                db.query(DiscoveryQueue)
                .filter(DiscoveryQueue.status == DiscoveryStatus.PENDING)
                .limit(5)
                .all()
            )
            return [{"id": r.id, "url": r.youtube_url} for r in rows]
        finally:
            db.close()
    except Exception as e:
        log.debug(f"[queue] DB unavailable ({e}), using env fallback")
        # Fallback: check QUEUE_URLS env var (comma-separated)
        raw = os.getenv("QUEUE_URLS", "")
        if not raw:
            return []
        return [{"id": i, "url": u.strip()} for i, u in enumerate(raw.split(",")) if u.strip()]


def _update_queue_status(item_id, status: str, video_path: str = None, error: str = None):
    """Update discovery_queue row status."""
    try:
        from db.session import SessionLocal
        from db.models import DiscoveryQueue, DiscoveryStatus
        status_map = {
            "downloading": DiscoveryStatus.DOWNLOADING if hasattr(DiscoveryStatus, "DOWNLOADING") else DiscoveryStatus.PENDING,
            "downloaded":  DiscoveryStatus.DOWNLOADED if hasattr(DiscoveryStatus, "DOWNLOADED") else DiscoveryStatus.PROCESSED,
            "error":       DiscoveryStatus.ERROR if hasattr(DiscoveryStatus, "ERROR") else DiscoveryStatus.FAILED,
        }
        db = SessionLocal()
        try:
            row = db.query(DiscoveryQueue).filter(DiscoveryQueue.id == item_id).first()
            if row:
                row.status = status_map.get(status, row.status)
                if video_path:
                    row.local_path = video_path
                if error:
                    row.error_message = error
                db.commit()
        finally:
            db.close()
    except Exception as e:
        log.debug(f"[queue] DB update skipped: {e}")


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _url_to_id(url: str) -> str:
    """Convert URL to a safe filename-friendly identifier."""
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _find_output_file(expected: Path) -> Path:
    """yt-dlp sometimes appends extension. Find the actual output file."""
    if expected.exists():
        return expected
    # Search for files with same stem
    parent = expected.parent
    stem = expected.stem
    candidates = sorted(parent.glob(f"{stem}*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    return expected  # Return expected even if missing (caller will handle error)


async def _run_async(cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run subprocess asynchronously with timeout."""
    log.debug(f"[cmd] {' '.join(cmd[:4])}...")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError(f"Command timed out after {timeout}s: {cmd[0]}")
    if proc.returncode != 0:
        err = stderr.decode(errors="replace")[:500]
        raise RuntimeError(f"{cmd[0]} failed (code {proc.returncode}): {err}")
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
