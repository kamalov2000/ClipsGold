"""
Transcription service: faster-whisper ASR with initial_prompt and LLM refinement layer.
Uses CTranslate2 backend (int8 quantization) — ~4x faster than openai-whisper on CPU.
"""

import gc
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()


def _load_whisper_model():
    from faster_whisper import WhisperModel
    print("[transcription] Loading faster-whisper model 'medium' (int8, CPU)...")
    model = WhisperModel("medium", device="cpu", compute_type="int8")
    print("[transcription] faster-whisper model loaded.")
    return model


def _unload_whisper_model(model) -> None:
    """Release faster-whisper model from memory immediately after use."""
    try:
        del model
    except Exception:
        pass
    gc.collect()
    print("[transcription] faster-whisper model unloaded.")


# Initial prompt for Whisper to improve recognition of common terms (max ~224 tokens)
INITIAL_PROMPT_TERMS = "South Park, Cartman, ClipsGold, YouTube, TikTok, Instagram, viral, clip, менты, ментов, копы, предприятие, предприятиях, одежда, одежду, шить, шила, работой, следах, рабский, рабство, милиция, милиции, советский, союза."

# Direct word-level corrections for known Whisper ASR errors.
# Applied after transcription, word-by-word, case-insensitive on stripped form.
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
    """
    Apply direct word-level corrections for known Whisper ASR errors.
    Updates word text in-place, keeps timestamps unchanged.
    """
    import re
    strip_punct = re.compile(r"[^\w]", re.UNICODE)
    for seg in segments:
        corrected_words = []
        for w in seg.get("words", []):
            raw = w.get("word", "")
            key = strip_punct.sub("", raw).lower()
            if key in _WORD_CORRECTIONS:
                # Preserve leading space and trailing punctuation
                prefix = " " if raw.startswith(" ") else ""
                suffix = raw[-1] if raw and not raw[-1].isalpha() and not raw[-1].isdigit() else ""
                w["word"] = prefix + _WORD_CORRECTIONS[key] + suffix
                corrected_words.append(f"{raw.strip()} -> {w['word'].strip()}")
        if corrected_words:
            print(f"    [word fix] {', '.join(corrected_words)}")
        # Rebuild segment text from corrected words
        seg["text"] = "".join(w.get("word", "") for w in seg.get("words", []))


def _convert_faster_whisper_result(segments_iter, info) -> dict:
    """
    Convert faster-whisper output to openai-whisper dict format.

    faster-whisper returns:
      - segments: generator of Segment(start, end, text, words=[Word(start, end, word, probability)])
      - info: TranscriptionInfo(language, language_probability, duration, ...)

    openai-whisper format expected by the rest of the codebase:
      {
        "text": "...",
        "language": "ru",
        "segments": [
          {
            "id": N, "start": float, "end": float, "text": " ...",
            "words": [{"word": " text", "start": float, "end": float, "probability": float}]
          }
        ]
      }

    Note: openai-whisper prefixes each word with a leading space; we replicate that
    so apply_word_corrections and subtitle generators work unchanged.
    """
    out_segments = []
    full_text_parts = []

    for seg in segments_iter:  # consume the generator
        words = []
        for w in (seg.words or []):
            word_text = " " + w.word.lstrip()  # add leading space like openai-whisper
            words.append({
                "word": word_text,
                "start": w.start,
                "end": w.end,
                "probability": w.probability,
            })

        seg_text = seg.text  # faster-whisper already includes leading space
        full_text_parts.append(seg_text)

        out_segments.append({
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg_text,
            "words": words,
        })

    return {
        "text": "".join(full_text_parts),
        "language": info.language,
        "segments": out_segments,
    }


def run_whisper_transcribe(audio_path: Path, word_timestamps: bool = True, initial_prompt: Optional[str] = None):
    """
    Run faster-whisper on an audio file.
    Uses initial_prompt to bias recognition of brands and common terms.
    int8 quantization on CPU — ~4x faster than openai-whisper FP32.
    """
    import sys
    _backend_dir = str(Path(__file__).parent.parent)
    if _backend_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _backend_dir + os.pathsep + os.environ.get("PATH", "")

    model = _load_whisper_model()
    prompt = (initial_prompt or INITIAL_PROMPT_TERMS)[:500]
    try:
        segments_iter, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            language=None,           # auto-detect language
            word_timestamps=word_timestamps,
            initial_prompt=prompt,
            vad_filter=True,         # skip silence — speeds up CPU transcription
            vad_parameters={"min_silence_duration_ms": 500},
        )
        print(f"[transcription] Detected language: {info.language} (p={info.language_probability:.2f})")
        result = _convert_faster_whisper_result(segments_iter, info)
        apply_word_corrections(result["segments"])
        return result
    finally:
        _unload_whisper_model(model)
