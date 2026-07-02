"""
Telegram Reporter — Step 8 of the Autonomous Factory.

Sends notifications when:
  - A high-score clip is ready (with title, score, hashtags)
  - A scout cycle completes (summary)
  - An error occurs in the pipeline

Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env
"""

import logging
import os
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


def _resolution_label(width: Optional[int], height: Optional[int]) -> str:
    if not width or not height:
        return "неизвестно"
    if height >= 2160:
        return f"4K ({width}×{height})"
    if height >= 1440:
        return f"1440p ({width}×{height})"
    if height >= 1080:
        return f"1080p ({width}×{height})"
    return f"{height}p ({width}×{height})"


def _send(payload: dict) -> bool:
    """Send a Telegram API request synchronously."""
    if not BOT_TOKEN or not CHAT_ID:
        log.debug("[telegram] Bot not configured, skipping notification")
        return False
    try:
        import httpx
        with httpx.Client(timeout=15) as client:
            resp = client.post(_api_url("sendMessage"), json=payload)
            if resp.status_code != 200:
                log.warning(f"[telegram] sendMessage failed: {resp.text[:200]}")
                return False
            return True
    except Exception as e:
        log.warning(f"[telegram] Send failed: {e}")
        return False


def _probe_video_dims(path: Path):
    """ffprobe → (width, height, duration_sec) кодированного видео; (None,None,None) при ошибке."""
    try:
        import subprocess, json as _json
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode != 0:
            return None, None, None
        d = _json.loads(r.stdout)
        st = (d.get("streams") or [{}])[0]
        dur = d.get("format", {}).get("duration")
        return st.get("width"), st.get("height"), (int(float(dur)) if dur else None)
    except Exception:
        return None, None, None


def _send_video(path: Path, caption: str) -> bool:
    """Send video file — plays inline in Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        import httpx
        w, h, dur = _probe_video_dims(path)
        data = {
            "chat_id": CHAT_ID,
            "caption": caption[:1024],
            "parse_mode": "HTML",
            "supports_streaming": "true",
        }
        # Явные размеры: без них мобильный Telegram растягивает плеер (на десктопе ок).
        if w and h:
            data["width"] = w
            data["height"] = h
        if dur:
            data["duration"] = dur
        with open(path, "rb") as f:
            with httpx.Client(timeout=120) as client:
                resp = client.post(
                    _api_url("sendVideo"),
                    data=data,
                    files={"video": (path.name, f, "video/mp4")},
                )
                if resp.status_code != 200:
                    log.warning(f"[telegram] sendVideo failed: {resp.text[:200]}")
                    return False
                return True
    except Exception as e:
        log.warning(f"[telegram] sendVideo failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# Public notification functions
# ─────────────────────────────────────────────────────────────

def notify_clip_ready(
    source_title: str,
    clip_title: str,
    viral_score: float,
    hook: str = "",
    clip_path: Optional[Path] = None,
    source_url: str = "",
    # legacy params kept for compat
    start_time: float = 0,
    end_time: float = 0,
    hashtags: Optional[List[str]] = None,
) -> bool:
    """
    Send rendered clip to Telegram as inline video.
    If file > 50MB, falls back to text message with source link.
    """
    score_bar = "🔥" * min(int(viral_score), 10)

    caption = f"<b>Готов клип!</b>\n\n"
    caption += f"<b>{clip_title}</b>\n"
    if hook:
        caption += f"<i>{hook[:200]}</i>\n"
    caption += f"\nВиральность: {int(viral_score)}/10 {score_bar}"
    if source_title:
        caption += f"\nИсточник: {source_title[:60]}"

    # Try to send as inline video
    if clip_path and clip_path.exists():
        size_mb = clip_path.stat().st_size / 1024 / 1024
        if size_mb <= 50:
            return _send_video(clip_path, caption=caption)

    # Fallback: text message
    text = caption
    if source_url:
        text += f"\n\n<a href='{source_url}'>Смотреть источник</a>"
    return _send({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})


def notify_scout_complete(stats: dict) -> bool:
    """Send summary after a scout cycle."""
    text = (
        f"<b>Разведка завершена</b>\n\n"
        f"Запросов: {stats.get('searched', 0)}\n"
        f"Найдено: {stats.get('found', 0)}\n"
        f"Отфильтровано: {stats.get('filtered', 0)}\n"
        f"Дубликатов: {stats.get('duplicates', 0)}\n"
        f"<b>В очередь добавлено: {stats.get('queued', 0)}</b>"
    )
    return _send({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


def notify_factory_cycle(success: int, failed: int, clips: int) -> bool:
    """Send summary after a factory processing cycle."""
    text = (
        f"<b>Цикл фабрики завершён</b>\n\n"
        f"Видео обработано: {success}\n"
        f"Ошибок: {failed}\n"
        f"<b>Клипов создано: {clips}</b>"
    )
    return _send({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


def notify_error(stage: str, error: str, url: str = "") -> bool:
    """Send error notification."""
    text = (
        f"<b>Ошибка на этапе: {stage}</b>\n\n"
        f"<code>{error[:300]}</code>"
    )
    if url:
        text += f"\nURL: {url[:100]}"
    return _send({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


def notify_render_complete(
    title: str,
    clip_path: Optional[Path] = None,
    source_width: Optional[int] = None,
    source_height: Optional[int] = None,
    mode_label: Optional[str] = None,
    lang_label: Optional[str] = None,
) -> bool:
    """Send Telegram notification when a manual render completes."""
    caption = f"<b>✂️ Клип готов!</b>\n\n<b>{title[:80]}</b>"
    src_label = _resolution_label(source_width, source_height)
    caption += f"\n\n📹 Источник: {src_label} → выходное 1080×1920"
    if mode_label:
        caption += f"\n🎬 Режим: {mode_label}"
    if lang_label:
        caption += f"\n🗣 Субтитры: {lang_label}"

    if clip_path and clip_path.exists():
        size_mb = clip_path.stat().st_size / 1024 / 1024
        if size_mb <= 50:
            return _send_video(clip_path, caption=caption)

    return _send({"chat_id": CHAT_ID, "text": caption, "parse_mode": "HTML"})


def notify_daily_report(
    discovered: int,
    processed: int,
    clips: int,
    top_score: float,
    niches: dict,
) -> bool:
    """Send daily summary report."""
    niches_str = "\n".join(f"  • {k}: {v}" for k, v in sorted(niches.items(), key=lambda x: -x[1]))
    text = (
        f"<b>Ежедневный отчёт</b>\n\n"
        f"Найдено видео: {discovered}\n"
        f"Обработано: {processed}\n"
        f"Клипов создано: {clips}\n"
        f"Топ-оценка: {top_score:.1f}/10\n"
    )
    if niches_str:
        text += f"\n<b>По нишам:</b>\n{niches_str}"
    return _send({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
