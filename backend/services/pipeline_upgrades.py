"""
Video pipeline upgrades:
  1. loudnorm_filter()      — EBU R128 audio normalization for Pass 2
  2. check_lufs_compliance() — CI/QA: verify rendered clip is within LUFS/TP spec
  3. SAFE_ZONES             — per-platform subtitle placement rules engine
  4. get_safe_margin_v()    — compute ASS MarginV from platform safe zone
  5. FILLER_WORDS           — regex pattern for RU+EN filler words
  6. remove_filler_words()  — mark filler word timestamps for FFmpeg concat removal
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# ─────────────────────────────────────────────────────────────
# 1. Audio Normalization — EBU R128 loudnorm
# ─────────────────────────────────────────────────────────────

def loudnorm_filter(
    integrated_loudness: float = -16.0,
    true_peak: float = -1.5,
    loudness_range: float = 11.0,
    linear: bool = True,
) -> str:
    """
    Build an FFmpeg loudnorm audio filter string targeting EBU R128.

    Defaults:
      I  = -16 LUFS  — standard for online short-form content
      TP = -1.5 dBTP — prevents clipping on mobile speakers
      LRA = 11 LU    — moderate dynamic range

    linear=True uses single-pass linear normalization (fast, good for clips).
    For highest accuracy use two-pass (measure first, then normalize).

    Usage in Pass 2 cmd:
        cmd_pass2.extend(["-af", loudnorm_filter()])
    """
    mode = "linear=true" if linear else "linear=false"
    return (
        f"loudnorm=I={integrated_loudness}:TP={true_peak}:LRA={loudness_range}:{mode}"
    )


# ─────────────────────────────────────────────────────────────
# 2. LUFS Compliance CI Check — ebur128
# ─────────────────────────────────────────────────────────────

@dataclass
class LufsResult:
    integrated_lufs: float
    true_peak_dbtp: float
    lra: float
    passed: bool
    reason: str  # empty string when passed


def check_lufs_compliance(
    clip_path: Path,
    min_lufs: float = -17.0,
    max_lufs: float = -15.0,
    max_true_peak: float = -1.0,
) -> LufsResult:
    """
    Run FFmpeg ebur128 filter on a rendered clip and verify it meets spec:
      - Integrated loudness within [min_lufs, max_lufs]  (default: -17 to -15 LUFS)
      - True Peak < max_true_peak                         (default: -1.0 dBTP)

    Uses FFmpeg's built-in ebur128 filter (no extra deps).
    Returns a LufsResult; check result.passed before uploading to S3.

    Usage in CI / post-render QA:
        result = check_lufs_compliance(Path("clip.mp4"))
        if not result.passed:
            raise ValueError(result.reason)
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(clip_path),
        "-af", "ebur128=peak=true",
        "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        stderr = proc.stderr.decode("utf-8", errors="ignore")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return LufsResult(
            integrated_lufs=0.0, true_peak_dbtp=0.0, lra=0.0,
            passed=False, reason=f"ebur128 measurement failed: {exc}",
        )

    # Parse summary block printed at end of ebur128 output
    integrated = _parse_ebur128_float(stderr, r"I:\s*([-\d.]+)\s*LUFS")
    true_peak  = _parse_ebur128_float(stderr, r"True peak:\s*\n?\s*Peak:\s*([-\d.]+)\s*dBFS")
    lra        = _parse_ebur128_float(stderr, r"LRA:\s*([-\d.]+)\s*LU")

    # Fallback: some FFmpeg builds print "Integrated loudness" differently
    if integrated == 0.0:
        integrated = _parse_ebur128_float(stderr, r"Integrated loudness[^\n]*\n\s*I:\s*([-\d.]+)")
    if true_peak == 0.0:
        true_peak = _parse_ebur128_float(stderr, r"True peak[^\n]*\n\s*Peak:\s*([-\d.]+)")

    reasons = []
    if integrated < min_lufs or integrated > max_lufs:
        reasons.append(
            f"Integrated loudness {integrated:.1f} LUFS outside [{min_lufs}, {max_lufs}]"
        )
    if true_peak > max_true_peak:
        reasons.append(f"True Peak {true_peak:.1f} dBTP exceeds {max_true_peak} dBTP")

    return LufsResult(
        integrated_lufs=integrated,
        true_peak_dbtp=true_peak,
        lra=lra,
        passed=len(reasons) == 0,
        reason="; ".join(reasons),
    )


