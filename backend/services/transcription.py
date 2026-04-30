"""
Transcription service: OpenAI Whisper API with auto-chunking for large files.
No local model — cloud-based, fast, language auto-detected.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv

load_dotenv()

# OpenAI Whisper API file size limit. 24MB leaves margin under the 25MB hard limit.
_OPENAI_MAX_BYTES = 24 * 1024 * 1024
# Chunk duration when splitting large audio files
_CHUNK_SECONDS = 600  # 10 minutes → ~5MB at 64kbps mono
# Per-chunk API limits (replaces a single long global HTTP wait)
_CHUNK_API_TIMEOUT_SEC = 300
_CHUNK_MAX_RETRIES = 2  # after first failure → 3 attempts total
_PARALLEL_CHUNKS_DEFAULT = 3

# OpenAI returns full language names; map to ISO 639-1 codes used elsewhere.
_LANG_TO_CODE = {
    "afrikaans": "af", "arabic": "ar", "armenian": "hy", "azerbaijani": "az",
    "belarusian": "be", "bosnian": "bs", "bulgarian": "bg", "catalan": "ca",
    "chinese": "zh", "croatian": "hr", "czech": "cs", "danish": "da",
    "dutch": "nl", "english": "en", "estonian": "et", "finnish": "fi",
    "french": "fr", "galician": "gl", "german": "de", "greek": "el",
    "hebrew": "he", "hindi": "hi", "hungarian": "hu", "icelandic": "is",
    "indonesian": "id", "italian": "it", "japanese": "ja", "kannada": "kn",
    "kazakh": "kk", "korean": "ko", "latvian": "lv", "lithuanian": "lt",
    "macedonian": "mk", "malay": "ms", "marathi": "mr", "maori": "mi",
    "nepali": "ne", "norwegian": "no", "persian": "fa", "polish": "pl",
    "portuguese": "pt", "romanian": "ro", "russian": "ru", "serbian": "sr",
    "slovak": "sk", "slovenian": "sl", "spanish": "es", "swahili": "sw",
    "swedish": "sv", "tagalog": "tl", "tamil": "ta", "thai": "th",
    "turkish": "tr", "ukrainian": "uk", "urdu": "ur", "vietnamese": "vi",
    "welsh": "cy",
}

# Initial prompt to bias Whisper toward domain-specific terms
INITIAL_PROMPT_TERMS = (
    "South Park, Cartman, ClipsGold, YouTube, TikTok, Instagram, viral, clip, "
    "менты, ментов, копы, предприятие, предприятиях, одежда, одежду, шить, шила, "
    "работой, следах, рабский, рабство, милиция, милиции, советский, союза."
)

# Known Whisper ASR errors to fix post-transcription
_WORD_CORRECTIONS = {
    "отдежда": "одежда",
    "отдежду": "одежду",
    "припреатиях": "предприятиях",
    "припреантиях": "предприятиях",
    "припреaтиях": "предприятиях",
    "шица": "шить",
    "рабблотой": "работой",
    "рабблота": "работа",
    "следе": "следах",
    "ошила": "шила",
}


def apply_word_corrections(segments: list) -> None:
    """Apply direct word-level corrections for known Whisper ASR errors."""
    import re
    strip_punct = re.compile(r"[^\w]", re.UNICODE)
    for seg in segments:
        corrected_words = []
        for w in seg.get("words", []):
            raw = w.get("word", "")
            key = strip_punct.sub("", raw).lower()
            if key in _WORD_CORRECTIONS:
                prefix = " " if raw.startswith(" ") else ""
                suffix = raw[-1] if raw and not raw[-1].isalpha() and not raw[-1].isdigit() else ""
                w["word"] = prefix + _WORD_CORRECTIONS[key] + suffix
                corrected_words.append(f"{raw.strip()} -> {w['word'].strip()}")
        if corrected_words:
            print(f"    [word fix] {', '.join(corrected_words)}")
            seg["text"] = "".join(w.get("word", "") for w in seg.get("words", []))


def _api_response_to_dict(resp, time_offset: float = 0.0, seg_id_offset: int = 0) -> dict:
    """
    Convert an OpenAI verbose_json Transcription object to the internal dict format:
      {
        "text": str,
        "language": str,   # ISO 639-1 code
        "segments": [
          {
            "id": int, "start": float, "end": float, "text": str,
            "words": [{"word": str, "start": float, "end": float, "probability": float}]
          }
        ]
      }

    time_offset is added to every timestamp (used when merging audio chunks).
    Words get a leading space to match the openai-whisper convention expected
    by subtitle_generator_v2 and apply_word_corrections.
    """
    lang_raw = (getattr(resp, "language", "") or "").lower()
    lang = _LANG_TO_CODE.get(lang_raw, lang_raw[:2] if len(lang_raw) >= 2 else lang_raw)

    segments = []
    for seg in (getattr(resp, "segments", None) or []):
        words = []
        for w in (getattr(seg, "words", None) or []):
            word_str = str(w.word)
            if word_str and not word_str.startswith(" "):
                word_str = " " + word_str
            words.append({
                "word": word_str,
                "start": round(float(w.start) + time_offset, 3),
                "end":   round(float(w.end)   + time_offset, 3),
                "probability": float(getattr(w, "probability", 1.0)),
            })
        segments.append({
            "id":    int(seg.id) + seg_id_offset,
            "start": round(float(seg.start) + time_offset, 3),
            "end":   round(float(seg.end)   + time_offset, 3),
            "text":  str(seg.text),
            "words": words,
        })

    return {
        "text":     str(resp.text),
        "language": lang,
        "segments": segments,
    }


def _shift_timestamps(result: dict, time_offset: float, seg_id_offset: int) -> dict:
    """Add time_offset to every timestamp in an already-converted result dict."""
    shifted_segs = []
    for seg in result["segments"]:
        shifted_segs.append({
            **seg,
            "id":    seg["id"] + seg_id_offset,
            "start": round(seg["start"] + time_offset, 3),
            "end":   round(seg["end"]   + time_offset, 3),
            "words": [
                {**w, "start": round(w["start"] + time_offset, 3),
                       "end":   round(w["end"]   + time_offset, 3)}
                for w in seg["words"]
            ],
        })
    return {**result, "segments": shifted_segs}


def _ffprobe_duration(path: Path) -> float:
    """Return audio duration in seconds."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _split_audio(audio_path: Path, chunk_sec: int, tmpdir: str) -> list:
    """
    Split audio into chunks of chunk_sec seconds.
    Returns list of (chunk_path, start_offset_seconds).
    Output is 64kbps mono MP3 to keep chunk sizes small.
    """
    duration = _ffprobe_duration(audio_path)
    if duration <= 0:
        return [(audio_path, 0.0)]

    chunks = []
    start = 0.0
    idx = 0
    while start < duration:
        chunk_path = Path(tmpdir) / f"chunk_{idx:03d}.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(audio_path),
             "-ss", str(start), "-t", str(chunk_sec),
             "-ac", "1", "-ar", "16000", "-b:a", "64k",
             str(chunk_path)],
            capture_output=True, check=True,
        )
        if chunk_path.exists() and chunk_path.stat().st_size > 100:
            chunks.append((chunk_path, start))
        start += chunk_sec
        idx += 1

    print(f"[transcription] Split into {len(chunks)} chunks "
          f"({chunk_sec}s each, total={duration:.0f}s)")
    return chunks


