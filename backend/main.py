from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil
import aiofiles
import os
import sys
import subprocess
from pathlib import Path
import uuid
import json
from typing import Optional, List, Dict
import yt_dlp
from services.transcription import (
    INITIAL_PROMPT_TERMS,
    run_whisper_transcribe_async,
)
from services.ai_engine import _apply_corrected_segment_text
from services.viral_scout import discover_viral_moments
from dotenv import load_dotenv
import asyncio
import re
from analyzer import create_analyzer
from reframer import create_reframer
from subtitle_generator_v2 import create_subtitle_generator
from thumbnail_generator import generate_thumbnails_for_candidates
from ffmpeg_progress import run_ffmpeg_with_progress, run_ffmpeg_sync_with_progress
from render_single_clip import render_single_clip_with_progress
from slowapi.errors import RateLimitExceeded

# ── Security & observability imports ─────────────────────────
from services.observability import configure_logging, configure_sentry, CorrelationIdMiddleware, get_logger
from services.limiter import limiter, rate_limit_handler, LIMITS
from services.ssrf_guard import validate_import_url, validate_resolved_ip, YDL_SSRF_OPTS
from services.auth import get_current_user
from services.pipeline_upgrades import loudnorm_filter
from jose import jwt as _jose_jwt, JWTError as _JWTError
import hmac as _hmac
import hashlib as _hashlib
from datetime import datetime as _datetime, timedelta as _timedelta
from db.session import create_tables, get_db, SessionLocal
from db.models import (
    User,
    Video,
    Transcript,
    VideoStatus,
    TranscriptionJob,
    TranscriptionJobStatus,
)
from routers.auth import router as auth_router
from routers.factory import router as factory_router

configure_logging()
log = get_logger(__name__)

# ── Simple single-account auth ────────────────────────────────
# Credentials read from env; fall back to safe defaults shown below.
_ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@clipsgold.io")
_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ClipsGold2024!")
_SIMPLE_JWT_SECRET = os.getenv("JWT_SECRET_KEY", "clipsgold-simple-jwt-secret-change-me")
_SIMPLE_JWT_ALG    = "HS256"
_SIMPLE_JWT_EXPIRE_HOURS = 24 * 30  # 30 days


class _SimpleLoginRequest(BaseModel):
    email: str
    password: str


class _SimpleTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _make_simple_token(email: str) -> str:
    expire = _datetime.utcnow() + _timedelta(hours=_SIMPLE_JWT_EXPIRE_HOURS)
    return _jose_jwt.encode(
        {"sub": email, "exp": expire, "type": "simple"},
        _SIMPLE_JWT_SECRET,
        algorithm=_SIMPLE_JWT_ALG,
    )


def _verify_simple_token(token: str) -> str:
    """Decode token and return email, or raise HTTPException 401."""
    try:
        payload = _jose_jwt.decode(token, _SIMPLE_JWT_SECRET, algorithms=[_SIMPLE_JWT_ALG])
        if payload.get("type") != "simple":
            raise _JWTError("wrong type")
        return payload["sub"]
    except _JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

# In-memory storage for clip candidates (Human-in-the-Loop architecture)
clip_candidates_store: Dict[str, List[Dict]] = {}

# In-memory storage for transcriptions
transcription_store: Dict[str, Dict] = {}

