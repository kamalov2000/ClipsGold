"""
Test subtitles WITH Claude semantic chunking (ANTHROPIC_API_KEY)
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
for i, seg in enumerate(segments, 1):
    words = seg.get('words', [])
    print(f"   Seg {i}: {seg['start']:.1f}-{seg['end']:.1f}s | {len(words)} words | {seg['text'][:60].strip()}")

print("\n2. Generating subtitles WITH Claude semantic chunking...")

subtitle_gen = SubtitleGeneratorV2(use_semantic_chunking=True)
output_path = Path("outputs/gpt_subs.ass")
output_path.parent.mkdir(exist_ok=True)

subtitle_gen.generate_ass_from_transcription(
    transcription_data={'segments': segments},
    output_path=output_path,
    clip_start_time=5.0,
    clip_end_time=20.0,
    platform='tiktok',
    subtitle_style='hormozi'
)

size = output_path.stat().st_size
with open(output_path, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()
event_count = sum(1 for l in lines if l.startswith('Dialogue:'))

print(f"   File size: {size} bytes")
print(f"   Events: {event_count}")

print("\n3. Rendering...")
import subprocess, os

clip_path = Path("clips/gpt_subs_test.mp4")
rel_sub = os.path.relpath(output_path, os.getcwd()).replace('\\', '/')

cmd = [
    'ffmpeg', '-i', str(test_video),
    '-ss', '5.0', '-t', '15.0',
    '-vf', f'subtitles={rel_sub}',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-c:a', 'copy', '-y', str(clip_path)
]

r = subprocess.run(cmd, capture_output=True, timeout=60)
if clip_path.exists():
    print(f"   SUCCESS! {clip_path.stat().st_size/1024/1024:.2f} MB")
    print(f"\n   Path: {clip_path.absolute()}")
    print("\n   Open and check: words sync to speech?")
else:
    print(f"   FAILED: {r.stderr.decode()[:300]}")
