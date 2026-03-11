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


def _send_document(path: Path, caption: str) -> bool:
    """Send a file (video/photo) to the chat."""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        import httpx
        with open(path, "rb") as f:
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    _api_url("sendDocument"),
                    data={"chat_id": CHAT_ID, "caption": caption[:1024], "parse_mode": "HTML"},
                    files={"document": (path.name, f, "video/mp4")},
                )
                return resp.status_code == 200
    except Exception as e:
        log.warning(f"[telegram] sendDocument failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# Public notification functions
# ─────────────────────────────────────────────────────────────

def notify_clip_ready(
    source_title: str,
    clip_title: str,
    viral_score: float,
    start_time: float,
    end_time: float,
    hashtags: Optional[List[str]] = None,
    clip_path: Optional[Path] = None,
    source_url: str = "",
) -> bool:
    """
    Notify when a high-score clip is rendered.
    Sends text message; optionally attaches video file if small enough (<50MB).
    """
    duration = int(end_time - start_time)
    score_bar = "🔥" * min(int(viral_score), 10)
    tags_str = " ".join(f"#{t.lstrip('#')}" for t in (hashtags or [])[:5])

    text = (
        f"<b>Хозяин, нашёл крутой момент!</b>\n\n"
        f"<b>Источник:</b> {source_title[:80]}\n"
        f"<b>Клип:</b> {clip_title[:80]}\n"
        f"<b>Оценка:</b> {viral_score:.1f}/10 {score_bar}\n"
        f"<b>Длина:</b> {duration}с ({int(start_time)}–{int(end_time)}с)\n"
    )
    if tags_str:
        text += f"<b>Теги:</b> {tags_str}\n"
    if source_url:
        text += f"\n<a href='{source_url}'>Источник</a>"

    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    ok = _send(payload)

    # Attach video if small enough
    if ok and clip_path and clip_path.exists():
        size_mb = clip_path.stat().st_size / 1024 / 1024
        if size_mb < 50:
            _send_document(clip_path, caption=f"{clip_title} | {viral_score:.1f}/10")

    return ok


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