def _parse_ebur128_float(text: str, pattern: str) -> float:
    """Extract a float from ebur128 stderr output. Returns 0.0 if not found."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return 0.0


# ─────────────────────────────────────────────────────────────
# 3. Safe Zones Rules Engine
# ─────────────────────────────────────────────────────────────

# All values as fraction of frame height (0.0–1.0)
# top_clear    — fraction from top that must stay free (platform UI: progress bar, back button)
# bottom_clear — fraction from bottom that must stay free (platform UI: like/share/caption)
# subtitle_pos — recommended subtitle center as fraction from top (within safe area)
SAFE_ZONES: Dict[str, Dict[str, float]] = {
    "tiktok": {
        "top_clear":     0.15,   # ~288px @ 1920h — TikTok progress bar + username
        "bottom_clear":  0.32,   # ~614px @ 1920h — raised higher, away from UI
        "subtitle_pos":  0.62,   # center of subtitle block from top
        "hook_pos":      0.12,   # hook text from top (just inside safe area)
    },
    "instagram": {
        "top_clear":     0.10,   # ~192px — story/reel header
        "bottom_clear":  0.35,   # ~672px — raised higher
        "subtitle_pos":  0.60,
        "hook_pos":      0.08,
    },
    "youtube": {
        "top_clear":     0.08,   # ~154px — progress bar
        "bottom_clear":  0.25,   # ~480px — raised higher
        "subtitle_pos":  0.65,
        "hook_pos":      0.06,
    },
}

_DEFAULT_ZONE = SAFE_ZONES["tiktok"]

PLAY_RES_Y = 1920  # 9:16 vertical resolution


def get_safe_margin_v(platform: str, play_res_y: int = PLAY_RES_Y) -> int:
    """
    Compute ASS MarginV (distance from bottom) for subtitle Default style.
    Ensures subtitles never overlap platform UI elements.

    ASS Alignment=2 (bottom-center): MarginV = distance from bottom edge.
    """
    zone = SAFE_ZONES.get(platform, _DEFAULT_ZONE)
    # bottom_clear fraction -> pixels from bottom -> that's our minimum MarginV
    min_margin = int(play_res_y * zone["bottom_clear"])
    # Add a small padding buffer (32px)
    return min_margin + 32


def get_hook_margin_v(platform: str, play_res_y: int = PLAY_RES_Y) -> int:
    """
    Compute ASS MarginV for Hook style (top-aligned, Alignment=8).
    ASS Alignment=8 (top-center): MarginV = distance from top edge.
    """
    zone = SAFE_ZONES.get(platform, _DEFAULT_ZONE)
    return int(play_res_y * zone["hook_pos"]) + 16


# ─────────────────────────────────────────────────────────────
# 3. Filler Word Removal
# ─────────────────────────────────────────────────────────────

# Russian + English filler words / hesitation markers
_FILLER_PATTERN = re.compile(
    r"^("
    # English
    r"uh+|um+|hmm+|hm+|er+|erm+|ah+|like|you\s+know|i\s+mean|"
    r"basically|literally|actually|right\?|okay\?|so+|well+|"
    # Russian
    r"эм+|ну+|вот|типа|как\s+бы|значит|короче|понимаешь|"
    r"слушай|слушайте|собственно|в\s+общем|то\s+есть|"
    r"как\s+сказать|ладно|окей"
    r")$",
    re.IGNORECASE | re.UNICODE,
)


def is_filler_word(word: str) -> bool:
    """Return True if the word is a filler/hesitation marker."""
    return bool(_FILLER_PATTERN.match(word.strip().lower()))


def find_filler_segments(
    transcription_data: dict,
    clip_start: float,
    clip_end: float,
) -> List[Dict]:
    """
    Scan word-level timestamps and return list of {start, end} intervals
    for filler words within the clip range.

    These intervals can be passed to build_concat_without_fillers() to
    generate an FFmpeg concat filter that removes them.
    """
    filler_intervals: List[Dict] = []
    segments = transcription_data.get("segments", []) if transcription_data else []

    for seg in segments:
        seg_s = seg.get("start", 0)
        seg_e = seg.get("end", 0)
        if seg_e < clip_start or seg_s > clip_end:
            continue
        for w in seg.get("words", []):
            ws = w.get("start", 0)
            we = w.get("end", 0)
            word_text = w.get("word", "").strip()
            if we > clip_start and ws < clip_end and is_filler_word(word_text):
                filler_intervals.append({"start": ws - clip_start, "end": we - clip_start})

    return filler_intervals


def build_keep_segments_without_fillers(
    clip_duration: float,
    filler_intervals: List[Dict],
    min_segment_duration: float = 0.1,
) -> Optional[List[Dict]]:
    """
    Given filler word intervals (relative to clip start), compute the
    inverse: list of {start, end} keep-segments that exclude fillers.

    Returns None if no fillers found (no-op).
    Returns list of keep-segments for FFmpeg concat.

    Merges filler intervals that are within 0.05s of each other to avoid
    micro-cuts that produce audio glitches.
    """
    if not filler_intervals:
        return None

    # Sort and merge overlapping/adjacent filler intervals
    sorted_fillers = sorted(filler_intervals, key=lambda x: x["start"])
    merged: List[Dict] = []
    for fi in sorted_fillers:
        if merged and fi["start"] - merged[-1]["end"] < 0.05:
            merged[-1]["end"] = max(merged[-1]["end"], fi["end"])
        else:
            merged.append(dict(fi))

    # Build keep-segments as inverse of merged fillers
    keep: List[Dict] = []
    cursor = 0.0
    for fi in merged:
        if fi["start"] - cursor > min_segment_duration:
            keep.append({"start": cursor, "end": fi["start"]})
        cursor = fi["end"]

    if clip_duration - cursor > min_segment_duration:
        keep.append({"start": cursor, "end": clip_duration})

    return keep if len(keep) > 1 else None