# WebSocket connection manager for progress tracking
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[task_id] = websocket
        print(f"[OK] WebSocket connected for task: {task_id}")
    
    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            print(f"[OK] WebSocket disconnected for task: {task_id}")
    
    async def send_progress(self, task_id: str, progress: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_json(progress)
            except Exception as e:
                print(f"[WARN] Failed to send progress for {task_id}: {e}")
                self.disconnect(task_id)

manager = ConnectionManager()

# Render queue: one job at a time to avoid hangs when multiple clips are rendered at once
render_queue: asyncio.Queue = asyncio.Queue()


async def _render_worker():
    """Process render jobs one at a time from the queue."""
    while True:
        job = await render_queue.get()
        task_id = job["task_id"]
        try:
            result = await render_single_clip_with_progress(
                job["file_id"],
                job["clip_index"],
                job["platform"],
                task_id,
                clip_candidates_store,
                UPLOAD_DIR,
                CLIPS_DIR,
                OUTPUT_DIR,
                transcription_store,
                cut_video_segment_enhanced,
                manual_crop_x=job.get("manual_crop_x"),
                show_hook=job.get("show_hook", True),
                subtitle_style=job.get("subtitle_style", "hormozi"),
                subtitle_language=job.get("subtitle_language", "auto"),
                enable_jump_cut=job.get("enable_jump_cut", False),
                enable_sfx=job.get("enable_sfx", True),
                use_semantic_chunking=job.get("use_semantic_chunking", True),
                start_time_override=job.get("start_time_override"),
                end_time_override=job.get("end_time_override"),
                render_mode=job.get("render_mode", "auto"),
            )
            download_path = f"/download-clip/{job['file_id']}/{result['clip_id']}"
            await manager.send_progress(task_id, {
                "status": "success",
                "download_url": download_path,
                "task_id": task_id,
                "file_id": job["file_id"],
                "clip_id": result["clip_id"],
                "filename": result["filename"],
                "title": result.get("title", ""),
            })
        except Exception as e:
            import traceback
            err_msg = str(e) or repr(e) or type(e).__name__
            print(f"❌ Render failed: {err_msg}")
            traceback.print_exc()
            await manager.send_progress(task_id, {"status": "error", "error": err_msg})
        finally:
            render_queue.task_done()


# Load environment variables from .env file
load_dotenv()


app = FastAPI(title="ClipsGold API", version="1.0.0")

# ── Sentry (no-op if SENTRY_DSN not set) ─────────────────────
configure_sentry(app)

# ── Rate limiter ──────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# ── Auth router ───────────────────────────────────────────────
app.include_router(auth_router)

# ── Factory router (Autonomous AI Factory) ────────────────────
app.include_router(factory_router)


async def _auto_cleanup_worker():
    """Delete files older than 24 hours from uploads/, outputs/, and temp/ every 60 minutes."""
    import time as _time
    while True:
        await asyncio.sleep(3600)  # wait 60 minutes between runs
        cutoff = _time.time() - 86400  # 24 hours ago
        cleaned = 0
        dirs_to_scan = [UPLOAD_DIR, OUTPUT_DIR, CLIPS_DIR / "temp"]
        for directory in dirs_to_scan:
            if not directory.exists():
                continue
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                    try:
                        file_path.unlink()
                        cleaned += 1
                    except Exception as e:
                        print(f"[WARN] Auto-cleanup: could not delete {file_path}: {e}")
        if cleaned:
            print(f"🧹 Auto-cleanup: deleted {cleaned} file(s) older than 24h")


def _restore_transcription_store() -> None:
    """Re-populate in-memory cache from DB first, then disk fallback."""
    count = 0
    try:
        with SessionLocal() as db:
            rows = (
                db.query(Video.file_id, Transcript.raw_text, Transcript.refined_text, Transcript.language, Transcript.segments_json)
                .join(Transcript, Transcript.video_id == Video.id)
                .all()
            )
            for file_id, raw_text, refined_text, language, segments_json in rows:
                transcription_store[file_id] = {
                    "text": refined_text or raw_text or "",
                    "language": language or "",
                    "segments": segments_json or [],
                }
                count += 1
    except Exception as exc:
        log.warning("transcription_restore_db_failed", error=str(exc))

    if count:
        log.info("transcriptions_restored_from_db", count=count)
        return

    # Backward-compatible fallback for old file-only records.
    for f in OUTPUT_DIR.glob("*_transcription.json"):
        file_id = f.name[: -len("_transcription.json")]
        try:
            with f.open("r", encoding="utf-8") as fp:
                transcription_store[file_id] = json.load(fp)
            count += 1
        except Exception as exc:
            log.warning("transcription_restore_failed", file_id=file_id, error=str(exc))
    if count:
        log.info("transcriptions_restored_from_disk", count=count)


def _save_transcript_to_db(
    file_id: str,
    owner_id: str,
    transcript_data: Dict,
    duration_seconds: Optional[float] = None,
) -> Optional[str]:
    """Persist transcript payload into transcripts table (upsert by video_id). Returns transcript row id."""
    try:
        with SessionLocal() as db:
            video = (
                db.query(Video)
                .filter(Video.file_id == file_id, Video.owner_id == owner_id)
                .first()
            )
            if not video:
                log.warning("transcript_save_skipped_no_video", file_id=file_id, owner_id=owner_id)
                return None

            row = db.query(Transcript).filter(Transcript.video_id == video.id).first()
            if not row:
                row = Transcript(video_id=video.id)
                db.add(row)

            text = transcript_data.get("text", "")
            row.raw_text = text
            row.refined_text = text
            row.segments_json = transcript_data.get("segments", [])
            row.language = transcript_data.get("language")
            row.whisper_model = "whisper-1"
            if duration_seconds is not None:
                row.duration_seconds = duration_seconds

            video.status = VideoStatus.transcribed
            video.error_message = None
            db.commit()
            db.refresh(row)
            return str(row.id)
    except Exception as exc:
        log.warning("transcript_save_failed", file_id=file_id, error=str(exc))
        return None


def _touch_video_job_status(
    file_id: str,
    owner_id: str,
    status: VideoStatus,
    error_message: Optional[str] = None,
) -> None:
    try:
        with SessionLocal() as db:
            video = (
                db.query(Video)
                .filter(Video.file_id == file_id, Video.owner_id == owner_id)
                .first()
            )
            if not video:
                return
            video.status = status
            video.error_message = error_message
            db.commit()
    except Exception as exc:
        log.warning("video_job_status_failed", file_id=file_id, error=str(exc))


def _fail_transcription_job(job_id: str, message: str) -> None:
    try:
        with SessionLocal() as db:
            job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if not job:
                return
            job.status = TranscriptionJobStatus.failed
            job.error_message = (message or "")[:4000]
            db.commit()
    except Exception as exc:
        log.warning("transcription_job_fail_update_failed", job_id=job_id, error=str(exc))


async def _run_transcription_job(job_id: str, file_id: str, owner_id: str) -> None:
    input_file = UPLOAD_DIR / f"{file_id}.mp4"
    audio_file = OUTPUT_DIR / f"{file_id}_audio.mp3"

    def _persist_progress(done: int, total: int) -> None:
        with SessionLocal() as db:
            job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if job:
                job.progress = done
                job.total_chunks = total
                db.commit()

    try:
        with SessionLocal() as db:
            job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if not job:
                log.error("transcription_job_missing_row", job_id=job_id)
                return

        if not input_file.exists():
            _fail_transcription_job(job_id, "Video file not found")
            return

        _touch_video_job_status(file_id, owner_id, VideoStatus.transcribing, None)

        video_duration = await asyncio.to_thread(get_video_duration, input_file)
        await asyncio.to_thread(extract_audio, input_file, audio_file)

        async def on_chunk_done(done: int, total: int) -> None:
            await asyncio.to_thread(_persist_progress, done, total)

        result, skipped_list = await run_whisper_transcribe_async(
            audio_path=audio_file,
            initial_prompt=INITIAL_PROMPT_TERMS,
            on_chunk_done=on_chunk_done,
            parallel_chunks=3,
        )

        try:
            if audio_file.exists():
                audio_file.unlink()
        except OSError:
            pass

        segments_in = result.get("segments") or []
        segments = fill_segment_gaps(segments_in, video_duration)
        result["segments"] = segments

        transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"

        def _write_transcription_disk() -> None:
            with transcription_file.open("w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        await asyncio.to_thread(_write_transcription_disk)

        transcript_id = await asyncio.to_thread(
            _save_transcript_to_db,
            file_id,
            owner_id,
            result,
            video_duration,
        )

        transcription_store[file_id] = result

        with SessionLocal() as db:
            job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if job:
                job.status = TranscriptionJobStatus.done
                job.progress = job.total_chunks or job.progress
                job.transcript_id = transcript_id
                job.skipped_chunks_json = skipped_list or None
                job.error_message = None
                db.commit()

    except Exception as e:
        log.exception("transcription_job_error", job_id=job_id, file_id=file_id)
        try:
            if audio_file.exists():
                audio_file.unlink()
        except OSError:
            pass
        _fail_transcription_job(job_id, str(e))
        _touch_video_job_status(file_id, owner_id, VideoStatus.error, str(e))


def _load_transcript_from_db(file_id: str, owner_id: str) -> Optional[Dict]:
    """Load transcript payload from transcripts table for a specific owner/file."""
    try:
        with SessionLocal() as db:
            row = (
                db.query(Transcript)
                .join(Video, Video.id == Transcript.video_id)
                .filter(Video.file_id == file_id, Video.owner_id == owner_id)
                .first()
            )
            if not row:
                return None
            return {
                "text": row.refined_text or row.raw_text or "",
                "language": row.language or "",
                "segments": row.segments_json or [],
            }
    except Exception as exc:
        log.warning("transcript_load_failed", file_id=file_id, error=str(exc))
        return None


@app.on_event("startup")
async def start_background_workers():
    """Initialise DB tables, start render queue worker and auto-cleanup service."""
    try:
        create_tables()
        log.info("db_tables_created")
    except Exception as e:
        log.error("db_init_failed", error=str(e))

    asyncio.create_task(_render_worker())
    log.info("render_worker_started")
    asyncio.create_task(_auto_cleanup_worker())
    log.info("cleanup_worker_started")

    # Restore transcriptions from disk (survives container restart)
    _restore_transcription_store()

    # One-time background-video check at startup (not on every request)
    check_background_videos()

    autonomous_mode = os.getenv("AUTONOMOUS_MODE", "False").lower() == "true"
    if autonomous_mode:
        log.info("autonomous_mode_enabled")


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
CLIPS_DIR = Path("clips")
THUMBNAILS_DIR = Path("thumbnails")
BACKGROUND_VIDEOS_DIR = BASE_DIR / "assets" / "background_videos"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)
THUMBNAILS_DIR.mkdir(exist_ok=True)
BACKGROUND_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

# YouTube cookies: optional for age-restricted / throttled downloads
YOUTUBE_COOKIES_FILE = os.environ.get("YOUTUBE_COOKIES_FILE")  # path to Netscape cookie file
YOUTUBE_COOKIES_STRING = os.environ.get("YOUTUBE_COOKIES")      # raw Cookie header value
YOUTUBE_COOKIES_GENERATED_PATH = BASE_DIR / "youtube_cookies_generated.txt"


def _cookie_string_to_netscape(s: str) -> str:
    """Convert 'name1=value1; name2=value2' (or 'Cookie: ...') to Netscape format."""
    s = s.strip()
    if s.lower().startswith("cookie:"):
        s = s[7:].strip()
    lines = ["# Netscape HTTP Cookie File", "# https://curl.se/docs/http-cookies.html"]
    for part in s.split(";"):
        part = part.strip()
        if not part:
            continue
        idx = part.find("=")
        if idx <= 0:
            continue
        name, value = part[:idx].strip(), part[idx + 1 :].strip()
        if name.startswith("__Secure-") or name.startswith("__Host-"):
            secure = "TRUE"
        else:
            secure = "TRUE"
        # domain, includeSubdomains, path, secure, expiration, name, value
        lines.append(f".youtube.com\tTRUE\t/\t{secure}\t9999999999\t{name}\t{value}")
    return "\n".join(lines)


def _get_youtube_cookiefile_path() -> Optional[Path]:
    """Return path to cookie file for yt-dlp, or None if not configured."""
    if YOUTUBE_COOKIES_FILE:
        p = Path(YOUTUBE_COOKIES_FILE)
        if p.exists():
            return p
    if YOUTUBE_COOKIES_STRING:
        try:
            content = _cookie_string_to_netscape(YOUTUBE_COOKIES_STRING)
            YOUTUBE_COOKIES_GENERATED_PATH.write_text(content, encoding="utf-8")
            return YOUTUBE_COOKIES_GENERATED_PATH
        except Exception as e:
            print(f"[WARN] Failed to write YouTube cookies file: {e}")
    return None


# Helper function to find ffmpeg/ffprobe (local or system)
def get_ffmpeg_path():
    local_ffmpeg = BASE_DIR / "ffmpeg.exe"
    return str(local_ffmpeg) if local_ffmpeg.exists() else "ffmpeg"

def get_ffprobe_path():
    local_ffprobe = BASE_DIR / "ffprobe.exe"
    return str(local_ffprobe) if local_ffprobe.exists() else "ffprobe"

def check_background_videos():
    """
    Check if background videos are available.
    Logs warning if directory is empty.
    """
    video_files = list(BACKGROUND_VIDEOS_DIR.glob("*.mp4"))
    
    if not video_files:
        print("\n" + "="*60)
        print("[WARN] WARNING: Background Videos Directory Empty")
        print("="*60)
        print(f"Directory: {BACKGROUND_VIDEOS_DIR}")
        print("No .mp4 files found for 'satisfying' split-screen mode.")
        print("System will fallback to standard single-view crop.")
        print("\nTo enable satisfying split-screen:")
        print("1. Add .mp4 files to backend/assets/background_videos/")
        print("2. Recommended: Minecraft parkour, Subway Surfers, ASMR")
        print("3. Format: 1080x1080 or any (will be cropped)")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("[OK] Background Videos Available")
        print("="*60)
        print(f"Found {len(video_files)} background video(s):")
        for i, video in enumerate(video_files[:5], 1):
            print(f"  {i}. {video.name}")
        if len(video_files) > 5:
            print(f"  ... and {len(video_files) - 5} more")
        print("Satisfying split-screen mode: ENABLED")
        print("="*60 + "\n")


def check_ffmpeg():
    try:
        subprocess.run(
            [get_ffmpeg_path(), "-version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False



def get_video_duration(video_path: Path) -> float:
    result = subprocess.run(
        [
            get_ffprobe_path(),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return float(result.stdout.strip())


def fill_segment_gaps(segments: List[Dict], video_duration: float, gap_threshold: float = 0.3) -> List[Dict]:
    """
    Insert placeholder segments for gaps so subtitle timeline covers 0..video_duration.
    Avoids "subs 0:00-0:16, 0:30-0:45" when video actually runs 0:00-0:46.
    """
    if not segments or video_duration <= 0:
        return segments
    sorted_segs = sorted(segments, key=lambda s: s.get("start", 0))
    out = []
    prev_end = 0.0
    for seg in sorted_segs:
        start = seg.get("start", 0)
        end = seg.get("end", start + 0.1)
        if start - prev_end >= gap_threshold:
            out.append({
                "start": prev_end,
                "end": start,
                "text": "",
                "words": [],
            })
        out.append(seg)
        prev_end = max(prev_end, end)
    if video_duration - prev_end >= gap_threshold:
        out.append({
            "start": prev_end,
            "end": video_duration,
            "text": "",
            "words": [],
        })
    return out


def extract_audio(video_path: Path, audio_path: Path):
    # MP3 64kbps mono — ~8KB/s vs 32KB/s for WAV. 4x smaller → fewer API chunks.
    subprocess.run(
        [
            get_ffmpeg_path(),
            "-i", str(video_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            "-y",
            str(audio_path)
        ],
        capture_output=True,
        check=True
    )


async def cut_video_segment_enhanced(
    input_path: Path,
    output_path: Path,
    start_time: float,
    end_time: float,
    subtitle_path: Optional[Path] = None,
    crop_filter: Optional[str] = None,
    zoom_filter: Optional[str] = None,
    video_fps: Optional[float] = None,
    is_split_screen: bool = False,
    task_id: Optional[str] = None,
    background_video_path: Optional[Path] = None,
    manual_crop_x: Optional[int] = None,
    letterbox_with_blur: bool = False,
    sfx_path: Optional[Path] = None,
    jump_cut_segments: Optional[List[Dict]] = None,
    emoji_sequence: Optional[List[Dict]] = None,
):
    """
    TWO-PASS RENDERING: 1) Physical cut to reset timestamps, 2) Apply effects with 0-based subtitles

    Args:
        background_video_path: Path to background video for "satisfying" split-screen mode
        manual_crop_x: Manual override for crop X position (bypasses AI face detection)
        letterbox_with_blur: If True, scale video to fit 1080x1920 (letterbox) and fill bars with blurred background
        sfx_path: Optional SFX file to amix into audio at t=0 (hook moment)
        jump_cut_segments: Optional list of {start, end} keep-segments (relative to clip) to concat-cut silences
        emoji_sequence: Optional list of emoji pop-up configs [{"emoji": "🔥", "start": 2.0, "duration": 1.5}, ...]
    """
    duration = end_time - start_time

    # Progress callback for WebSocket updates
    async def send_progress(tid: str, progress: dict):
        await manager.send_progress(tid, progress)
    
    # Generate temp file path for intermediate cut
    temp_dir = output_path.parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    temp_cut_file = temp_dir / f"temp_cut_{output_path.stem}.mp4"
    
    # ========== JUMP-CUT PRE-PASS (only when jump-cut enabled) ==========
    _use_jump_cut = bool(jump_cut_segments and len(jump_cut_segments) > 1)

    if _use_jump_cut:
        print(f"\n  === TWO-PASS RENDERING (Jump-Cut) ===")
        print(f"  -> Pre-Pass: Jump-cut segments concat ({len(jump_cut_segments)} segments)")
        concat_list_path = temp_dir / f"concat_{output_path.stem}.txt"
        segment_files = []
        for i, seg in enumerate(jump_cut_segments):
            seg_start = start_time + seg["start"]
            seg_dur = seg["end"] - seg["start"]
            if seg_dur <= 0:
                continue
            seg_file = temp_dir / f"seg_{output_path.stem}_{i}.mp4"
            cmd_seg = [
                get_ffmpeg_path(),
                "-ss", str(seg_start), "-t", str(seg_dur),
                "-i", str(input_path),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-threads", "0",
                "-c:a", "aac", "-b:a", "128k", "-y", str(seg_file)
            ]
            r = subprocess.run(cmd_seg, capture_output=True, text=True)
            if r.returncode == 0:
                segment_files.append(seg_file)
        if segment_files:
            with concat_list_path.open("w") as f:
                for sf in segment_files:
                    f.write(f"file '{sf.as_posix()}'\n")
            cmd_concat = [
                get_ffmpeg_path(),
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy", "-y", str(temp_cut_file)
            ]
            r2 = subprocess.run(cmd_concat, capture_output=True, text=True)
            if r2.returncode != 0:
                print(f"  [FAIL] Jump-cut concat failed, falling back to single-pass")
                _use_jump_cut = False
            else:
                for sf in temp_dir.glob(f"seg_{output_path.stem}_*.mp4"):
                    try: sf.unlink()
                    except Exception: pass
                print(f"  [OK] Jump-cut concat complete")
        else:
            _use_jump_cut = False  # no valid segments, fallback

    # _render_input: source for the render pass
    # Single-pass uses input seeking + setpts reset; jump-cut uses pre-cut temp file
    if _use_jump_cut:
        _render_input = str(temp_cut_file)
        _ss_args: list = []       # already cut, no seeking needed
        _need_setpts = False      # timestamps already start at 0
    else:
        _render_input = str(input_path)
        _ss_args = ["-ss", str(start_time), "-t", str(duration)]
        _need_setpts = True       # seeking → add setpts=PTS-STARTPTS for subtitle sync
        print(f"\n  === SINGLE-PASS RENDERING ===")
        print(f"  -> Direct input seeking: -ss {start_time:.2f}s (setpts reset for subtitle sync)")

    # ========== RENDER PASS: APPLY ALL EFFECTS ==========
    print(f"  -> Render: Apply effects (crop, subtitles, audio mastering)")
    
    # Probe video dimensions to clamp crop filter safely
    import re
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0",
             str(input_path)],   # probe source; dimensions identical regardless of seek
            capture_output=True, text=True
        )
        parts = probe.stdout.strip().split(",")
        vid_width, vid_height = int(parts[0]), int(parts[1])
        print(f"  [INFO] Video dimensions: {vid_width}x{vid_height}")
    except Exception as e:
        print(f"  [WARN] Could not probe video dimensions: {e}")
        vid_width, vid_height = None, None

    # Detect vertical source (portrait 9:16 or similar)
    _is_vertical = bool(vid_width and vid_height and vid_height > vid_width)
    if _is_vertical:
        print(f"  [INFO] Vertical source detected ({vid_width}x{vid_height}) — passthrough mode (no crop/blur)")

    # Clamp crop_filter so it never exceeds actual video bounds
    if crop_filter and vid_width and vid_height:
        crop_match = re.search(r'crop=(\d+):(\d+):(\d+):(\d+)', crop_filter)
        if crop_match:
            cw, ch, cx, cy = [int(v) for v in crop_match.groups()]
            cw = min(cw, vid_width)
            ch = min(ch, vid_height)
            # ensure even values for FFmpeg codecs
            cw = (cw // 2) * 2
            ch = (ch // 2) * 2
            cx = max(0, min(cx, vid_width - cw))
            cy = max(0, min(cy, vid_height - ch))
            safe_crop = f"crop={cw}:{ch}:{cx}:{cy}"
            if safe_crop != crop_filter.split("crop=", 1)[1][:len(safe_crop)]:
                print(f"  [WARN] crop_filter adjusted: crop={crop_match.group(0)} → {safe_crop} (video {vid_width}x{vid_height})")
            crop_filter = re.sub(r'crop=\d+:\d+:\d+:\d+', safe_crop, crop_filter)

    # Apply manual crop override if provided
    if manual_crop_x is not None and crop_filter:
        # Ensure manual_crop_x is even for FFmpeg
        manual_crop_x = (manual_crop_x // 2) * 2

        crop_match = re.search(r'crop=(\d+):(\d+):(\d+):(\d+)', crop_filter)
        if crop_match:
            crop_w, crop_h, crop_x, crop_y = crop_match.groups()
            crop_w_int = int(crop_w)

            # Clamp X so crop doesn't go out of bounds
            if vid_width:
                clamped_x = max(0, min(manual_crop_x, vid_width - crop_w_int))
                if clamped_x != manual_crop_x:
                    print(f"  [WARN] manual_crop_x={manual_crop_x} clamped to {clamped_x} (video width={vid_width})")
                manual_crop_x = clamped_x

            new_crop_filter = crop_filter.replace(
                f'crop={crop_w}:{crop_h}:{crop_x}:{crop_y}',
                f'crop={crop_w}:{crop_h}:{manual_crop_x}:{crop_y}'
            )
            crop_filter = new_crop_filter
            print(f"  [OK] Manual crop override: X={manual_crop_x} (AI suggested: {crop_x})")
    
    # Logo watermark asset (merged into this pass — no separate re-encode)
    _logo_path = Path(__file__).parent / "assets" / "logo.png"
    _has_logo = _logo_path.exists()
    # Logo input index: right after main(0) + optional background(1)
    _logo_idx = 2 if (background_video_path and background_video_path.exists()) else 1

    # Build render command
    cmd_pass2 = [get_ffmpeg_path()]
    cmd_pass2.extend(_ss_args)                    # [-ss t -t d] for single-pass, [] for jump-cut
    cmd_pass2.extend(["-i", _render_input])

    # Add background video input if available (for satisfying split-screen)
    if background_video_path and background_video_path.exists():
        cmd_pass2.extend(["-i", str(background_video_path)])
        print(f"     • Background video input: {background_video_path.name}")

    # Add logo input now (before SFX so SFX index stays consistent)
    if _has_logo:
        cmd_pass2.extend(["-i", str(_logo_path)])
        print(f"     • Logo input: {_logo_path.name} (input idx={_logo_idx})")
    
    # Helper: prepend setpts=PTS-STARTPTS to filter_complex for single-pass subtitle sync
    def _pts(fc: str) -> str:
        if not _need_setpts:
            return fc
        return "[0:v]setpts=PTS-STARTPTS[_v0];" + fc.replace("[0:v]", "[_v0]", 1)

    # Helper: inject logo overlay at the end of a filter_complex string
    def _with_logo(fc: str, out_label: str = "[out]") -> str:
        if not _has_logo:
            return fc
        idx = fc.rfind(out_label)
        if idx == -1:
            return fc
        fc_mod = fc[:idx] + "[pre_logo]" + fc[idx + len(out_label):]
        logo_chain = (
            f"[{_logo_idx}:v]scale=200:-1,format=rgba,colorchannelmixer=aa=0.85[logo_wm];"
            f"[pre_logo][logo_wm]overlay=W-w-20:20{out_label}"
        )
        return f"{fc_mod};{logo_chain}"

    # Check if split_screen mode (requires filter_complex)
    if _is_vertical:
        # ── VERTICAL SOURCE MODE ──────────────────────────────────────────
        # Source is already portrait — just scale to 1080x1920 (pad if not exact 9:16)
        # No crop, no blur background, no face detection needed.
        print(f"     • VERTICAL MODE: scale to 1080x1920 (no crop, no blur)")
        rel_sub = (
            str(subtitle_path.resolve()).replace('\\', '/').replace(':', '\\:')
            if subtitle_path and subtitle_path.exists() else None
        )
        _pad = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"
        _vf_chain = f"{_pad},subtitles={rel_sub}" if rel_sub else _pad

        _master_chain = "acompressor=threshold=0.089:ratio=4:attack=5:release=50,alimiter=level_in=1:level_out=1:limit=0.891:attack=5:release=50:level=disabled"

        _vf = ("setpts=PTS-STARTPTS," + _vf_chain) if _need_setpts else _vf_chain
        _af_chain = ("asetpts=PTS-STARTPTS," + _master_chain) if _need_setpts else _master_chain
        if _has_logo:
            _video_fc = _with_logo(f"[0:v]{_vf}[out_v]", "[out_v]")
            _audio_fc = f"[0:a]{_af_chain}[out_a]"
            cmd_pass2.extend(["-filter_complex", f"{_video_fc};{_audio_fc}"])
            cmd_pass2.extend(["-map", "[out_v]", "-map", "[out_a]"])
        else:
            cmd_pass2.extend(["-vf", _vf])
            cmd_pass2.extend(["-af", _af_chain])
        if rel_sub:
            print(f"     • Subtitles: {rel_sub}")
        print(f"     • Audio: acompressor -> alimiter")

    elif is_split_screen and crop_filter:
        # Check if we have background video for "satisfying" mode
        if background_video_path and background_video_path.exists():
            print(f"     • SATISFYING SPLIT SCREEN MODE: Using -filter_complex with background video")
        else:
            print(f"     • SPLIT SCREEN MODE: Using -filter_complex (dual face crops)")
        
        # Build filter_complex for split screen
        if background_video_path and background_video_path.exists():
            # SATISFYING SPLIT-SCREEN MODE: crop_filter already contains the full filter
            # from create_satisfying_split_screen_filter() in reframer.py
            # It expects [0:v] = speaker, [1:v] = background video
            # Format: [0:v]crop=...[speaker];[1:v]loop=...[background];[speaker][background]vstack[stacked];[stacked]scale=...[out]
            
            # Add subtitles if exists
            if subtitle_path and subtitle_path.exists():
                abs_subtitle_path = str(subtitle_path.resolve()).replace('\\', '/').replace(':', '\\:')
                # Modify crop_filter to add subtitles before final output
                # Replace [out] with [pre_sub], then add subtitle filter
                filter_complex = crop_filter.replace('[out]', '[pre_sub]')
                filter_complex += f";[pre_sub]subtitles={abs_subtitle_path}[out]"
                print(f"     • Subtitles: {abs_subtitle_path} (centered at border)")
            else:
                filter_complex = crop_filter
            
            print(f"     • Speaker crop: top 50% (1080x960)")
            print(f"     • Background: bottom 50% (1080x960, looped)")
            print(f"     • Final: 1080x1920 (9:16)")
            cmd_pass2.extend(["-filter_complex", _pts(_with_logo(filter_complex))])
            cmd_pass2.extend(["-map", "[out]"])  # Map video output
            cmd_pass2.extend(["-map", "0:a"])    # Map audio from speaker (mute background)
        else:
            # DUAL FACE SPLIT-SCREEN MODE (old logic)
            # Step 1: Apply zoom to input
            stable_zoom = "scale=iw*1.1:ih*1.1,crop=iw/1.1:ih/1.1:(iw-iw/1.1)/2:(ih-ih/1.1)/2"
            
            # Step 2: crop_filter contains split/vstack logic from reframer
            # Example: [0:v]split=2[left][right];[left]crop=...[left_crop];[right]crop=...[right_crop];[left_crop][right_crop]vstack=inputs=2
            # We need to replace [0:v] with [zoomed] to chain after zoom
            split_filter = crop_filter.replace('[0:v]', '[zoomed]')
            
            # Step 3: Scale to final 9:16 resolution (1080x1920)
            # The vstack output needs a label, let's add it
            if split_filter.endswith('vstack=inputs=2'):
                split_filter += '[vstacked]'
            
            # Step 4: Add subtitles if exists
            if subtitle_path and subtitle_path.exists():
                abs_subtitle_path = str(subtitle_path.resolve()).replace('\\', '/').replace(':', '\\:')
                subtitle_filter = f"[vstacked]scale=1080:1920,subtitles={abs_subtitle_path}[out]"
                print(f"     • Subtitles: {abs_subtitle_path} (0-based, perfect sync!)")
            else:
                subtitle_filter = "[vstacked]scale=1080:1920[out]"
            
            # Combine all parts
            filter_complex = f"[0:v]{stable_zoom}[zoomed];{split_filter};{subtitle_filter}"

            print(f"     • Zoom: scale+crop (no freeze)")
            print(f"     • Split Screen: split->crop->vstack")
            print(f"     • Scale: 1080x1920")
            cmd_pass2.extend(["-filter_complex", _pts(_with_logo(filter_complex))])
            cmd_pass2.extend(["-map", "[out]"])  # Map video output
            cmd_pass2.extend(["-map", "0:a"])    # Map audio from input
    else:
        # Standard single crop mode (use -vf or filter_complex for letterbox+blur)
        if letterbox_with_blur:
            # Blur background: original frame fits entirely in 9:16, blurred version fills the rest
            print(f"     • BLUR BACKGROUND MODE (no face detected)")
            rel_sub = str(subtitle_path.resolve()).replace('\\', '/').replace(':', '\\:') if subtitle_path and subtitle_path.exists() else None
            # [bg]: scale to fill 1080x1920, apply heavy blur
            # [fg]: scale to fit inside 1080x1920 keeping aspect ratio
            # overlay fg centered on blurred bg
            if rel_sub:
                filter_complex = (
                    f"[0:v]split=2[fg_src][bg_src];"
                    f"[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];"
                    f"[fg_src]scale=1080:-1[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2[pre_sub];"
                    f"[pre_sub]subtitles={rel_sub}[out]"
                )
            else:
                filter_complex = (
                    f"[0:v]split=2[fg_src][bg_src];"
                    f"[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];"
                    f"[fg_src]scale=1080:-1[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
                )
            cmd_pass2.extend(["-filter_complex", _pts(_with_logo(filter_complex))])
            cmd_pass2.extend(["-map", "[out]", "-map", "0:a"])
        else:
            print(f"     • STANDARD MODE: Using filter_complex")
            # Build video filter chain: crop to 9:16 → scale to 1080x1920
            video_parts = []
            if crop_filter:
                # Use AI face-centered crop from reframer (expected to produce 9:16 portrait)
                crop_match_check = re.search(r'crop=(\d+):(\d+):(\d+):(\d+)', crop_filter)
                is_noop = (
                    crop_match_check and vid_width and vid_height
                    and int(crop_match_check.group(1)) >= vid_width
                    and int(crop_match_check.group(2)) >= vid_height
                    and int(crop_match_check.group(3)) == 0
                    and int(crop_match_check.group(4)) == 0
                )
                if is_noop:
                    print(f"     • Crop: skipped (no-op for {vid_width}x{vid_height} video)")
                else:
                    video_parts.append(crop_filter)
                    print(f"     • Crop: {crop_filter[:60]}...")
            else:
                # Fallback: center-crop to 9:16 (works for 16:9, 4:3, 1:1, or any source)
                # trunc(ih*9/16/2)*2 ensures even pixel width required by libx264
                video_parts.append("crop=trunc(ih*9/16/2)*2:ih")
                print(f"     • Crop: center-crop 9:16 fallback (crop=trunc(ih*9/16/2)*2:ih)")
            video_parts.append("scale=1080:1920")
            if subtitle_path and subtitle_path.exists():
                abs_subtitle_path = str(subtitle_path.resolve()).replace('\\', '/').replace(':', '\\:')
                video_parts.append(f"subtitles={abs_subtitle_path}")
                print(f"     • Subtitles: {abs_subtitle_path} (0-based, perfect sync!)")
            
            # Emoji overlays disabled: FFmpeg drawtext with emoji crashes on Ubuntu (exit code 234)
            
            video_chain = ",".join(video_parts)
            print(f"     • Scale: 1080x1920")

            # ── Audio mastering chain ──────────────────────────────────
            _master_chain = "acompressor=threshold=0.089:ratio=4:attack=5:release=50,alimiter=level_in=1:level_out=1:limit=0.891:attack=5:release=50:level=disabled"

            if sfx_path and sfx_path.exists():
                cmd_pass2.extend(["-i", str(sfx_path)])
                # SFX index: after main(0) + optional logo(logo_idx) → logo_idx+1 if logo, else 1
                sfx_input_idx = (_logo_idx + 1) if _has_logo else (2 if (background_video_path and background_video_path.exists()) else 1)
                audio_filter = (
                    f"[0:a]volume=1.0[main_a];"
                    f"[{sfx_input_idx}:a]adelay=0|0,volume=0.4[sfx_a];"
                    f"[main_a][sfx_a]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[mixed_a];"
                    f"[mixed_a]{_master_chain}[out_a]"
                )
                _vfc = _pts(_with_logo(f"[0:v]{video_chain}[out_v]", "[out_v]"))
                cmd_pass2.extend(["-filter_complex", f"{_vfc};{audio_filter}"])
                cmd_pass2.extend(["-map", "[out_v]", "-map", "[out_a]"])
                print(f"     • Audio: SFX mix -> acompressor -> alimiter")
            else:
                # No SFX
                _af_chain = ("asetpts=PTS-STARTPTS," + _master_chain) if _need_setpts else _master_chain
                if _has_logo:
                    _vf_base = ("setpts=PTS-STARTPTS," + video_chain) if _need_setpts else video_chain
                    _video_fc = _with_logo(f"[0:v]{_vf_base}[out_v]", "[out_v]")
                    _audio_fc = f"[0:a]{_af_chain}[out_a]"
                    cmd_pass2.extend(["-filter_complex", f"{_video_fc};{_audio_fc}"])
                    cmd_pass2.extend(["-map", "[out_v]", "-map", "[out_a]"])
                else:
                    _vf = ("setpts=PTS-STARTPTS," + video_chain) if _need_setpts else video_chain
                    cmd_pass2.extend(["-vf", _vf])
                    cmd_pass2.extend(["-af", _af_chain])
                print(f"     • Audio: acompressor -> alimiter")
    
    # Common encoding settings
    cmd_pass2.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-threads", "0"])
    cmd_pass2.extend(["-c:a", "aac", "-b:a", "128k"])
    
    # Output specs for compatibility
    cmd_pass2.extend(["-r", "30"])
    cmd_pass2.extend(["-pix_fmt", "yuv420p"])
    cmd_pass2.extend(["-async", "1"])
    cmd_pass2.extend(["-vsync", "cfr"])
    cmd_pass2.extend(["-y", str(output_path)])
    
    # ── Subtitle file diagnostics before Pass 2 ──────────────────────────
    if subtitle_path:
        if subtitle_path.exists():
            sub_size = subtitle_path.stat().st_size
            print(f"  [SUB] Subtitle file: {subtitle_path} (size={sub_size} bytes)")
            try:
                sub_lines = subtitle_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
                print(f"  [SUB] First 30 lines of subtitle file:")
                for i, ln in enumerate(sub_lines[:30]):
                    print(f"    {i+1:3d}: {ln}")
            except Exception as _sub_e:
                print(f"  [SUB] Could not read subtitle file: {_sub_e}")
        else:
            print(f"  [SUB] ⚠️  Subtitle file NOT FOUND: {subtitle_path}")

    # Run Pass 2 with progress tracking if task_id provided
    # On Windows, asyncio.create_subprocess_exec can raise NotImplementedError;
    # run FFmpeg in a thread with sync Popen and schedule progress on the main loop.
    print(f"  -> Pass 2 command: {' '.join(str(c) for c in cmd_pass2)}")
    if task_id:
        print(f"  -> Tracking progress via WebSocket (task: {task_id})")
        if sys.platform == "win32":
            loop = asyncio.get_running_loop()
            result_pass2 = await asyncio.to_thread(
                run_ffmpeg_sync_with_progress,
                cmd_pass2,
                duration,
                task_id,
                send_progress,
                loop,
            )
        else:
            result_pass2 = await run_ffmpeg_with_progress(
                cmd_pass2,
                duration,
                task_id,
                send_progress,
            )
    else:
        print(f"     Command: {' '.join(str(c) for c in cmd_pass2)}")
        result_pass2 = subprocess.run(cmd_pass2, capture_output=True, text=True)
    
    if result_pass2.returncode != 0:
        raw_stderr = result_pass2.stderr or b""
        try:
            stderr_str = raw_stderr.decode("utf-8", errors="replace") if isinstance(raw_stderr, bytes) else str(raw_stderr)
        except Exception:
            stderr_str = repr(raw_stderr)
        last_lines = stderr_str.splitlines()[-10:]
        print(f"  [FAIL] Pass 2 FAILED (exit {result_pass2.returncode}) — last 10 stderr lines:")
        for ln in last_lines:
            print(f"     {ln}")
        # Cleanup temp file before raising error
        if temp_cut_file.exists():
            temp_cut_file.unlink()
        print(f"FFmpeg stderr: {result_pass2.stderr.decode('utf-8', errors='replace') if isinstance(result_pass2.stderr, bytes) else str(result_pass2.stderr)}")
        print(f"FFmpeg stdout: {result_pass2.stdout.decode('utf-8', errors='replace') if isinstance(result_pass2.stdout, bytes) else str(result_pass2.stdout)}")
        raise subprocess.CalledProcessError(result_pass2.returncode, cmd_pass2, result_pass2.stdout, result_pass2.stderr)
    
    print(f"  [OK] Render complete: Effects + logo watermark applied in single pass")

    # ========== CLEANUP: DELETE TEMP FILE ==========
    if temp_cut_file.exists():
        temp_cut_file.unlink()
        print(f"  [OK] Cleanup: Temp file deleted")
    
    print(f"  === RENDER COMPLETE [OK] ===")


@app.post("/auth/simple-login", response_model=_SimpleTokenResponse)
async def simple_login(body: _SimpleLoginRequest):
    """Single hardcoded account login — no DB required."""
    email_ok = _hmac.compare_digest(body.email.lower().strip(), _ADMIN_EMAIL.lower())
    pass_ok  = _hmac.compare_digest(body.password, _ADMIN_PASSWORD)
    if not email_ok or not pass_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = _make_simple_token(_ADMIN_EMAIL)
    log.info("simple_login_success", email=_ADMIN_EMAIL)
    return _SimpleTokenResponse(access_token=token)


@app.get("/auth/me")
async def simple_me(current_user: User = Depends(get_current_user)):
    """Verify Bearer token and return user info. Used by frontend on page load."""
    return {"email": current_user.email, "plan": current_user.plan}


@app.post("/auth/json-login", response_model=_SimpleTokenResponse)
async def json_login(body: _SimpleLoginRequest, db=Depends(get_db)):
    """
    JSON-based login: accepts {email, password}.
    Checks admin credentials first, then falls back to DB users (registered via /auth/register).
    Issues a standard 'access' JWT compatible with get_current_user.
    """
    from services.auth import verify_password, create_access_token, hash_password
    # 1. Try hardcoded admin account — auto-create DB record on first login
    if _hmac.compare_digest(body.email.lower().strip(), _ADMIN_EMAIL.lower()) and \
       _hmac.compare_digest(body.password, _ADMIN_PASSWORD):
        admin_user = db.query(User).filter_by(email=_ADMIN_EMAIL.lower()).first()
        if not admin_user:
            admin_user = User(
                email=_ADMIN_EMAIL.lower(),
                hashed_password=hash_password(_ADMIN_PASSWORD),
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        token = create_access_token(str(admin_user.id))
        log.info("json_login_admin", email=_ADMIN_EMAIL, user_id=str(admin_user.id))
        return _SimpleTokenResponse(access_token=token)
    # 2. Try DB user
    user = db.query(User).filter_by(email=body.email.lower().strip(), is_active=True).first()
    _dummy = "$2b$12$KIXbKkDqzFbMnJqX5QvXeOmNKLhVqFwMPqRsT7uVwXyZaAbBcCdDe"
    candidate_hash = user.hashed_password if user else _dummy
    if not verify_password(body.password, candidate_hash) or not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token(str(user.id))
    log.info("json_login_user", user_id=str(user.id))
    return _SimpleTokenResponse(access_token=token)


@app.websocket("/ws/render-progress/{task_id}")
async def websocket_render_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time render progress updates.
    Frontend connects here to receive progress updates during video rendering.
    """
    await manager.connect(task_id, websocket)
    try:
        # Keep connection alive and wait for messages
        while True:
            # Receive messages (if any) to detect disconnection
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(task_id)
        print(f"Client disconnected from task: {task_id}")


@app.get("/")
async def root():
    return {
        "message": "Video Processing API",
        "ffmpeg_available": check_ffmpeg(),
    }


class YouTubeDownloadRequest(BaseModel):
    url: str


@app.get("/test-no-auth")
async def test_no_auth():
    """Test endpoint with absolutely no auth - for debugging"""
    return {"status": "ok", "message": "Backend is working without auth!"}


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith('.mp4'):
        raise HTTPException(status_code=400, detail="Only MP4 files are allowed")

    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    file_path = UPLOAD_DIR / f"{file_id}{file_extension}"

    # Async chunked write — does not block the event loop during upload
    async with aiofiles.open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            await buffer.write(chunk)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "size": file_path.stat().st_size,
        "message": "File uploaded successfully"
    }


def _run_yt_dlp_download(url: str, output_path: Path) -> dict:
    """Run yt-dlp synchronously (for use in thread). Returns info dict.

    SECURITY: `url` MUST already be the canonical form returned by
    validate_import_url() (https://www.youtube.com/watch?v={id}).
    Post-resolve IP check (DNS rebinding guard) runs here, immediately
    before the download, as a second layer after validate_import_url().
    YDL_SSRF_OPTS enforces socket_timeout and no certificate bypass.
    """
    # Post-canonicalization DNS rebinding guard: re-resolve www.youtube.com
    # right before the download to catch IP changes since the initial check.
    validate_resolved_ip("www.youtube.com")

    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'outtmpl': str(output_path),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        # Use iOS/Android client — no JS n-challenge required, formats available directly
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web'],
            },
        },
        # Parallel fragment download (speeds up segmented streams 3-4x)
        'concurrent_fragment_downloads': 4,
        # Prefer native downloaders to reduce TLS/FFmpeg pull failures
        'hls_prefer_native': True,
        'downloader': {'http': 'native', 'https': 'native'},
        # User-Agent: mimic real browser
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        # Enable Node.js and Deno for JS execution (required by YouTube extractor)
        'js_runtimes': {'node': {}, 'deno': {}},
    }
    # Merge SSRF hardening opts (socket_timeout, nocheckcertificate=False, etc.)
    ydl_opts.update(YDL_SSRF_OPTS)
    # Merge http_headers separately so browser UA is preserved
    ydl_opts['http_headers'] = {**YDL_SSRF_OPTS.get('http_headers', {}), **ydl_opts['http_headers']}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info


def _is_interrupted_download_error(e: Exception) -> bool:
    """True if error looks like connection/server interrupted (user can retry)."""
    msg = (str(e) or "").lower()
    return any(
        x in msg
        for x in (
            "end of file",
            "io error",
            "tls",
            "connection",
            "interrupted",
            "eof",
            "ffmpeg exited",  # TLS/EOF often surfaces as ffmpeg exit in yt-dlp
        )
    )


def _is_youtube_bot_detection_error(e: Exception) -> bool:
    """True if error is YouTube anti-bot protection (needs cookies or different approach)."""
    msg = (str(e) or "").lower()
    return any(
        x in msg
        for x in (
            "page needs to be reloaded",
            "sign in to confirm",
            "this video is unavailable",
            "members-only content",
            "private video",
        )
    )


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from yt-dlp/ffmpeg output."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


@app.post("/download-youtube")
@limiter.limit(LIMITS["youtube"])
async def download_youtube(
    request: Request,
    body: YouTubeDownloadRequest,
    current_user: User = Depends(get_current_user),
):
    # SSRF guard: validate + canonicalize URL before any server-side fetch.
    # canonical_url is always https://www.youtube.com/watch?v={id}
    canonical_url = validate_import_url(body.url)

    file_id = str(uuid.uuid4())
    output_path = UPLOAD_DIR / f"{file_id}.mp4"
    try:
        # Run blocking yt-dlp in thread to avoid blocking the event loop.
        # Pass canonical_url (not body.url) to prevent open-redirect exploitation.
        info = await asyncio.to_thread(_run_yt_dlp_download, canonical_url, output_path)

        if info is None:
            raise HTTPException(status_code=500, detail="YouTube extraction returned no data")

        video_title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)

        if not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Download failed - file not created. Check that FFmpeg is in PATH (needed for merging video+audio)."
            )

        log.info("youtube_download_complete", file_id=file_id, duration=duration)
        return {
            "file_id": file_id,
            "filename": f"{video_title}.mp4",
            "title": video_title,
            "duration": duration,
            "size": output_path.stat().st_size,
            "message": "YouTube video downloaded successfully"
        }

    except yt_dlp.utils.DownloadError as e:
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass
        
        # Provide specific guidance based on error type
        if _is_youtube_bot_detection_error(e):
            detail = (
                "YouTube detected automated access. This can happen with:\n"
                "• Age-restricted videos\n"
                "• Private/members-only content\n"
                "• Regional restrictions\n"
                "• Temporary YouTube anti-bot measures\n\n"
                "Try:\n"
                "1. Use a different video URL\n"
                "2. Wait a few minutes and retry\n"
                "3. Check if the video is publicly accessible\n\n"
                f"Original error: {_strip_ansi(str(e))}"
            )
        elif _is_interrupted_download_error(e):
            detail = "Download was interrupted (connection lost or server restarted). Please try again."
        else:
            detail = f"YouTube download error: {_strip_ansi(str(e))}"
        
        raise HTTPException(status_code=400, detail=detail)
    except HTTPException:
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass
        raise
    except Exception as e:
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.post("/process/{file_id}")
async def process_video(
    file_id: str,
    operation: str = "info",
    current_user: User = Depends(get_current_user),
):
    input_file = UPLOAD_DIR / f"{file_id}.mp4"
    
    if not input_file.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not check_ffmpeg():
        raise HTTPException(status_code=500, detail="FFmpeg is not available")
    
    try:
        if operation == "info":
            result = subprocess.run(
                [
                    get_ffprobe_path(),
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(input_file)
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return {"info": result.stdout}
        
        elif operation == "thumbnail":
            output_file = OUTPUT_DIR / f"{file_id}_thumb.jpg"
            subprocess.run(
                [
                    get_ffmpeg_path(),
                    "-i", str(input_file),
                    "-ss", "00:00:01",
                    "-vframes", "1",
                    "-y",
                    str(output_file)
                ],
                capture_output=True,
                check=True
            )
            return {
                "output_file": str(output_file),
                "message": "Thumbnail generated successfully"
            }
        
        elif operation == "compress":
            output_file = OUTPUT_DIR / f"{file_id}_compressed.mp4"
            subprocess.run(
                [
                    get_ffmpeg_path(),
                    "-i", str(input_file),
                    "-vcodec", "libx264",
                    "-crf", "28",
                    "-y",
                    str(output_file)
                ],
                capture_output=True,
                check=True
            )
            return {
                "output_file": str(output_file),
                "message": "Video compressed successfully"
            }
        
        else:
            raise HTTPException(status_code=400, detail="Invalid operation")
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
        )


@app.get("/download/{file_id}")
async def download_file(
    file_id: str,
    file_type: str = "compressed",
    current_user: User = Depends(get_current_user),
):
    if file_type == "thumbnail":
        file_path = OUTPUT_DIR / f"{file_id}_thumb.jpg"
    else:
        file_path = OUTPUT_DIR / f"{file_id}_compressed.mp4"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )


@app.get("/clips/{filename}")
async def download_clip(filename: str):
    """Serve rendered clip files for download"""
    clip_path = CLIPS_DIR / filename
    
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        path=clip_path,
        filename=filename,
        media_type="video/mp4"
    )


@app.get("/thumbnails/{filename}")
async def get_thumbnail(filename: str):
    """Serve thumbnail images for candidates"""
    thumbnail_path = THUMBNAILS_DIR / filename
    
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(
        path=thumbnail_path,
        filename=filename,
        media_type="image/jpeg"
    )


@app.post("/transcribe/{file_id}")
async def transcribe_video(
    file_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Start async transcription (returns immediately with job_id)."""
    input_file = UPLOAD_DIR / f"{file_id}.mp4"

    if not input_file.exists():
        raise HTTPException(status_code=404, detail="File not found")

    with SessionLocal() as db:
        existing = (
            db.query(TranscriptionJob)
            .filter(
                TranscriptionJob.file_id == file_id,
                TranscriptionJob.owner_id == current_user.id,
                TranscriptionJob.status == TranscriptionJobStatus.processing,
            )
            .order_by(TranscriptionJob.created_at.desc())
            .first()
        )
        if existing:
            return {
                "job_id": str(existing.id),
                "status": "processing",
                "message": "Transcription already in progress",
            }

        job = TranscriptionJob(
            file_id=file_id,
            owner_id=current_user.id,
            status=TranscriptionJobStatus.processing,
            progress=0,
            total_chunks=0,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_uuid = str(job.id)

    background_tasks.add_task(_run_transcription_job, job_uuid, file_id, current_user.id)

    return {
        "job_id": job_uuid,
        "status": "processing",
        "message": "Transcription started",
    }


@app.get("/transcribe/{file_id}/status")
def transcribe_job_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Poll async transcription progress for the latest job on this upload."""
    with SessionLocal() as db:
        job = (
            db.query(TranscriptionJob)
            .filter(
                TranscriptionJob.file_id == file_id,
                TranscriptionJob.owner_id == current_user.id,
            )
            .order_by(TranscriptionJob.created_at.desc())
            .first()
        )

    if not job:
        raise HTTPException(status_code=404, detail="No transcription job for this file")

    if job.status == TranscriptionJobStatus.processing:
        return {
            "status": "processing",
            "progress": int(job.progress or 0),
            "total_chunks": int(job.total_chunks or 0),
        }
    if job.status == TranscriptionJobStatus.done:
        payload: Dict[str, object] = {
            "status": "done",
            "progress": job.total_chunks or job.progress or 0,
            "total_chunks": job.total_chunks or 0,
        }
        if job.transcript_id:
            payload["transcript_id"] = job.transcript_id
        return payload
    if job.status == TranscriptionJobStatus.failed:
        err = job.error_message or "Transcription failed"
        return {"status": "failed", "error": err}
    return {"status": "unknown"}


@app.get("/transcription/{file_id}")
def get_transcription(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Return full transcription and segments for editing."""
    data = transcription_store.get(file_id)
    if not data:
        data = _load_transcript_from_db(file_id=file_id, owner_id=current_user.id)
    if not data:
        transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
        if not transcription_file.exists():
            raise HTTPException(status_code=404, detail="Transcription not found")
        with transcription_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    transcription_store[file_id] = data
    return {
        "text": data.get("text", ""),
        "segments": data.get("segments", []),
    }


class SegmentEditItem(BaseModel):
    index: int
    text: str


class TranscriptionEditRequest(BaseModel):
    segments: List[SegmentEditItem]


@app.patch("/transcription/{file_id}")
def patch_transcription(
    file_id: str,
    request: TranscriptionEditRequest,
    current_user: User = Depends(get_current_user),
):
    """Update segment texts (and words) from user edits. Persists to file and store."""
    data = transcription_store.get(file_id)
    if not data:
        data = _load_transcript_from_db(file_id=file_id, owner_id=current_user.id)
    if not data:
        transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
        if not transcription_file.exists():
            raise HTTPException(status_code=404, detail="Transcription not found")
        with transcription_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    segments = data.get("segments") or []
    if not segments:
        raise HTTPException(status_code=400, detail="No segments to edit")
    for item in request.segments:
        if item.index < 0 or item.index >= len(segments):
            continue
        _apply_corrected_segment_text(segments[item.index], item.text)
    # Rebuild full text from segments
    data["text"] = " ".join((s.get("text") or "").strip() for s in segments).strip()
    data["segments"] = segments
    transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
    with transcription_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    transcription_store[file_id] = data
    _save_transcript_to_db(
        file_id=file_id,
        owner_id=current_user.id,
        transcript_data=data,
    )
    return {"text": data["text"], "segments": data["segments"], "message": "Transcription updated"}


@app.post("/analyze/{file_id}")
async def analyze_video(
    file_id: str,
    provider: str = "claude",
    max_clips: int = Query(5, ge=1, le=15),
    current_user: User = Depends(get_current_user),
):
    """HUMAN-IN-THE-LOOP: Analyze video and store candidates (no rendering yet)"""
    print(f"[DEBUG] /analyze/{file_id} called: provider={provider}, max_clips={max_clips}")
    input_file = UPLOAD_DIR / f"{file_id}.mp4"
    transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
    
    if not input_file.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    if not transcription_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Transcription not found. Please transcribe the video first."
        )
    
    try:
        with transcription_file.open("r", encoding="utf-8") as f:
            transcription_data = json.load(f)
        
        transcription_text = transcription_data["text"]
        video_duration = get_video_duration(input_file)
        
        analyzer = create_analyzer(provider=provider)
        viral_clips = analyzer.analyze_transcription(transcription_text, video_duration, max_clips=max_clips)
        
        # Generate thumbnails for candidates
        print(f"-> Generating thumbnails for {len(viral_clips)} candidates...")
        viral_clips_with_thumbnails = generate_thumbnails_for_candidates(
            input_video=input_file,
            candidates=viral_clips,
            output_dir=THUMBNAILS_DIR,
            file_id=file_id
        )
        
        # Store candidates in memory for human review
        clip_candidates_store[file_id] = viral_clips_with_thumbnails
        
        # Also save to file for persistence
        analysis_file = OUTPUT_DIR / f"{file_id}_analysis.json"
        with analysis_file.open("w", encoding="utf-8") as f:
            json.dump(viral_clips_with_thumbnails, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Analysis complete: {len(viral_clips_with_thumbnails)} candidates stored for review")
        
        return {
            "viral_clips": viral_clips_with_thumbnails,
            "video_duration": video_duration,
            "message": f"Analysis completed: {len(viral_clips_with_thumbnails)} candidates ready for review"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis error: {str(e)}"
        )


@app.post("/analyze-video")
async def analyze_video_autonomous(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    AUTONOMOUS AI FACTORY: Discover viral moments using Claude.
    Analyzes transcript and returns high-impact segments with viral scores.
    """
    input_file = UPLOAD_DIR / f"{file_id}.mp4"
    transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
    
    if not input_file.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    if not transcription_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Transcription not found. Please transcribe the video first."
        )
    
    try:
        # Load transcription
        with transcription_file.open("r", encoding="utf-8") as f:
            transcription_data = json.load(f)
        
        # Discover viral moments using Claude
        print(f"🤖 Starting autonomous viral moment discovery for {file_id}...")
        viral_moments = await discover_viral_moments(transcription_data)
        
        if not viral_moments:
            raise HTTPException(
                status_code=500,
                detail="No viral moments discovered. Check ANTHROPIC_API_KEY or transcript quality."
            )
        
        # Convert viral moments to clip candidates format
        viral_clips = []
        for i, moment in enumerate(viral_moments):
            viral_clips.append({
                "start_time": moment["start_time"],
                "end_time": moment["end_time"],
                "title": moment["title"],
                "viral_score": moment["viral_score"],
                "hook": moment["hook"],
                "duration": moment["duration"],
                "clip_index": i
            })
        
        # Generate thumbnails for viral moments
        print(f"-> Generating thumbnails for {len(viral_clips)} viral moments...")
        viral_clips_with_thumbnails = generate_thumbnails_for_candidates(
            input_video=input_file,
            candidates=viral_clips,
            output_dir=THUMBNAILS_DIR,
            file_id=file_id
        )
        
        # Store candidates in memory
        clip_candidates_store[file_id] = viral_clips_with_thumbnails
        
        # Save to file for persistence
        analysis_file = OUTPUT_DIR / f"{file_id}_viral_analysis.json"
        with analysis_file.open("w", encoding="utf-8") as f:
            json.dump(viral_clips_with_thumbnails, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Autonomous analysis complete: {len(viral_clips_with_thumbnails)} viral moments discovered")
        
        return {
            "viral_moments": viral_clips_with_thumbnails,
            "count": len(viral_clips_with_thumbnails),
            "message": f"AI discovered {len(viral_clips_with_thumbnails)} viral moments"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Viral moment discovery failed: {str(e)}"
        )


@app.get("/clips/{file_id}/candidates")
async def get_clip_candidates(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """HUMAN-IN-THE-LOOP: Get clip candidates for review (no rendering)"""
    # Try in-memory store first
    if file_id in clip_candidates_store:
        candidates = clip_candidates_store[file_id]
        return {
            "file_id": file_id,
            "candidates": candidates,
            "count": len(candidates),
            "message": "Candidates loaded from memory"
        }
    
    # Fallback to file if not in memory
    analysis_file = OUTPUT_DIR / f"{file_id}_analysis.json"
    if not analysis_file.exists():
        raise HTTPException(
            status_code=404,
            detail="No analysis found. Please analyze the video first."
        )
    
    try:
        with analysis_file.open("r", encoding="utf-8") as f:
            candidates = json.load(f)
        
        # Store in memory for future requests
        clip_candidates_store[file_id] = candidates
        
        return {
            "file_id": file_id,
            "candidates": candidates,
            "count": len(candidates),
            "message": "Candidates loaded from file"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading candidates: {str(e)}"
        )


class ExtractClipsRequest(BaseModel):
    """Request body for extract-clips: which clips to render and options"""
    clip_indices: Optional[List[int]] = None  # Which clips to render (0-based), None = all
    custom_clips: Optional[List[Dict]] = None  # Custom timecodes from frontend editing
    enable_reframe: bool = True
    enable_subtitles: bool = True
    platform: str = "tiktok"  # tiktok, youtube, instagram


class RenderClipRequest(BaseModel):
    """Request body for rendering a single clip with progress tracking"""
    file_id: str
    clip_index: int  # 0-based index
    platform: str = "tiktok"  # tiktok, youtube, instagram
    manual_crop_x: Optional[int] = None  # Manual override for crop X position
    show_hook: bool = True  # Show AI hook text overlay (can be disabled for clean look)
    subtitle_style: str = "hormozi"  # hormozi | beast | minimal
    subtitle_language: str = "auto"  # auto | ru | en
    enable_jump_cut: bool = False  # Cut silences >1.5s
    enable_sfx: bool = True  # Mix in pop/whoosh SFX from assets/sfx/
    use_semantic_chunking: bool = True  # Use semantic chunking for subtitles
    start_time: Optional[float] = None  # User-edited start time override (seconds)
    end_time: Optional[float] = None  # User-edited end time override (seconds)
    render_mode: str = "auto"  # "auto" | "face_crop" | "blur_background"


@app.post("/extract-clips/{file_id}")
async def extract_viral_clips(
    file_id: str,
    request: Optional[ExtractClipsRequest] = None,
    current_user: User = Depends(get_current_user),
):
    """HUMAN-IN-THE-LOOP: Render specific clips selected by user"""
    # Default request if not provided (backward compatibility)
    if request is None:
        request = ExtractClipsRequest()
    
    input_file = UPLOAD_DIR / f"{file_id}.mp4"
    transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
    
    if not input_file.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    try:
        # Get clips to render
        if request.custom_clips:
            # User provided custom timecodes (edited in frontend)
            viral_clips = request.custom_clips
            print(f"-> Rendering {len(viral_clips)} custom clips from frontend")
        elif file_id in clip_candidates_store:
            # Get from in-memory store
            all_candidates = clip_candidates_store[file_id]
            if request.clip_indices:
                # Render specific clips by index
                viral_clips = [all_candidates[i] for i in request.clip_indices if i < len(all_candidates)]
                print(f"-> Rendering {len(viral_clips)} selected clips: {request.clip_indices}")
            else:
                # Render all candidates
                viral_clips = all_candidates
                print(f"-> Rendering all {len(viral_clips)} candidates")
        else:
            # Fallback to file
            analysis_file = OUTPUT_DIR / f"{file_id}_analysis.json"
            if not analysis_file.exists():
                raise HTTPException(
                    status_code=404,
                    detail="No candidates found. Please analyze the video first."
                )
            with analysis_file.open("r", encoding="utf-8") as f:
                all_candidates = json.load(f)
            
            if request.clip_indices:
                viral_clips = [all_candidates[i] for i in request.clip_indices if i < len(all_candidates)]
            else:
                viral_clips = all_candidates
        
        transcription_data = None
        if request.enable_subtitles and transcription_file.exists():
            with transcription_file.open("r", encoding="utf-8") as f:
                transcription_data = json.load(f)
        
        reframer = create_reframer() if request.enable_reframe else None
        subtitle_gen = create_subtitle_generator() if request.enable_subtitles else None
        
        print(f"\n{'='*60}")
        print(f"RENDERING CLIPS FOR {file_id.upper()}")
        print(f"{'='*60}")
        print(f"Platform: {request.platform}")
        print(f"Reframe: {request.enable_reframe}")
        print(f"Subtitles: {request.enable_subtitles}")
        print(f"Clips to render: {len(viral_clips)}")
        print(f"{'='*60}\n")
        
        extracted_clips = []
        
        for idx, clip in enumerate(viral_clips):
            clip_filename = f"{file_id}_clip_{idx + 1}_VIRAL_GOLD.mp4"
            clip_path = CLIPS_DIR / clip_filename
            
            crop_filter = None
            crop_preview = clip.get("crop_preview")

            # Detect no-face mode: use blur background instead of smart crop
            _preview_mode = (crop_preview or {}).get("mode", "center_crop")
            _has_face = _preview_mode not in ("center_crop", None) and bool((crop_preview or {}).get("faces"))
            _force_blur = not _has_face and _preview_mode != "split_screen"

            if _force_blur:
                print(f"  -> No face detected (mode={_preview_mode}) — using blur background mode")
            elif reframer:
                try:
                    # Pass crop_preview for split_screen mode support
                    crop_filter = reframer.get_crop_filter(
                        input_file,
                        clip["start_time"],
                        clip["end_time"],
                        crop_preview=crop_preview
                    )
                except Exception as e:
                    print(f"Reframing failed for clip {idx + 1}: {e}")
            
            # Get video FPS for sync
            video_info = None
            if reframer:
                try:
                    video_info = reframer.get_video_info(input_file)
                except Exception as e:
                    print(f"[WARN] Could not get video info: {e}")
            
            subtitle_path = None
            sentence_starts = []
            if subtitle_gen and transcription_data:
                try:
                    # Unique subtitle path with timestamp to avoid overwriting
                    import time
                    timestamp = int(time.time() * 1000)
                    clip_id = f"{file_id}_clip_{idx + 1}"
                    subtitle_path = OUTPUT_DIR / f"subs_{clip_id}_{timestamp}.ass"
                    
                    # Check if split_screen mode for subtitle positioning
                    is_split_screen = crop_preview and crop_preview.get("mode") == "split_screen"
                    
                    sentence_starts = subtitle_gen.generate_ass_from_transcription(
                        transcription_data,
                        subtitle_path,
                        hook_text=clip.get("hook", ""),
                        emojis=clip.get("emojis", []),
                        clip_start_time=clip["start_time"],
                        clip_end_time=clip["end_time"],
                        clip_duration=clip["end_time"] - clip["start_time"],
                        platform=request.platform,  # Pass platform for subtitle positioning
                        is_split_screen=is_split_screen  # Pass split_screen mode
                    )
                    fps_info = f"FPS: {video_info['fps']:.2f}" if video_info else "FPS: unknown"
                    print(f"[OK] Processing Clip {clip_id} with {fps_info} and Subtitles: {subtitle_path.name}")
                    print(f"  -> Sentence starts for zoom: {sentence_starts[:5]}...") if len(sentence_starts) > 5 else print(f"  -> Sentence starts: {sentence_starts}")
                except Exception as e:
                    print(f"[FAIL] Subtitle generation failed for clip {idx + 1}: {e}")
            
            zoom_filter = None
            clip_duration = clip["end_time"] - clip["start_time"]
            print(f"  -> Continuous slow zoom will be applied (1.0->1.1 over {clip_duration:.1f}s)")
            
            try:
                print(f"\n-> Processing Clip {idx + 1}/{len(viral_clips)}: {clip['title'][:40]}...")
                print(f"  -> Time range: {clip['start_time']:.1f}s - {clip['end_time']:.1f}s")
                print(f"  -> Crop: {'YES' if crop_filter else 'NO'}")
                print(f"  -> Subtitles: {'YES' if subtitle_path and subtitle_path.exists() else 'NO'}")
                
                # Determine if split_screen mode (already set during subtitle generation)
                is_split_screen_mode = crop_preview and crop_preview.get("mode") == "split_screen" if crop_preview else False
                if is_split_screen_mode:
                    print(f"  -> Mode: [!] SPLIT SCREEN")
                
                await cut_video_segment_enhanced(
                    input_file,
                    clip_path,
                    clip["start_time"],
                    clip["end_time"],
                    subtitle_path=subtitle_path,
                    crop_filter=crop_filter,
                    zoom_filter=zoom_filter,
                    video_fps=video_info['fps'] if video_info else None,
                    is_split_screen=is_split_screen_mode,
                    letterbox_with_blur=_force_blur,
                )
                print(f"[OK] Clip {idx + 1} rendered successfully: {clip_filename}")
                
                # Keep subtitle files for debugging
                if subtitle_path and subtitle_path.exists():
                    file_size = subtitle_path.stat().st_size
                    print(f"  -> Subtitle file kept: {subtitle_path.name} ({file_size} bytes)")
            except subprocess.CalledProcessError as e:
                print(f"❌ FFmpeg failed for clip {idx + 1}")
                print(f"  -> Error: {str(e)[:200]}")
                raise
            except Exception as e:
                print(f"❌ Clip rendering failed: {e}")
                raise
            
            extracted_clips.append({
                "clip_id": idx + 1,
                "filename": clip_filename,
                "title": clip["title"],
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "virality_score": clip["virality_score"],
                "reason": clip["reason"],
                "hook": clip.get("hook", ""),
                "enhanced": {
                    "reframed": crop_filter is not None,
                    "subtitles": subtitle_path is not None and subtitle_path.exists()
                }
            })
        
        if reframer:
            reframer.close()
        
        return {
            "clips": extracted_clips,
            "message": f"Successfully extracted {len(extracted_clips)} viral clips with enhancements"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Clip extraction error: {str(e)}"
        )


@app.get("/download-clip/{file_id}/{clip_id}")
async def download_clip(
    file_id: str,
    clip_id: int,
):
    # Try to find clip with any pattern (legacy, suffixed, or hashed)
    # First try exact match (legacy)
    clip_filename = f"{file_id}_clip_{clip_id}_VIRAL_GOLD.mp4"
    clip_path = CLIPS_DIR / clip_filename
    
    if not clip_path.exists():
        # Try with legacy suffixes
        for suffix in ["_with_hook", "_no_hook"]:
            clip_filename_suffixed = f"{file_id}_clip_{clip_id}{suffix}_VIRAL_GOLD.mp4"
            clip_path_suffixed = CLIPS_DIR / clip_filename_suffixed
            if clip_path_suffixed.exists():
                clip_path = clip_path_suffixed
                clip_filename = clip_filename_suffixed
                break
    
    if not clip_path.exists():
        # Try to find any file matching pattern: {file_id}_clip_{clip_id}_h*_s*_VIRAL_GOLD.mp4
        import glob
        pattern = str(CLIPS_DIR / f"{file_id}_clip_{clip_id}_h*_s*_VIRAL_GOLD.mp4")
        matching_files = glob.glob(pattern)
        if matching_files:
            # Use most recent file if multiple exist
            matching_files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
            clip_path = Path(matching_files[0])
            clip_filename = clip_path.name
    
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        path=clip_path,
        filename=clip_filename,
        media_type="video/mp4"
    )


@app.get("/clip-meta/{file_id}/{clip_id}")
async def get_clip_meta(
    file_id: str,
    clip_id: int,
    current_user: User = Depends(get_current_user),
):
    """Return social metadata JSON generated after render."""
    meta_path = OUTPUT_DIR / f"{file_id}_clip_{clip_id}_meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Metadata not found")
    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@app.post("/render-clip")
async def render_clip_with_progress(
    request: RenderClipRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Render a single clip with WebSocket progress tracking.
    Frontend should connect to /ws/render-progress/{task_id} to receive updates.
    
    Returns task_id immediately, rendering happens in background.
    """
    try:
        print(f"🎬 Render request received: file_id={request.file_id}, clip_index={request.clip_index}")
        task_id = str(uuid.uuid4())
        job = {
            "task_id": task_id,
            "file_id": request.file_id,
            "clip_index": request.clip_index,
            "platform": request.platform,
            "manual_crop_x": request.manual_crop_x,
            "show_hook": request.show_hook,
            "subtitle_style": request.subtitle_style,
            "subtitle_language": request.subtitle_language,
            "enable_jump_cut": request.enable_jump_cut,
            "enable_sfx": request.enable_sfx,
            "use_semantic_chunking": request.use_semantic_chunking,
            "start_time_override": request.start_time,
            "end_time_override": request.end_time,
            "render_mode": request.render_mode,
        }
        print(f"  -> Queueing job with task_id={task_id}")
        await render_queue.put(job)
        queue_position = render_queue.qsize()  # 1 = currently processing, 2+ = waiting
        print(f"  -> Job queued successfully, position={queue_position}")
        return {
            "task_id": task_id,
            "message": "Rendering queued. Connect to WebSocket for progress updates." + (
                f" Position in queue: {queue_position}." if queue_position > 1 else ""
            ),
            "websocket_url": f"/ws/render-progress/{task_id}",
            "queue_position": queue_position,
        }
    except Exception as e:
        import traceback
        print(f"❌ ERROR in render-clip endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Render request failed: {str(e)}")


@app.delete("/cleanup/{file_id}")
async def cleanup_files(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    files_deleted = []
    
    # Cleanup main directories
    for directory in [UPLOAD_DIR, OUTPUT_DIR, CLIPS_DIR, THUMBNAILS_DIR]:
        for file_path in directory.glob(f"{file_id}*"):
            try:
                file_path.unlink()
                files_deleted.append(str(file_path))
            except Exception as e:
                print(f"[WARN] Failed to delete {file_path}: {e}")
    
    # Cleanup temp directory
    temp_dir = CLIPS_DIR / "temp"
    if temp_dir.exists():
        for file_path in temp_dir.glob(f"*{file_id}*"):
            try:
                file_path.unlink()
                files_deleted.append(str(file_path))
            except Exception as e:
                print(f"[WARN] Failed to delete temp file {file_path}: {e}")
    
    return {
        "message": "Cleanup completed",
        "files_deleted": files_deleted
    }
