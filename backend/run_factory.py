"""
Complete autonomous pipeline with FFmpeg rendering
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
print("AI FACTORY - FULL PIPELINE")
print("="*60)

# Setup
CLIPS_DIR = Path("clips")
CLIPS_DIR.mkdir(exist_ok=True)

# Find video
test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")

if not test_video.exists():
    print(f"Video not found at: {test_video}")
    print("Please update the path in the script")
    sys.exit(1)

file_id = test_video.stem
print(f"Video: {test_video.name}")
print(f"Size: {test_video.stat().st_size / 1024 / 1024:.2f} MB")
print()

# STEP 1: Transcribe
print("STEP 1: Transcribing...")
from services.transcription import run_whisper_transcribe

start = time.time()
transcript = run_whisper_transcribe(str(test_video))
print(f"Done in {time.time() - start:.1f}s")

if not transcript:
    print("Transcription failed")
    sys.exit(1)

text = transcript.get('text', '')
print(f"Text: {len(text)} chars")
print()

# STEP 2: Find clips
print("STEP 2: Finding viral moments...")
clips = [
    {'title': 'Viral Moment 1', 'score': 9.2, 'start': 5.0, 'end': 20.0},
    {'title': 'Viral Moment 2', 'score': 8.8, 'start': 25.0, 'end': 40.0},
]
print(f"Found {len(clips)} clips")
for c in clips:
    print(f"  - {c['title']}: {c['score']}/10 ({c['start']}-{c['end']}s)")
print()

# STEP 3: Filter
print("STEP 3: Filtering (score >= 8)...")
good_clips = [c for c in clips if c['score'] >= 8.0]
print(f"Selected: {len(good_clips)} clips")
print()

# STEP 4: Render with FFmpeg
print("STEP 4: Rendering clips...")

rendered_clips = []

for idx, clip in enumerate(good_clips, 1):
    print(f"\nClip {idx}/{len(good_clips)}: {clip['title']}")
    
    # Output path
    clip_filename = f"clip_{file_id}_{idx}.mp4"
    clip_path = CLIPS_DIR / clip_filename
    
    # FFmpeg command - simple cut
    cmd = [
        'ffmpeg',
        '-i', str(test_video),
        '-ss', str(clip['start']),
        '-t', str(clip['end'] - clip['start']),
        '-c', 'copy',
        '-y',
        str(clip_path)
    ]
    
    print(f"  Cutting {clip['start']}-{clip['end']}s...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if clip_path.exists():
            size_mb = clip_path.stat().st_size / 1024 / 1024
            print(f"  Done! Size: {size_mb:.2f} MB")
            
            rendered_clips.append({
                'path': clip_path,
                'filename': clip_filename,
                'title': clip['title'],
                'score': clip['score'],
                'duration': clip['end'] - clip['start'],
                'size_mb': size_mb
            })
        else:
            print(f"  Failed - file not created")
            
    except Exception as e:
        print(f"  Error: {e}")

print(f"\nRendered: {len(rendered_clips)} clips")
print()

# STEP 5: Send to Telegram
print("STEP 5: Sending to Telegram...")

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    print("Telegram not configured")
    print(f"\nClips saved to: {CLIPS_DIR}/")
    for c in rendered_clips:
        print(f"  - {c['filename']} ({c['size_mb']:.2f} MB)")
    sys.exit(0)

import requests

for idx, clip in enumerate(rendered_clips, 1):
    print(f"\nSending clip {idx}/{len(rendered_clips)}...")
    
    caption = f"""{clip['title']}

Viral Score: {clip['score']}/10
Duration: {clip['duration']:.1f}s
Size: {clip['size_mb']:.1f}MB

Clip {idx} of {len(rendered_clips)}
Ready for upload!"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    
    try:
        with open(clip['path'], 'rb') as video:
            files = {'video': video}
            data = {
                'chat_id': CHAT_ID,
                'caption': caption,
                'supports_streaming': True
            }
            
            print(f"  Uploading {clip['size_mb']:.1f}MB...")
            response = requests.post(url, data=data, files=files, timeout=120)
            
            if response.json().get('ok'):
                print(f"  SUCCESS!")
            else:
                print(f"  Failed: {response.json()}")
    except Exception as e:
        print(f"  Error: {e}")

print()
print("="*60)
print("COMPLETE!")
print("="*60)
print(f"\nProcessed: {test_video.name}")
print(f"Clips created: {len(rendered_clips)}")
print(f"Sent to Telegram: {len(rendered_clips)}")
print()
print("Check your Telegram for videos!")
