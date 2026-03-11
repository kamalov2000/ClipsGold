"""
Test simple word-by-word subtitles without semantic chunking
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.transcription import run_whisper_transcribe
from subtitle_generator_v2 import SubtitleGeneratorV2

test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")

print("1. Transcribing...")
result = run_whisper_transcribe(str(test_video), word_timestamps=True)

segments = result.get('segments', [])
print(f"   Segments: {len(segments)}")

print("\n2. Generating subtitles (NO semantic chunking)...")

# Create generator WITHOUT semantic chunking
subtitle_gen = SubtitleGeneratorV2(use_semantic_chunking=False)

output_path = Path("outputs/simple_subs.ass")
output_path.parent.mkdir(exist_ok=True)

subtitle_gen.generate_ass_from_transcription(
    transcription_data={'segments': segments},
    output_path=output_path,
    clip_start_time=5.0,
    clip_end_time=20.0,
    platform='tiktok',
    subtitle_style='hormozi'
)

print(f"   File: {output_path}")
print(f"   Size: {output_path.stat().st_size} bytes")

# Count events
with open(output_path, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

event_count = sum(1 for line in lines if line.startswith('Dialogue:'))
print(f"   Events: {event_count}")

print("\n3. Rendering...")

import subprocess
import os

clip_path = Path("clips/simple_subs_test.mp4")

rel_subtitle_path = os.path.relpath(output_path, os.getcwd())
rel_subtitle_path = rel_subtitle_path.replace('\\', '/')

cmd = [
    'ffmpeg',
    '-i', str(test_video),
    '-ss', '5.0',
    '-t', '15.0',
    '-vf', f'subtitles={rel_subtitle_path}',
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-crf', '23',
    '-c:a', 'copy',
    '-y',
    str(clip_path)
]

result = subprocess.run(cmd, capture_output=True, timeout=60)

if clip_path.exists():
    size_mb = clip_path.stat().st_size / 1024 / 1024
    print(f"   SUCCESS! {size_mb:.2f} MB")
    print(f"\n   Path: {clip_path.absolute()}")
    print("\n   NOW CHECK: Words should appear one-by-one!")
else:
    print("   FAILED")
