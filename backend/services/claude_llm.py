"""
Shared Claude (Anthropic) helpers for analysis, subtitles metadata, etc.
Uses the same model as analyzer.py by default — override with ANTHROPIC_ANALYSIS_MODEL.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

CLAUDE_ANALYSIS_MODEL = os.getenv("ANTHROPIC_ANALYSIS_MODEL", "claude-sonnet-4-5")


def _api_key() -> Optional[str]:
    return os.getenv("ANTHROPIC_API_KEY")


def claude_completion_sync(
    *,
    user: str,
    system: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """Blocking Claude Messages API call."""
    key = _api_key()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    kw: dict = {
        "model": CLAUDE_ANALYSIS_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        kw["system"] = system
    msg = client.messages.create(**kw)
    return (msg.content[0].text or "").strip()


async def claude_completion_async(
    *,
    user: str,
    system: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """Async Claude Messages API call."""
    key = _api_key()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=key)
    kw: dict = {
        "model": CLAUDE_ANALYSIS_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        kw["system"] = system
    msg = await client.messages.create(**kw)
    return (msg.content[0].text or "").strip()
