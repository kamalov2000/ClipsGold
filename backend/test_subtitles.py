"""
Test subtitle generation with debug output
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("Testing subtitle generation...")

# Get transcript
from services.transcription import run_whisper_transcribe

test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")
print(f"\n1. Transcribing {test_video.name}...")

transcript = run_whisper_transcribe(str(test_video))
segments = transcript.get('segments', [])

print(f"   Segments: {len(segments)}")
for i, seg in enumerate(segments[:3], 1):
    print(f"   {i}. {seg['start']:.1f}-{seg['end']:.1f}s: {seg['text'][:50]}...")

# Generate subtitles
print("\n2. Generating subtitle file...")

from subtitle_generator_v2 import create_subtitle_generator

subtitle_gen = create_subtitle_generator()
output_path = Path("outputs/test_subtitles.ass")
output_path.parent.mkdir(exist_ok=True)

try:
    result = subtitle_gen.generate_ass_from_transcription(
        transcription_data={'segments': segments},
        output_path=output_path,
        clip_start_time=5.0,
        clip_end_time=20.0,
        platform='tiktok',
        subtitle_style='hormozi'
    )
    
    if output_path.exists():
        size = output_path.stat().st_size
        print(f"   SUCCESS! File created: {size} bytes")
        print(f"   Path: {output_path.absolute()}")
        
        # Show first few lines
        print("\n3. Subtitle content preview:")
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:20]
            for line in lines:
                print(f"   {line.rstrip()}")
    else:
        print("   FAILED - file not created")
        
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n4. Testing FFmpeg subtitle rendering...")

import subprocess

clip_path = Path("clips/test_with_subs.mp4")
clip_path.parent.mkdir(exist_ok=True)

if output_path.exists():
    # Prepare subtitle path for FFmpeg
    import os
    rel_subtitle_path = os.path.relpath(output_path, os.getcwd())
    rel_subtitle_path = rel_subtitle_path.replace('\\', '/').replace(':', '\\:')
    
    print(f"   Subtitle path: {rel_subtitle_path}")
    
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
    
    print(f"   Running FFmpeg...")
    print(f"   Command: {' '.join(cmd[:10])}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if clip_path.exists():
            size_mb = clip_path.stat().st_size / 1024 / 1024
            print(f"   SUCCESS! Clip created: {size_mb:.2f} MB")
            print(f"   Path: {clip_path.absolute()}")
            print("\n   Open the clip to verify subtitles are visible!")
        else:
            print("   FAILED - clip not created")
            if result.stderr:
                print(f"   FFmpeg error: {result.stderr[:500]}")
    except Exception as e:
        print(f"   ERROR: {e}")
else:
    print("   Skipping FFmpeg - no subtitle file")

print("\nDone!")