def _transcribe_one(client, audio_path: Path, prompt: str) -> dict:
    """Transcribe a single file (must be < 25MB) via OpenAI API."""
    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            prompt=prompt,
        )
    return _api_response_to_dict(resp)


async def _transcribe_one_async(client, audio_path: Path, prompt: str) -> dict:
    """Async OpenAI Whisper call for one chunk."""
    import io

    import aiofiles

    async with aiofiles.open(audio_path, "rb") as f:
        content = await f.read()
    bio = io.BytesIO(content)
    bio.name = audio_path.name
    resp = await client.audio.transcriptions.create(
        model="whisper-1",
        file=bio,
        response_format="verbose_json",
        timestamp_granularities=["word", "segment"],
        prompt=prompt,
    )
    return _api_response_to_dict(resp)


async def _transcribe_chunk_with_retries(client, chunk_path: Path, prompt: str) -> Tuple[Optional[dict], Optional[str]]:
    """Up to 3 attempts per chunk with 300s cap each. Returns (result, skip_reason)."""
    last_msg: Optional[str] = None
    for attempt in range(_CHUNK_MAX_RETRIES + 1):
        try:
            raw = await asyncio.wait_for(
                _transcribe_one_async(client, chunk_path, prompt),
                timeout=_CHUNK_API_TIMEOUT_SEC,
            )
            return raw, None
        except asyncio.TimeoutError:
            last_msg = f"timeout after {_CHUNK_API_TIMEOUT_SEC}s"
        except Exception as e:
            last_msg = str(e)
        if attempt < _CHUNK_MAX_RETRIES:
            await asyncio.sleep(min(8.0, 2 ** attempt))

    print(f"[transcription] Chunk failed after retries: {chunk_path.name} ({last_msg})")
    return None, last_msg or "unknown error"


OnChunkDone = Callable[[int, int], Awaitable[None]]


def _prepare_split_chunks(audio_path: Path, chunk_sec: int) -> Tuple[str, List[Tuple[Path, float]]]:
    tmpdir = tempfile.mkdtemp(prefix="cg_whisper_chunks_")
    try:
        chunks = _split_audio(audio_path, chunk_sec, tmpdir)
        return tmpdir, chunks
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


