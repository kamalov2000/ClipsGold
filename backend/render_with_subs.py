"""
Render clips with Hormozi-style subtitles
Simplified version without heavy dependencies
"""

import os
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("AI FACTORY - SUBTITLES ENABLED")
print("="*60)

# Setup
CLIPS_DIR = Path("clips")
OUTPUT_DIR = Path("outputs")
CLIPS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Video
test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")

if not test_video.exists():
    print(f"Video not found: {test_video}")
    sys.exit(1)

file_id = test_video.stem
print(f"Video: {test_video.name}")
print()

# STEP 1: Transcribe
print("STEP 1: Transcribing...")
from services.transcription import run_whisper_transcribe

start = time.time()
transcript = run_whisper_transcribe(str(test_video))
print(f"Done in {time.time() - start:.1f}s")

if not transcript:
    print("Failed")
    sys.exit(1)

segments = transcript.get('segments', [])
print(f"Segments: {len(segments)}")
print()

# STEP 2: Clips
print("STEP 2: Viral moments...")
clips = [
    {'title': 'Viral Moment 1', 'score': 9.2, 'start': 5.0, 'end': 20.0},
]
print(f"Selected: {len(clips)} clips")
print()

# STEP 3: Render with subtitles
print("STEP 3: Rendering with subtitles...")

from subtitle_generator_v2 import create_subtitle_generator

rendered_clips = []

for idx, clip in enumerate(clips, 1):
    print(f"\nClip {idx}: {clip['title']}")
    
    clip_filename = f"clip_subs_{idx}.mp4"
    clip_path = CLIPS_DIR / clip_filename
    
    # Generate subtitles
    print("  Creating subtitles...")
    subtitle_gen = create_subtitle_generator()
    
    # Filter segments for this clip
    clip_segments = [
        s for s in segments
        if s['start'] >= clip['start'] and s['end'] <= clip['end']
    ]
    
    subtitle_path = OUTPUT_DIR / f"clip{idx}.ass"
    
    try:
        subtitle_gen.generate_ass_from_transcription(
            transcription_data={'segments': clip_segments},
            output_path=subtitle_path,
            clip_start_time=clip['start'],
            clip_end_time=clip['end'],
            platform='tiktok',
            subtitle_style='hormozi'
        )
        print(f"  Subtitles: OK")
    except Exception as e:
        print(f"  Subtitle error: {e}")
        subtitle_path = None
    
    # Render with FFmpeg
    print(f"  Rendering video...")
    
    # Prepare subtitle path for FFmpeg (Windows path escaping)
    if subtitle_path and subtitle_path.exists():
        abs_subtitle_path = str(subtitle_path.resolve()).replace('\\', '/').replace(':', '\\:')
        subtitle_filter = f"subtitles={abs_subtitle_path}"
    else:
        subtitle_filter = None
    
    # FFmpeg command
    cmd = [
        'ffmpeg',
        '-i', str(test_video),
        '-ss', str(clip['start']),
        '-t', str(clip['end'] - clip['start']),
    ]
    
    # Add subtitle filter if available
    if subtitle_filter:
        cmd.extend(['-vf', subtitle_filter])
        cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-threads', '0'])
        cmd.extend(['-movflags', '+faststart'])
    else:
        cmd.extend(['-c', 'copy'])
    
    cmd.extend(['-c:a', 'copy', '-y', str(clip_path)])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if clip_path.exists():
            size_mb = clip_path.stat().st_size / 1024 / 1024
            print(f"  Done! {size_mb:.2f} MB")
            
            rendered_clips.append({
                'path': clip_path,
                'filename': clip_filename,
                'title': clip['title'],
                'score': clip['score'],
                'size_mb': size_mb
            })
        else:
            print(f"  Failed")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            
    except Exception as e:
        print(f"  Error: {e}")

print(f"\nRendered: {len(rendered_clips)} clips with subtitles")
print()

# STEP 4: Show results
print("STEP 4: Clips saved!")

print()
print("="*60)
print("COMPLETE!")
print("="*60)
print(f"\nClips saved to: {CLIPS_DIR.absolute()}/")
print()
for c in rendered_clips:
    print(f"  {c['filename']}")
    print(f"    Size: {c['size_mb']:.2f} MB")
    print(f"    Score: {c['score']}/10")
    print(f"    Path: {c['path'].absolute()}")
    print()
print("Open the clip to see Hormozi-style subtitles!")
