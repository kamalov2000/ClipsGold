"""
Transcription service: Whisper ASR with initial_prompt and LLM refinement layer.
"""

import gc
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()


def _load_whisper_model():
    import whisper
    print("[transcription] Loading Whisper model 'base'...")
    model = whisper.load_model("base")
    print("[transcription] Whisper model loaded.")
    return model


def _unload_whisper_model(model) -> None:
    """Release Whisper model from memory immediately after use."""
    try:
        import torch
        if hasattr(model, "encoder"):
            model.encoder.cpu()
        if hasattr(model, "decoder"):
            model.decoder.cpu()
        del model
        torch.cuda.empty_cache()
    except Exception:
        del model
    gc.collect()
    print("[transcription] Whisper model unloaded.")

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


def run_whisper_transcribe(audio_path: Path, word_timestamps: bool = True, initial_prompt: Optional[str] = None):
    """
    Run OpenAI Whisper on an audio file.
    Uses initial_prompt to bias recognition of brands and common terms.
    """
    # Whisper calls ffmpeg internally via subprocess. If ffmpeg is not in PATH
    # (e.g. only local ffmpeg.exe in backend dir), we add it here.
    import sys
    _backend_dir = str(Path(__file__).parent.parent)
    if _backend_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _backend_dir + os.pathsep + os.environ.get("PATH", "")
    model = _load_whisper_model()
    prompt = initial_prompt or INITIAL_PROMPT_TERMS
    try:
        result = model.transcribe(
            str(audio_path),
            word_timestamps=word_timestamps,
            initial_prompt=prompt[:500],
        )
        apply_word_corrections(result.get("segments", []))
        return result
    finally:
        _unload_whisper_model(model)


def refine_transcript(raw_text: str) -> str:
    """
    Use GPT to proofread and correct the raw ASR output.
    - Fix misheard words (e.g. phonetically similar).
    - Keep brands and English names in English.
    - Do not omit small words (e.g. "Это", "даже") if they were likely spoken.
    Returns the corrected transcript only; does not change timing/segments.
    """
    if not raw_text or not raw_text.strip():
        return raw_text

    prompt = f"""You are a careful proofreader for speech-to-text output. Correct the following transcript.

RULES:
1. Fix misheard words: correct obvious ASR errors (e.g. "пизоц" -> "очень", "Сава Спарк" -> "South Park"). Keep the same language and meaning.
2. Brands and English names must stay in English: South Park, Cartman, ClipsGold, YouTube, TikTok, etc.
3. Do NOT omit small words like "Это", "даже", "вот", "ну", "так" if they fit the flow of speech—only fix clear errors.
4. Preserve the original structure: same paragraphs/line breaks if any, same tone. Output ONLY the corrected transcript, no explanations."""

    user_content = f"Transcript to correct:\n\n{raw_text}"

    try:
        if os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a proofreader. Output ONLY the corrected transcript, no other text."},
                    {"role": "user", "content": f"{prompt}\n\n{user_content}"},
                ],
                temperature=0.2,
                max_tokens=4096,
            )
            refined = (response.choices[0].message.content or "").strip()
            if refined:
                return refined
    except Exception:
        pass

    return raw_text
