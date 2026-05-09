"""
Redis-backed replacements for clip_candidates_store and transcription_store.

Both stores use JSON serialization with a 7-day TTL so data survives
backend restarts but doesn't accumulate indefinitely on disk.

Falls back to an in-memory dict when Redis is unavailable (dev/test).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_TTL = 7 * 24 * 3600  # 7 days

_PREFIX_CANDIDATES = "cg:candidates:"
_PREFIX_TRANSCRIPTION = "cg:transcription:"

try:
    import redis as _redis_lib

    _client = _redis_lib.Redis.from_url(_REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    _client.ping()
    _USE_REDIS = True
except Exception as _e:
    print(f"[redis_store] Redis unavailable ({_e}), falling back to in-memory dict")
    _USE_REDIS = False
    _client = None  # type: ignore


class _DictFallback(dict):
    """Behaves like a plain dict but mirrors the get/set/delete interface."""


def _rget(key: str) -> Optional[Any]:
    try:
        raw = _client.get(key)  # type: ignore[union-attr]
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _rset(key: str, value: Any) -> None:
    try:
        _client.setex(key, _TTL, json.dumps(value))  # type: ignore[union-attr]
    except Exception:
        pass


def _rdel(key: str) -> None:
    try:
        _client.delete(key)  # type: ignore[union-attr]
    except Exception:
        pass


class RedisBackedStore:
    """Thin dict-like wrapper around Redis (or in-memory fallback)."""

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._fallback: Dict[str, Any] = {}

    def _key(self, file_id: str) -> str:
        return self._prefix + file_id

    def get(self, file_id: str, default: Any = None) -> Any:
        if _USE_REDIS:
            v = _rget(self._key(file_id))
            return v if v is not None else default
        return self._fallback.get(file_id, default)

    def __getitem__(self, file_id: str) -> Any:
        v = self.get(file_id)
        if v is None:
            raise KeyError(file_id)
        return v

    def __setitem__(self, file_id: str, value: Any) -> None:
        if _USE_REDIS:
            _rset(self._key(file_id), value)
        else:
            self._fallback[file_id] = value

    def __delitem__(self, file_id: str) -> None:
        if _USE_REDIS:
            _rdel(self._key(file_id))
        else:
            self._fallback.pop(file_id, None)

    def __contains__(self, file_id: object) -> bool:
        if _USE_REDIS:
            try:
                return bool(_client.exists(self._key(str(file_id))))  # type: ignore[union-attr]
            except Exception:
                return False
        return file_id in self._fallback

    def __repr__(self) -> str:
        backend = "redis" if _USE_REDIS else "in-memory"
        return f"RedisBackedStore(prefix={self._prefix!r}, backend={backend})"


clip_candidates_store: RedisBackedStore = RedisBackedStore(_PREFIX_CANDIDATES)
transcription_store: RedisBackedStore = RedisBackedStore(_PREFIX_TRANSCRIPTION)
