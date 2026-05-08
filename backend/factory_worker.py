"""
Factory Worker — Headless entry point for the Autonomous Factory.

Starts the scheduler and keeps the event loop running.
Used by docker-compose factory_worker service.

Usage:
    python factory_worker.py
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("factory_worker.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("factory_worker")


async def main():
    log.info("=" * 60)
    log.info("ClipsGold Autonomous Factory Worker starting...")
    log.info(f"AUTONOMOUS_MODE: {os.getenv('AUTONOMOUS_MODE', 'False')}")
    log.info(f"DOWNLOADS_DIR:   {os.getenv('DOWNLOADS_DIR', 'downloads')}")
    log.info("=" * 60)

    # ── Import pipeline functions ─────────────────────────────
    # These are lazy-imported so the worker can start even if
    # some optional dependencies are missing.

    async def transcribe_func(audio_path: str) -> dict:
        """Transcribe audio file using Whisper."""
        try:
            from services.transcription import run_whisper_transcribe_async
            result, _ = await run_whisper_transcribe_async(Path(audio_path), word_timestamps=True)
            return result
        except Exception as e:
            log.error(f"Transcription error: {e}")
            return {}

    async def analyze_func(file_id: str, transcript: dict = None) -> list:
        """Analyze transcript to find viral moments."""
        try:
            from analyzer import analyze_transcript
            return await analyze_transcript(file_id, transcript=transcript)
        except ImportError:
            log.warning("analyzer.py not found, skipping analysis")
            return []
        except Exception as e:
            log.error(f"Analysis error: {e}")
            return []

    async def render_func(file_id: str, clip: dict, source_video_path=None) -> str:
        """Render a clip using 2-pass FFmpeg pipeline."""
        try:
            from render_single_clip import render_clip_headless
            return await render_clip_headless(file_id, clip, source_video_path=source_video_path)
        except ImportError:
            log.warning("render_single_clip.py not found, skipping render")
            return None
        except Exception as e:
            log.error(f"Render error: {e}")
            return None

    # ── Start scheduler ───────────────────────────────────────
    from services.autonomous_scheduler import start_autonomous_scheduler

    start_autonomous_scheduler(
        transcribe_func=transcribe_func,
        analyze_func=analyze_func,
        render_func=render_func,
        enable_scout=True,
        enable_factory_cycle=True,
        enable_daily_report=True,
    )

    log.info("Factory scheduler started. Press Ctrl+C to stop.")

    # ── Keep alive ────────────────────────────────────────────
    stop_event = asyncio.Event()

    def _handle_signal():
        log.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except (NotImplementedError, RuntimeError):
            # Windows doesn't support add_signal_handler for all signals
            pass

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass

    log.info("Factory worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