async def run_whisper_transcribe_async(
    audio_path: Path,
    word_timestamps: bool = True,
    initial_prompt: Optional[str] = None,
    on_chunk_done: Optional[OnChunkDone] = None,
    parallel_chunks: int = _PARALLEL_CHUNKS_DEFAULT,
) -> Tuple[dict, List[Dict]]:
    """
    Transcribe with optional progress callback after each logical chunk completes.
    Large files run up to `parallel_chunks` API calls concurrently.

    Returns (result_dict, skipped_chunks_metadata).
    """
    from openai import AsyncOpenAI

    del word_timestamps  # Whisper API always returns word timestamps here

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    prompt = (initial_prompt or INITIAL_PROMPT_TERMS)[:500]
    path = Path(audio_path)
    file_size = path.stat().st_size

    print(f"[transcription] OpenAI Whisper API | {path.name} | {file_size/1024/1024:.1f}MB")

    client = AsyncOpenAI(api_key=api_key)
    skipped_chunks: List[Dict] = []

    async def _notify(done: int, total: int) -> None:
        if on_chunk_done:
            await on_chunk_done(done, total)

    if file_size <= _OPENAI_MAX_BYTES:
        await _notify(0, 1)
        chunk_result, errmsg = await _transcribe_chunk_with_retries(client, path, prompt)
        await _notify(1, 1)
        if errmsg or chunk_result is None:
            raise RuntimeError(f"Transcription failed: {errmsg or 'empty response'}")
        result = chunk_result
        print(f"[transcription] Done | lang={result.get('language')} "
              f"| segments={len(result.get('segments', []))}")
        apply_word_corrections(result["segments"])
        return result, skipped_chunks

    print(f"[transcription] File > 24MB — splitting into {_CHUNK_SECONDS}s chunks "
          f"(parallel={parallel_chunks})")

    tmpdir, chunks = await asyncio.to_thread(_prepare_split_chunks, path, _CHUNK_SECONDS)
    n = len(chunks)
    results: Dict[int, Tuple[str, float, Optional[dict], Optional[str]]] = {}
    par = max(1, int(parallel_chunks))
    audio_total = await asyncio.to_thread(_ffprobe_duration, path)

    try:
        await _notify(0, n)
        completed = 0

        for batch_start in range(0, n, par):
            batch_idxs = list(range(batch_start, min(batch_start + par, n)))

            async def _work(ci: int) -> Tuple[int, float, Optional[dict], Optional[str]]:
                cpath, toff = chunks[ci]
                res, errmsg = await _transcribe_chunk_with_retries(client, cpath, prompt)
                return ci, toff, res, errmsg

            tasks = [asyncio.create_task(_work(i)) for i in batch_idxs]
            for fut in asyncio.as_completed(tasks):
                i, toff, chunk_result, errmsg = await fut
                if errmsg or chunk_result is None:
                    skipped_chunks.append({"chunk_index": i, "error": errmsg or "?"})
                    results[i] = ("skip", toff, None, errmsg)
                else:
                    results[i] = ("ok", toff, chunk_result, None)
                completed += 1
                await _notify(completed, n)

        all_text: List[str] = []
        all_segments: List = []
        detected_lang = ""
        seg_id_offset = 0

        for i in range(n):
            kind, time_offset, chunk_result, errmsg = results[i]
            if kind == "ok" and chunk_result is not None:
                cr = chunk_result
                if not detected_lang:
                    detected_lang = cr.get("language", "")
                if time_offset > 0 or seg_id_offset > 0:
                    cr = _shift_timestamps(cr, time_offset, seg_id_offset)
                all_text.append(cr["text"].strip())
                all_segments.extend(cr["segments"])
                seg_id_offset += len(cr["segments"])
            else:
                cpath, toff = chunks[i]
                chunk_dur = await asyncio.to_thread(_ffprobe_duration, cpath)
                if chunk_dur <= 0:
                    chunk_dur = float(_CHUNK_SECONDS)
                end_t = min(toff + chunk_dur, audio_total) if audio_total > 0 else toff + chunk_dur
                placeholder = {
                    "id": seg_id_offset,
                    "start": round(toff, 3),
                    "end": round(end_t, 3),
                    "text": f"[Не расшифровано — фрагмент {i + 1}: {errmsg or '?'}]",
                    "words": [],
                    "_chunk_skipped": True,
                }
                all_segments.append(placeholder)
                all_text.append(placeholder["text"])
                seg_id_offset += 1

        result = {
            "text": " ".join(all_text),
            "language": detected_lang,
            "segments": all_segments,
        }
        print(f"[transcription] Merged {len(all_segments)} segments | lang={detected_lang} "
              f"| skipped={len(skipped_chunks)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    apply_word_corrections(result["segments"])
    return result, skipped_chunks


def run_whisper_transcribe(
    audio_path: Union[str, Path],
    word_timestamps: bool = True,
    initial_prompt: Optional[str] = None,
):
    """
    Transcribe audio via OpenAI Whisper API (sync wrapper).

    Files > 24MB are automatically split into 10-minute chunks via ffmpeg,
    each chunk is transcribed separately (up to 3 in parallel), and results
    are merged with correct absolute timestamps.

    Returns a dict in the same format as the previous local Whisper backends:
      {"text": str, "language": str, "segments": [...]}
    """
    path = Path(audio_path) if not isinstance(audio_path, Path) else audio_path
    result, _skipped = asyncio.run(
        run_whisper_transcribe_async(
            path,
            word_timestamps=word_timestamps,
            initial_prompt=initial_prompt,
            on_chunk_done=None,
            parallel_chunks=_PARALLEL_CHUNKS_DEFAULT,
        )
    )
    return result


