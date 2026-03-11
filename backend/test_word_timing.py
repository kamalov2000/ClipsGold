"""
Test word-by-word subtitle timing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.transcription import run_whisper_transcribe
from subtitle_generator_v2 import create_subtitle_generator

test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")

print("1. Transcribing...")
result = run_whisper_transcribe(str(test_video), word_timestamps=True)

segments = result.get('segments', [])
print(f"   Segments: {len(segments)}")

# Check first segment words
seg1 = segments[0] if segments else {}
words1 = seg1.get('words', [])
print(f"   Segment 1 words: {len(words1)}")

if words1:
    print("\n   First 3 words:")
    for w in words1[:3]:
        print(f"     {w.get('start', 0):.2f}-{w.get('end', 0):.2f}s: '{w.get('word', '')}'")

print("\n2. Generating subtitles...")

subtitle_gen = create_subtitle_generator()
output_path = Path("outputs/word_timing_test.ass")
output_path.parent.mkdir(exist_ok=True)

# Generate for clip 5-20s
subtitle_gen.generate_ass_from_transcription(
    transcription_data={'segments': segments},
    output_path=output_path,
    clip_start_time=5.0,
    clip_end_time=20.0,
    platform='tiktok',
    subtitle_style='hormozi'
)

print(f"   Subtitle file: {output_path}")
print(f"   Size: {output_path.stat().st_size} bytes")

# Show subtitle content
print("\n3. Subtitle content (Events section):")
with open(output_path, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()
    
in_events = False
event_count = 0

for line in lines:
    if '[Events]' in line:
        in_events = True
        continue
    
    if in_events:
        if line.startswith('Dialogue:'):
            event_count += 1
            if event_count <= 3:
                # Parse dialogue line
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    start = parts[1]
                    end = parts[2]
                    text = parts[9].strip()
                    print(f"\n   Event {event_count}:")
                    print(f"     Time: {start} -> {end}")
                    print(f"     Text: {text[:100]}")

print(f"\n   Total events: {event_count}")

print("\n4. Rendering video...")

import subprocess

clip_path = Path("clips/word_timing_test.mp4")

import os
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
    print(f"   Path: {clip_path.absolute()}")
    print("\n   Open clip and check if words appear one-by-one!")
else:
    print("   FAILED")
    if result.stderr:
        print(f"   Error: {result.stderr.decode()[:200]}")
