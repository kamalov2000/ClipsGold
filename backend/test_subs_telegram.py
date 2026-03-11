"""
Full subtitle pipeline test: transcribe -> generate .ass -> render -> send to Telegram
"""

import os
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
CLIPS_DIR  = BASE_DIR / "clips"
FONTS_DIR  = BASE_DIR / "assets" / "fonts"
FFMPEG     = str(BASE_DIR / "ffmpeg.exe") if (BASE_DIR / "ffmpeg.exe").exists() else "ffmpeg"

OUTPUT_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)

VIDEO = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")
CLIP_START = 5.0
CLIP_END   = 35.0   # 30-second clip
PLATFORM   = "tiktok"
STYLE      = "hormozi"

print("=" * 60)
print("SUBTITLE PIPELINE TEST")
print("=" * 60)
print(f"Video : {VIDEO}")
print(f"Clip  : {CLIP_START}s — {CLIP_END}s ({CLIP_END - CLIP_START:.0f}s)")
print(f"Style : {STYLE} / {PLATFORM}")
print()

if not VIDEO.exists():
    print(f"ERROR: video not found at {VIDEO}")
    sys.exit(1)

# ── STEP 1: Transcribe ─────────────────────────────────────────
print("STEP 1: Whisper transcription...")
t0 = time.time()
from services.transcription import run_whisper_transcribe

transcription = run_whisper_transcribe(str(VIDEO), word_timestamps=True)
segs = transcription.get("segments", [])
total_words = sum(len(s.get("words", [])) for s in segs)
print(f"  Done in {time.time()-t0:.1f}s — {len(segs)} segments, {total_words} words")

if total_words == 0:
    print("  WARNING: no word-level timestamps! Subtitles will be empty.")

# ── STEP 2: Generate .ass subtitle file ───────────────────────
print("\nSTEP 2: Generate ASS subtitle file...")
from subtitle_generator_v2 import create_subtitle_generator

sub_path = OUTPUT_DIR / "test_subs_check.ass"
sub_gen = create_subtitle_generator(use_semantic_chunking=False)  # fixed chunking, no GPT needed
sub_gen.generate_ass_from_transcription(
    transcription_data=transcription,
    output_path=sub_path,
    hook_text="",
    clip_start_time=CLIP_START,
    clip_end_time=CLIP_END,
    clip_duration=CLIP_END - CLIP_START,
    platform=PLATFORM,
    subtitle_style=STYLE,
)

# Count Dialogue lines
dialogue_lines = [l for l in sub_path.read_text(encoding="utf-8-sig").splitlines() if l.startswith("Dialogue:")]
print(f"  ASS file: {sub_path}")
print(f"  Dialogue lines: {len(dialogue_lines)}")
if dialogue_lines:
    print(f"  First line: {dialogue_lines[0][:100]}")
else:
    print("  WARNING: 0 Dialogue lines — subtitles will NOT appear!")

# ── STEP 3: Build FFmpeg command ───────────────────────────────
print("\nSTEP 3: Build FFmpeg command...")

TEMP_DIR = OUTPUT_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
temp_cut  = TEMP_DIR / "test_cut.mp4"
clip_out  = CLIPS_DIR / "test_subtitle_result.mp4"

# Pass 1 — cut to reset timestamps
cmd_pass1 = [
    FFMPEG,
    "-ss", str(CLIP_START), "-t", str(CLIP_END - CLIP_START),
    "-i", str(VIDEO),
    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
    "-c:a", "aac", "-b:a", "128k",
    "-y", str(temp_cut)
]
print(f"  Pass 1: {' '.join(cmd_pass1)}")

r1 = subprocess.run(cmd_pass1, capture_output=True, text=True)
if r1.returncode != 0:
    print(f"  PASS 1 FAILED:\n{r1.stderr[-500:]}")
    sys.exit(1)
print(f"  Pass 1 OK ({temp_cut.stat().st_size // 1024} KB)")

# Pass 2 — subtitles filter + scale
rel_sub = os.path.relpath(sub_path, os.getcwd()).replace('\\', '/').replace(':', '\\:')

vf_chain = (
    # Source is already 9:16 (720x1280) — just scale up to 1080x1920
    "scale=1080:1920"
    f",subtitles={rel_sub}"
)

cmd_pass2 = [
    FFMPEG, "-i", str(temp_cut),
    "-vf", vf_chain,
    "-c:v", "libx264", "-preset", "fast", "-crf", "20",
    "-c:a", "aac", "-b:a", "128k",
    "-r", "30", "-pix_fmt", "yuv420p",
    "-y", str(clip_out)
]
print(f"\n  Pass 2: {' '.join(cmd_pass2)}")

t0 = time.time()
r2 = subprocess.run(cmd_pass2, capture_output=True, text=True)
print(f"  Return code: {r2.returncode} (took {time.time()-t0:.1f}s)")

if r2.returncode != 0:
    print(f"  PASS 2 FAILED — last stderr lines:")
    for ln in r2.stderr.splitlines()[-20:]:
        print(f"    {ln}")
    sys.exit(1)

size_mb = clip_out.stat().st_size / 1024 / 1024
print(f"  Output: {clip_out} ({size_mb:.2f} MB)")

# Check if subtitles filter was actually used in stderr
if "subtitles" in r2.stderr.lower() and "error" in r2.stderr.lower():
    print("  WARNING: subtitles filter error in FFmpeg stderr:")
    for ln in r2.stderr.splitlines():
        if "subtitles" in ln.lower() or "ass" in ln.lower() or "libass" in ln.lower():
            print(f"    {ln}")

# ── STEP 4: Send to Telegram ───────────────────────────────────
print("\nSTEP 4: Sending to Telegram...")

caption = "Субтитры видны?"

from services.telegram_notifier import send_video_file

if size_mb > 50:
    print(f"  WARNING: {size_mb:.1f} MB > 50 MB Telegram limit, skipping send")
else:
    ok = send_video_file(str(clip_out), caption=caption)
    print(f"  Telegram: {'OK' if ok else 'FAILED'}")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
