"""
Full pipeline with Hormozi-style subtitles
"""

import os
import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("AI FACTORY - WITH SUBTITLES")
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
segments = transcript.get('segments', [])
print(f"Text: {len(text)} chars")
print(f"Segments: {len(segments)}")
print()

# STEP 2: Find clips
print("STEP 2: Finding viral moments...")
clips = [
    {
        'title': 'Viral Moment 1',
        'score': 9.2,
        'start': 5.0,
        'end': 20.0,
        'transcript_text': text[:200] if text else ''
    },
]
print(f"Found {len(clips)} clips")
for c in clips:
    print(f"  - {c['title']}: {c['score']}/10 ({c['start']}-{c['end']}s)")
print()

# STEP 3: Render with subtitles
print("STEP 3: Rendering with subtitles...")

from subtitle_generator_v2 import create_subtitle_generator
from main import cut_video_segment_enhanced

rendered_clips = []

for idx, clip in enumerate(clips, 1):
    print(f"\nClip {idx}/{len(clips)}: {clip['title']}")
    
    clip_filename = f"clip_{file_id}_{idx}_subs.mp4"
    clip_path = CLIPS_DIR / clip_filename
    
    # Generate subtitles
    print("  Generating subtitles...")
    subtitle_gen = create_subtitle_generator()
    
    # Filter segments for this clip
    clip_segments = [
        s for s in segments
        if s['start'] >= clip['start'] and s['end'] <= clip['end']
    ]
    
    if not clip_segments:
        print("  No segments in this clip - using full transcript")
        clip_segments = segments
    
    # Generate subtitle file
    subtitle_path = OUTPUT_DIR / f"{file_id}_clip{idx}.ass"
    
    try:
        subtitle_gen.generate_subtitles(
            segments=clip_segments,
            output_path=str(subtitle_path),
            clip_start_time=clip['start'],
            platform='tiktok'
        )
        print(f"  Subtitles: {subtitle_path.name}")
    except Exception as e:
        print(f"  Subtitle generation failed: {e}")
        subtitle_path = None
    
    # Render with FFmpeg
    print(f"  Rendering {clip['start']}-{clip['end']}s...")
    
    try:
        # Use async render function
        async def render():
            await cut_video_segment_enhanced(
                input_path=test_video,
                output_path=clip_path,
                start_time=clip['start'],
                end_time=clip['end'],
                subtitle_path=subtitle_path if subtitle_path and subtitle_path.exists() else None,
                platform='tiktok',
                zoom_factor=1.2,
                manual_crop_x=None,
                manual_crop_y=None,
                task_id=None
            )
        
        asyncio.run(render())
        
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
        print(f"  Render error: {e}")
        import traceback
        traceback.print_exc()

print(f"\nRendered: {len(rendered_clips)} clips")
print()

# STEP 4: Send to Telegram
print("STEP 4: Sending to Telegram...")

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

WITH HORMOZI-STYLE SUBTITLES!

Clip {idx} of {len(rendered_clips)}
Ready for TikTok/YouTube Shorts!"""
    
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
            response = requests.post(url, data=data, files=files, timeout=180)
            
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
print(f"Clips with subtitles: {len(rendered_clips)}")
print()
print("Check Telegram for videos with Hormozi-style subtitles!")
