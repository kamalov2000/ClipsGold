"""
Transcription service: OpenAI Whisper API (whisper-1).
Word-level timestamps via verbose_json + timestamp_granularities.
Large files split into 10-minute chunks processed sequentially.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union

_CHUNK_SECONDS = 600  # 10-min chunks ≈ 18 MB WAV — safely under 25 MB API limit

# Initial prompt to bias Whisper toward domain-specific vocabulary
INITIAL_PROMPT_TERMS = (
    "South Park, Cartman, ClipsGold, YouTube, TikTok, Instagram, viral, clip, "
    "менты, ментов, копы, предприятие, предприятиях, одежда, одежду, шить, шила, "
    "работой, следах, рабский, рабство, милиция, милиции, советский, союза."
)

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


def _get_client():
    from openai import AsyncOpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=api_key)


def apply_word_corrections(segments: list) -> None:
    import re
    strip_punct = re.compile(r"[^\w]", re.UNICODE)
    for seg in segments:
        corrected = []
        for w in seg.get("words", []):
            raw = w.get("word", "")
            key = strip_punct.sub("", raw).lower()
            if key in _WORD_CORRECTIONS:
                prefix = " " if raw.startswith(" ") else ""
                suffix = raw[-1] if raw and not raw[-1].isalpha() and not raw[-1].isdigit() else ""
                w["word"] = prefix + _WORD_CORRECTIONS[key] + suffix
                corrected.append(f"{raw.strip()} -> {w['word'].strip()}")
        if corrected:
            print(f"    [word fix] {', '.join(corrected)}")
            seg["text"] = "".join(w.get("word", "") for w in seg.get("words", []))


def _ffprobe_duration(path: Path) -> float:
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
    duration = _ffprobe_duration(audio_path)
    if duration <= 0:
        return [(audio_path, 0.0)]
    chunks = []
    start = 0.0
    idx = 0
    while start < duration:
        chunk_path = Path(tmpdir) / f"chunk_{idx:03d}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(audio_path),
             "-ss", str(start), "-t", str(chunk_sec),
             "-ac", "1", "-ar", "16000",
             str(chunk_path)],
            capture_output=True, check=True,
        )
        if chunk_path.exists() and chunk_path.stat().st_size > 100:
            chunks.append((chunk_path, start))
        start += chunk_sec
        idx += 1
    print(f"[transcription] Split into {len(chunks)} chunks ({chunk_sec}s each, total={duration:.0f}s)")
    return chunks


def _parse_openai_response(response, time_offset: float = 0.0, seg_id_offset: int = 0) -> dict:
    """Convert OpenAI verbose_json response to our internal segment format."""
    # Build word list with space prefix (matches existing subtitle pipeline)
    api_words = []
    for w in (getattr(response, "words", None) or []):
        word_str = w.word if isinstance(w.word, str) else str(w.word)
        if word_str and not word_str.startswith(" "):
            word_str = " " + word_str
        api_words.append({
            "word":        word_str,
            "start":       round(float(w.start) + time_offset, 3),
            "end":         round(float(w.end)   + time_offset, 3),
            "probability": 1.0,
        })

    # Build segments, attaching words that fall within each segment's time range
    segments = []
    for i, seg in enumerate(getattr(response, "segments", None) or []):
        seg_start = round(float(seg.start) + time_offset, 3)
        seg_end   = round(float(seg.end)   + time_offset, 3)
        seg_words = [w for w in api_words if w["end"] > seg_start and w["start"] < seg_end]
        segments.append({
            "id":    i + seg_id_offset,
            "start": seg_start,
            "end":   seg_end,
            "text":  seg.text,
            "words": seg_words,
        })

    # Fallback: if API returned no segments, create one from full text
    if not segments and response.text:
        segments.append({
            "id":    seg_id_offset,
            "start": time_offset,
            "end":   time_offset + 1.0,
            "text":  response.text,
            "words": api_words,
        })

    return {
        "text":     response.text or "",
        "language": getattr(response, "language", "") or "",
        "segments": segments,
    }


async def _transcribe_chunk(
    client,
    audio_path: Path,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> object:
    """Call OpenAI Whisper API for one audio file. Returns raw API response."""
    kwargs: dict = {
        "model":                    "whisper-1",
        "response_format":          "verbose_json",
        "timestamp_granularities":  ["word", "segment"],
    }
    if language:
        kwargs["language"] = language
    if initial_prompt:
        kwargs["prompt"] = initial_prompt[:500]

    with open(audio_path, "rb") as f:
        return await client.audio.transcriptions.create(file=f, **kwargs)


OnChunkDone = Callable[[int, int], Awaitable[None]]


async def run_whisper_transcribe_async(
    audio_path: Path,
    word_timestamps: bool = True,
    initial_prompt: Optional[str] = None,
    on_chunk_done: Optional[OnChunkDone] = None,
    parallel_chunks: int = 1,
) -> Tuple[dict, List[Dict]]:
    """
    Transcribe audio using OpenAI whisper-1 API.
    Large files are split into 10-minute chunks and processed sequentially.
    Language detected from the first chunk is reused for subsequent chunks.
    Each chunk receives the tail of the previous chunk's text as context prompt.
    Returns (result_dict, skipped_chunks).
    """
    path = Path(audio_path)
    file_size = path.stat().st_size
    prompt = initial_prompt or INITIAL_PROMPT_TERMS
    skipped_chunks: List[Dict] = []
    client = _get_client()

    async def _notify(done: int, total: int) -> None:
        if on_chunk_done:
            await on_chunk_done(done, total)

    print(f"[transcription] OpenAI whisper-1 | {path.name} | {file_size/1024/1024:.1f} MB")

    duration = await asyncio.to_thread(_ffprobe_duration, path)

    # Short file — transcribe in one shot
    if duration <= _CHUNK_SECONDS:
        await _notify(0, 1)
        response = await _transcribe_chunk(client, path, initial_prompt=prompt)
        result = _parse_openai_response(response)
        await _notify(1, 1)
        apply_word_corrections(result["segments"])
        print(f"[transcription] Done | lang={result.get('language')} | segments={len(result.get('segments', []))}")
        return result, skipped_chunks

    # Long file — split into chunks
    print(f"[transcription] File > {_CHUNK_SECONDS}s — splitting into chunks")
    tmpdir = tempfile.mkdtemp(prefix="cg_whisper_chunks_")
    try:
        chunks = await asyncio.to_thread(_split_audio, path, _CHUNK_SECONDS, tmpdir)
        n = len(chunks)
        all_text: List[str] = []
        all_segments: List = []
        detected_lang = ""
        seg_id_offset = 0
        last_text = ""  # tail of previous chunk fed as context to next

        await _notify(0, n)
        for i, (chunk_path, time_offset) in enumerate(chunks):
            # Reuse detected language for chunks 2+ (faster + consistent)
            lang_hint = detected_lang if detected_lang else None
            # Context prompt: previous chunk tail > domain prompt
            chunk_prompt = last_text[-200:] if last_text else prompt

            try:
                response = await _transcribe_chunk(
                    client, chunk_path,
                    language=lang_hint,
                    initial_prompt=chunk_prompt,
                )
                chunk_result = _parse_openai_response(response, time_offset=time_offset, seg_id_offset=seg_id_offset)

                if not detected_lang:
                    detected_lang = chunk_result.get("language", "")

                all_text.append(chunk_result["text"].strip())
                all_segments.extend(chunk_result["segments"])
                seg_id_offset += len(chunk_result["segments"])
                last_text = chunk_result["text"]

            except Exception as e:
                errmsg = str(e)
                print(f"[transcription] Chunk {i} failed: {errmsg}")
                skipped_chunks.append({"chunk_index": i, "error": errmsg})
                placeholder = {
                    "id":    seg_id_offset,
                    "start": round(time_offset, 3),
                    "end":   round(time_offset + _CHUNK_SECONDS, 3),
                    "text":  f"[Не расшифровано — фрагмент {i+1}: {errmsg}]",
                    "words": [],
                    "_chunk_skipped": True,
                }
                all_segments.append(placeholder)
                all_text.append(placeholder["text"])
                seg_id_offset += 1

            await _notify(i + 1, n)

        result = {"text": " ".join(all_text), "language": detected_lang, "segments": all_segments}
        print(f"[transcription] Merged {len(all_segments)} segs | lang={detected_lang} | skipped={len(skipped_chunks)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    apply_word_corrections(result["segments"])
    return result, skipped_chunks


def run_whisper_transcribe(
    audio_path: Union[str, Path],
    word_timestamps: bool = True,
    initial_prompt: Optional[str] = None,
) -> dict:
    path = Path(audio_path)
    result, _ = asyncio.run(
        run_whisper_transcribe_async(path, word_timestamps=word_timestamps, initial_prompt=initial_prompt)
    )
    return result
