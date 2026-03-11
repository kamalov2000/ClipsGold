"""
2-pass subtitle rendering for perfect timing sync
Pass 1: Cut clip (timestamps reset to 0)
Pass 2: Apply subtitles (timestamps now match)
"""

import sys, os, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from services.transcription import run_whisper_transcribe
from services.ai_engine import fix_segments_with_openai
from subtitle_generator_v2 import SubtitleGeneratorV2

test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")
CLIPS_DIR = Path("clips")
OUTPUT_DIR = Path("outputs")
CLIPS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

print("1. Transcribing full video...")
result = run_whisper_transcribe(str(test_video), word_timestamps=True)
segments = result.get('segments', [])
total_words = sum(len(s.get('words', [])) for s in segments)
duration = result.get('duration', 0)
if not duration and segments:
    duration = segments[-1].get('end', 0)
print(f"   Duration: {duration:.1f}s")
print(f"   Segments: {len(segments)}, total words: {total_words}")
for i, seg in enumerate(segments, 1):
    words = seg.get('words', [])
    print(f"   Seg {i}: {seg['start']:.1f}-{seg['end']:.1f}s | {len(words)} words")

print("\n2. GPT-4o correction (fix misrecognized words, keep timestamps)...")
import asyncio
asyncio.run(fix_segments_with_openai(segments))
print("   Done")

print("\n3. Generating subtitles for FULL video (no word removal)...")

# use_semantic_chunking=False to guarantee zero word loss
subtitle_gen = SubtitleGeneratorV2(use_semantic_chunking=False)
subtitle_path = OUTPUT_DIR / "full_video_subs.ass"

subtitle_gen.generate_ass_from_transcription(
    transcription_data={'segments': segments},
    output_path=subtitle_path,
    clip_start_time=0.0,
    clip_end_time=duration,
    platform='tiktok',
    subtitle_style='hormozi'
)

with open(subtitle_path, 'r', encoding='utf-8-sig') as f:
    event_count = sum(1 for l in f if l.startswith('Dialogue:'))
print(f"   Subtitle events: {event_count} (should be ~{total_words // 3})")

print("\n3. Rendering full video with subtitles...")
clip_final = CLIPS_DIR / "full_video_subs.mp4"

rel_sub = os.path.relpath(subtitle_path, os.getcwd()).replace('\\', '/')

cmd = [
    'ffmpeg',
    '-i', str(test_video),
    '-vf', f'subtitles={rel_sub}',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-c:a', 'copy',
    '-y', str(clip_final)
]

r = subprocess.run(cmd, capture_output=True, timeout=300)
if clip_final.exists():
    print(f"   SUCCESS! {clip_final.stat().st_size/1024/1024:.2f} MB")
    print(f"\n   Path: {clip_final.absolute()}")
    print("\n   Open and check - ALL words, perfect sync!")
else:
    print(f"   FAILED: {r.stderr.decode()[:300]}")
