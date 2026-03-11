"""
AI engine: OpenAI GPT-4o for transcript correction (no Gemini dependency).
"""

import json
import os
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
_MATCH_RATE_MIN  = 0.85  # Revert if GPT changed more than 15% of words


def _norm_word(s: str) -> str:
    return _PUNCT_RE.sub("", s).lower()

SYSTEM_PROMPT_RU = """Ты — профессиональный редактор субтитров. Твоя единственная задача — исправить ТОЛЬКО опечатки и ошибки распознавания брендов/имён.

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- Менять порядок слов
- Удалять слова (любые — включая "ну", "вот", "эм", "типа")
- Упрощать или перефразировать речь спикера
- Объединять или разбивать фразы
- Менять стиль, сленг, интонацию

РАЗРЕШЕНО ТОЛЬКО:
1. Исправлять фонетические искажения брендов и имён:
   - "Сава Спарк" / "Саус Парке" -> "South Park"
   - "понь то вью" -> "point of view"
   - "Волк культура" -> "Woke culture"
   - "Картман" -> "Cartman"
2. Исправлять явные опечатки ASR (одно слово на одно слово).

КРИТИЧНО: На выходе должно быть РОВНО столько же слов, сколько на входе.
Если сомневаешься — оставь слово как есть.
Верни ТОЛЬКО исправленный текст. Никаких объяснений.
"""

SEGMENTS_SYSTEM_PROMPT = """Ты — редактор субтитров. Тебе дадут нумерованный список фраз (сегментов) из ASR.
Верни JSON-массив ровно из того же количества элементов: элемент i — исправленный текст сегмента i.

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- Удалять слова
- Менять порядок слов
- Перефразировать или упрощать речь
- Объединять или разбивать сегменты

РАЗРЕШЕНО ТОЛЬКО:
- Исправлять бренды/имена: "South Park", "point of view", "Woke", "Cartman" и т.п.
- Исправлять явные однословные ASR-ошибки (одно слово -> одно слово)

КРИТИЧНО: количество слов в каждом исправленном сегменте должно быть равно оригиналу.
Пустой сегмент → пустая строка ""
Ничего кроме JSON-массива в ответе"""


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
    Correct ASR transcript using OpenAI GPT-4o (cultural context, anglicisms, brands).
    Returns the corrected text only. If OpenAI is unavailable, returns original.
    """
    if not raw_text or not raw_text.strip():
        return raw_text

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return raw_text

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RU},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        corrected = (response.choices[0].message.content or "").strip()
        return corrected if corrected else raw_text
    except Exception:
        return raw_text


async def fix_segments_with_openai(segments: List[Dict[str, Any]]) -> None:
    """
    Correct each segment's text (and word-level text) so burned-in subtitles show
    the right wording (e.g. "point of view" instead of "поинт оф ю"). Updates segments in place.
    """
    if not segments:
        return
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return
    texts = [s.get("text", "") or "" for s in segments]
    if not any(t.strip() for t in texts):
        return
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        n = len(segments)
        user = f"Исправь ровно {n} сегментов, верни JSON-массив из {n} строк.\nСегменты:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SEGMENTS_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```\w*\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        corrected_list = json.loads(raw)
        if not isinstance(corrected_list, list) or len(corrected_list) != len(segments):
            print(f"    [correction] GPT returned wrong count: {len(corrected_list)} vs {len(segments)}")
            return
        for seg, corrected in zip(segments, corrected_list):
            if isinstance(corrected, str) and corrected.strip():
                orig_words = seg.get('words', [])
                _apply_corrected_segment_text(seg, corrected.strip())
                # Check match rate
                filler_count = sum(1 for w in seg.get('words', []) if w.get('_filler'))
                print(f"    [correction] Applied: {len(orig_words)} words, {filler_count} marked filler")
    except Exception as e:
        print(f"    [correction] ERROR: {e}")
