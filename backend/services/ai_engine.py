"""
Legacy helpers for aligning edited subtitle text with word timings.
OpenAI transcript correction paths are intentionally disabled — Whisper-only ASR uses apply_word_corrections().
"""

import re
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()


# ── Levenshtein helpers (no external deps) ────────────────────

def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + (0 if ca == cb else 1),
            ))
        prev = curr
    return prev[-1]


def _similarity(a: str, b: str) -> float:
    """Normalised similarity [0.0, 1.0] based on Levenshtein distance."""
    max_len = max(len(a), len(b)) if (a or b) else 0
    if max_len == 0:
        return 1.0
    return 1.0 - _levenshtein(a, b) / max_len


_PUNCT_RE = re.compile(r"[^\w]", re.UNICODE)
_FUZZY_THRESHOLD = 0.72
_FUZZY_THRESHOLD_SHORT = 0.55  # Lower threshold for short words (<=8 chars) — catches отдежда->одежда
_MATCH_RATE_MIN  = 0.85  # Revert if correction diverges from too many original words


def _norm_word(s: str) -> str:
    return _PUNCT_RE.sub("", s).lower()

def _apply_corrected_segment_text(segment: Dict[str, Any], corrected_text: str) -> None:
    """
    Update segment['text'] and align word-level entries to the corrected text.

    Alignment strategy (R3 — fuzzy Levenshtein + 80% match-rate fallback):
      1. Split corrected_text into tokens.
      2. Walk original word list; for each original word:
         a. Exact match (normalised, punctuation-stripped).
         b. Fuzzy match via Levenshtein similarity >= 0.72 (handles GPT
            spelling corrections, e.g. transliterated -> English).
         c. No match -> word was removed by GPT; mark w['_filler']=True.
      3. Compute match_rate = matched / total_original_words.
         If match_rate < 80%, the corrected text diverged too far — revert
         all staged changes and keep the original ASR text + timestamps.

    Every word keeps its original start/end timestamps; filler words are
    simply invisible in the rendered subtitles (no drift).
    """
    if not corrected_text or not corrected_text.strip():
        return

    words = segment.get("words") or []

    corrected_tokens = corrected_text.split()
    if not corrected_tokens:
        for w in words:
            w["_filler"] = True
        segment["text"] = corrected_text
        return

    if not words:
        segment["text"] = corrected_text
        return

    # Phase 1: greedy alignment with fuzzy fallback
    matched_count = 0
    ci = 0
    pending: List[Dict] = []

    for w in words:
        orig_norm = _norm_word(w.get("word", ""))
        if ci >= len(corrected_tokens):
            pending.append({"w": w, "new_word": None, "filler": True})
            continue

        corr_norm = _norm_word(corrected_tokens[ci])

        # a. Exact / prefix match
        if orig_norm == corr_norm or (orig_norm and corr_norm and corr_norm.startswith(orig_norm)):
            pending.append({"w": w, "new_word": corrected_tokens[ci], "filler": False})
            matched_count += 1
            ci += 1
            continue

        # b. Fuzzy match (lower threshold for short words to catch ASR typos)
        threshold = _FUZZY_THRESHOLD_SHORT if len(orig_norm) <= 8 else _FUZZY_THRESHOLD
        if orig_norm and corr_norm and _similarity(orig_norm, corr_norm) >= threshold:
            pending.append({"w": w, "new_word": corrected_tokens[ci], "filler": False})
            matched_count += 1
            ci += 1
            continue

        # c. Removed by GPT
        pending.append({"w": w, "new_word": None, "filler": True})

    # Phase 2: 80% match-rate guard — revert if corrected text diverged too far
    match_rate = matched_count / len(words) if words else 1.0
    if match_rate < _MATCH_RATE_MIN:
        return

    # Phase 3: commit
    segment["text"] = corrected_text
    for entry in pending:
        w = entry["w"]
        if entry["filler"]:
            w["_filler"] = True
        else:
            w["word"] = entry["new_word"]
            w.pop("_filler", None)


async def fix_transcript_with_openai(raw_text: str) -> str:
    """
    Deprecated no-op kept for backwards compatibility.
    Whisper ASR correction is intentionally not delegated to GPT.
    """
    return raw_text or ""


async def fix_segments_with_openai(segments: List[Dict[str, Any]]) -> None:
    """Deprecated no-op — segments unchanged."""
    _ = segments
