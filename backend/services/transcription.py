"""
Transcription service: OpenAI Whisper API with auto-chunking for large files.
No local model — cloud-based, fast, language auto-detected.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# OpenAI Whisper API file size limit. 24MB leaves margin under the 25MB hard limit.
_OPENAI_MAX_BYTES = 24 * 1024 * 1024
# Chunk duration when splitting large audio files
_CHUNK_SECONDS = 600  # 10 minutes → ~5MB at 64kbps mono

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


def run_whisper_transcribe(
    audio_path: Path,
    word_timestamps: bool = True,
    initial_prompt: Optional[str] = None,
):
    """
    Transcribe audio via OpenAI Whisper API.

    Files > 24MB are automatically split into 10-minute chunks via ffmpeg,
    each chunk is transcribed separately, and results are merged with correct
    absolute timestamps.

    Returns a dict in the same format as the previous local Whisper backends:
      {"text": str, "language": str, "segments": [...]}
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    prompt = (initial_prompt or INITIAL_PROMPT_TERMS)[:500]
    file_size = audio_path.stat().st_size

    print(f"[transcription] OpenAI Whisper API | {audio_path.name} | {file_size/1024/1024:.1f}MB")

    if file_size <= _OPENAI_MAX_BYTES:
        # ── Fast path: single API call ──────────────────────────────────
        result = _transcribe_one(client, audio_path, prompt)
        print(f"[transcription] Done | lang={result.get('language')} "
              f"| segments={len(result.get('segments', []))}")
    else:
        # ── Large file: split → transcribe each chunk → merge ───────────
        print(f"[transcription] File > 24MB — splitting into {_CHUNK_SECONDS}s chunks")
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = _split_audio(audio_path, _CHUNK_SECONDS, tmpdir)

            all_text = []
            all_segments = []
            detected_lang = ""
            seg_id_offset = 0

            for i, (chunk_path, time_offset) in enumerate(chunks):
                sz = chunk_path.stat().st_size
                print(f"[transcription] Chunk {i+1}/{len(chunks)} "
                      f"offset={time_offset:.0f}s size={sz/1024:.0f}KB")
                chunk_result = _transcribe_one(client, chunk_path, prompt)

                if not detected_lang:
                    detected_lang = chunk_result.get("language", "")

                if time_offset > 0 or seg_id_offset > 0:
                    chunk_result = _shift_timestamps(chunk_result, time_offset, seg_id_offset)

                all_text.append(chunk_result["text"].strip())
                all_segments.extend(chunk_result["segments"])
                seg_id_offset += len(chunk_result["segments"])

        result = {
            "text":     " ".join(all_text),
            "language": detected_lang,
            "segments": all_segments,
        }
        print(f"[transcription] Merged {len(all_segments)} segments | lang={detected_lang}")

    apply_word_corrections(result["segments"])
    return result


def refine_transcript(raw_text: str) -> str:
    """Use GPT to proofread raw ASR output. Returns corrected text only."""
    if not raw_text or not raw_text.strip():
        return raw_text

    system = "You are a proofreader. Output ONLY the corrected transcript, no other text."
    user = (
        "You are a careful proofreader for speech-to-text output. Correct the following transcript.\n\n"
        "RULES:\n"
        "1. Fix misheard words (e.g. 'пизоц' -> 'очень', 'Сава Спарк' -> 'South Park'). Keep language and meaning.\n"
        "2. Brands and English names stay in English: South Park, Cartman, ClipsGold, YouTube, TikTok, etc.\n"
        "3. Do NOT omit small words like 'Это', 'даже', 'вот', 'ну', 'так' — only fix clear errors.\n"
        "4. Preserve structure and tone. Output ONLY the corrected transcript.\n\n"
        f"Transcript:\n\n{raw_text}"
    )

    try:
        if os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system},
                           {"role": "user",   "content": user}],
                temperature=0.2,
                max_tokens=4096,
            )
            refined = (response.choices[0].message.content or "").strip()
            if refined:
                return refined
    except Exception:
        pass

    return raw_text
