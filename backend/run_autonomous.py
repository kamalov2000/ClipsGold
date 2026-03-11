"""
Autonomous AI Factory - Headless Mode
Runs completely in background without UI.

Pipeline:
1. Search for trending videos (yt-dlp)
2. Download video
3. Transcribe (Whisper)
4. Analyze for viral moments (GPT-4o/Gemini)
5. Filter clips (viral_score >= 8)
6. Render clips (FFmpeg)
7. Send to Telegram
8. Mark as processed

Usage:
    python run_autonomous.py
"""

import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("AUTONOMOUS AI FACTORY - HEADLESS MODE")
print("="*60)
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
UPLOAD_DIR = Path("uploads")
CLIPS_DIR = Path("clips")
UPLOAD_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)

VIRAL_THRESHOLD = 8  # Only render clips with score >= 8
MAX_CLIPS_PER_VIDEO = 3

# Check Telegram config
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    print("WARNING: Telegram not configured")
    print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env for notifications")
    print()

print("Configuration:")
print(f"  Viral Threshold: {VIRAL_THRESHOLD}")
print(f"  Max Clips per Video: {MAX_CLIPS_PER_VIDEO}")
print(f"  Telegram: {'Enabled' if BOT_TOKEN and CHAT_ID else 'Disabled'}")
print()

# ============================================================
# STEP 1: VIDEO DISCOVERY (Mock for now - can add yt-dlp search)
# ============================================================

print("="*60)
print("STEP 1: VIDEO DISCOVERY")
print("="*60)

# For testing, use the video we already have
test_video = Path("uploads/645a3ffa-e633-4e19-8472-b0cb5ba4d99c.mp4")

if test_video.exists():
    print(f"Using test video: {test_video.name}")
    video_path = test_video
    file_id = "645a3ffa-e633-4e19-8472-b0cb5ba4d99c"
else:
    print("No video found for processing")
    print("\nTo add videos:")
    print("  1. Place MP4 files in uploads/ directory")
    print("  2. Or implement yt-dlp search in auto_scout.py")
    sys.exit(0)

print(f"  File ID: {file_id}")
print(f"  Size: {video_path.stat().st_size / 1024 / 1024:.2f} MB")
print()

# ============================================================
# STEP 2: TRANSCRIPTION
# ============================================================

print("="*60)
print("STEP 2: TRANSCRIPTION (Whisper)")
print("="*60)

from services.transcription import run_whisper_transcribe

print("Running Whisper transcription...")
print("(This may take 30-60 seconds)")

start_time = time.time()
transcript = run_whisper_transcribe(str(video_path))
elapsed = time.time() - start_time

if transcript:
    text = transcript.get('text', '')
    print(f"SUCCESS! ({elapsed:.1f}s)")
    print(f"  Language: {transcript.get('language')}")
    print(f"  Duration: {transcript.get('duration', 0):.1f}s")
    print(f"  Text length: {len(text)} chars")
    print(f"  Segments: {len(transcript.get('segments', []))}")
else:
    print("FAILED: Transcription error")
    sys.exit(1)

print()

# ============================================================
# STEP 3: VIRAL MOMENT ANALYSIS
# ============================================================

print("="*60)
print("STEP 3: VIRAL MOMENT ANALYSIS")
print("="*60)

# For now, create mock clips
# In production, this would call GPT-4o/Gemini
print("Analyzing transcript for viral moments...")

mock_clips = [
    {
        'title': 'Viral Moment 1',
        'start_time': 5.0,
        'end_time': 20.0,
        'virality_score': 9.2,
        'reason': 'High energy hook with clear value proposition',
        'hook': text[:50] if text else 'Amazing moment',
        'hashtags': ['viral', 'shorts', 'trending'],
        'emojis': ['fire', 'rocket']
    },
    {
        'title': 'Viral Moment 2',
        'start_time': 25.0,
        'end_time': 40.0,
        'virality_score': 7.5,
        'reason': 'Good content but lower energy',
        'hook': text[50:100] if len(text) > 50 else 'Interesting point',
        'hashtags': ['content', 'video'],
        'emojis': ['star']
    },
    {
        'title': 'Viral Moment 3',
        'start_time': 45.0,
        'end_time': 58.0,
        'virality_score': 8.8,
        'reason': 'Strong emotional appeal',
        'hook': text[100:150] if len(text) > 100 else 'Key insight',
        'hashtags': ['motivation', 'inspiration'],
        'emojis': ['heart']
    }
]

print(f"Found {len(mock_clips)} potential clips")
for idx, clip in enumerate(mock_clips, 1):
    print(f"  {idx}. {clip['title']} - Score: {clip['virality_score']}/10")

print()

# ============================================================
# STEP 4: SMART FILTERING
# ============================================================

print("="*60)
print("STEP 4: SMART FILTERING")
print("="*60)

high_quality = [c for c in mock_clips if c['virality_score'] >= VIRAL_THRESHOLD]
high_quality = high_quality[:MAX_CLIPS_PER_VIDEO]

