"""
Small helpers for structured pipeline timing logs.

All events use the same event name (`pipeline_timing`) so production logs can be
filtered by stage, file_id, clip_id, or command.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Iterable, Optional

from services.observability import get_logger

log = get_logger(__name__)


def timer_start() -> float:
    return time.perf_counter()


def elapsed_seconds(started_at: float) -> float:
    return round(time.perf_counter() - started_at, 3)


def command_to_string(command: Iterable[Any]) -> str:
    return subprocess.list2cmdline([str(part) for part in command])


def resolution_string(width: Optional[int], height: Optional[int]) -> Optional[str]:
    if width and height:
        return f"{width}x{height}"
    return None


def file_size_mb(path: Path) -> Optional[float]:
    try:
        if path.exists():
            return round(path.stat().st_size / 1024 / 1024, 2)
    except OSError:
        return None
    return None


def log_stage(stage: str, elapsed: float, **fields: Any) -> None:
    clean_fields = {
        key: value
        for key, value in fields.items()
        if value is not None
    }
    log.info(
        "pipeline_timing",
        stage=stage,
        elapsed_seconds=round(float(elapsed), 3),
        **clean_fields,
    )