print(f"Filtering clips with score >= {VIRAL_THRESHOLD}")
print(f"  Total candidates: {len(mock_clips)}")
print(f"  High-quality clips: {len(high_quality)}")
print(f"  Selected for rendering: {len(high_quality)}")

if high_quality:
    print("\nSelected clips:")
    for idx, clip in enumerate(high_quality, 1):
        print(f"  {idx}. {clip['title']} (score: {clip['virality_score']})")
else:
    print("\nNo clips meet threshold - skipping this video")
    sys.exit(0)

print()

# ============================================================
# STEP 5: RENDERING (Simulated - would use FFmpeg in production)
# ============================================================

print("="*60)
print("STEP 5: RENDERING")
print("="*60)

print("NOTE: Full FFmpeg rendering requires:")
print("  - Subtitle generation")
print("  - Face detection")
print("  - Video effects")
print("  - Audio normalization")
print("\nFor this demo, we'll simulate the render process")
print()

rendered_clips = []

for idx, clip in enumerate(high_quality, 1):
    print(f"Rendering clip {idx}/{len(high_quality)}: {clip['title']}")
    
    # Simulate render time
    duration = clip['end_time'] - clip['start_time']
    print(f"  Duration: {duration:.1f}s")
    print(f"  Viral Score: {clip['virality_score']}/10")
    
    # In production, this would call FFmpeg
    # For demo, just copy the source video as "rendered" clip
    clip_filename = f"clip_{file_id}_{idx}.mp4"
    clip_path = CLIPS_DIR / clip_filename
    
    if not clip_path.exists():
        print(f"  Simulating render... (copying source)")
        shutil.copy2(video_path, clip_path)
    
    rendered_clips.append({
        'path': clip_path,
        'filename': clip_filename,
        'title': clip['title'],
        'score': clip['virality_score'],
        'duration': duration,
        'hashtags': clip['hashtags']
    })
    
    print(f"  Saved: {clip_filename}")
    print()

print(f"Rendering complete: {len(rendered_clips)} clips ready")
print()

# ============================================================
# STEP 6: TELEGRAM NOTIFICATION
# ============================================================

print("="*60)
print("STEP 6: TELEGRAM NOTIFICATION")
print("="*60)

if not BOT_TOKEN or not CHAT_ID:
    print("Telegram not configured - skipping notifications")
    print(f"\nClips saved to: {CLIPS_DIR}/")
    for clip in rendered_clips:
        print(f"  - {clip['filename']}")
else:
    import requests
    
    for idx, clip in enumerate(rendered_clips, 1):
        print(f"\nSending clip {idx}/{len(rendered_clips)} to Telegram...")
        
        file_size_mb = clip['path'].stat().st_size / 1024 / 1024
        
        # Build caption
        hashtags = ' '.join([f'#{tag}' for tag in clip['hashtags'][:5]])
        caption = f"""VIDEO READY!

Title: {clip['title']}
Viral Score: {clip['score']}/10
Duration: {clip['duration']:.1f}s
Size: {file_size_mb:.1f}MB

{hashtags}

Clip {idx} of {len(rendered_clips)} from autonomous factory
"""
        
        # Check file size
        if file_size_mb > 50:
            print(f"  WARNING: File too large ({file_size_mb:.1f}MB > 50MB)")
            print(f"  Sending text notification only")
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': CHAT_ID,
                'text': caption + f"\n\nFile too large for Telegram. Download from: clips/{clip['filename']}"
            }
            
            try:
                response = requests.post(url, json=payload, timeout=10)
                if response.json().get('ok'):
                    print(f"  Text notification sent")
                else:
                    print(f"  Failed: {response.json()}")
            except Exception as e:
                print(f"  Error: {e}")
        else:
            # Send video file
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
            
            try:
                with open(clip['path'], 'rb') as video:
                    files = {'video': video}
                    data = {
                        'chat_id': CHAT_ID,
                        'caption': caption[:1024],
                        'supports_streaming': True
                    }
                    
                    print(f"  Uploading video ({file_size_mb:.1f}MB)...")
                    response = requests.post(url, data=data, files=files, timeout=120)
                    
                    if response.json().get('ok'):
                        print(f"  SUCCESS! Video sent to Telegram")
                    else:
                        print(f"  Failed: {response.json()}")
            except Exception as e:
                print(f"  Error: {e}")

print()

# ============================================================
# STEP 7: COMPLETION SUMMARY
# ============================================================

print("="*60)
print("PIPELINE COMPLETE")
print("="*60)

print(f"\nProcessed: {video_path.name}")
print(f"Clips generated: {len(rendered_clips)}")
print(f"Clips location: {CLIPS_DIR}/")
print()

if BOT_TOKEN and CHAT_ID:
    print("Notifications sent to Telegram")
    print("Check your phone for videos!")
else:
    print("Clips saved locally:")
    for clip in rendered_clips:
        print(f"  - {clip['filename']}")

print()
print("="*60)
print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)
print()
print("Next steps:")
print("  1. Check Telegram for videos")
print("  2. Upload to YouTube/TikTok/Instagram")
print("  3. Add more videos to uploads/ for processing")
print()
print("To run continuously, add this script to scheduler")
print("Or use: services/autonomous_scheduler.py for full automation")
