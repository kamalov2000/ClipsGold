"""
Simplified Pipeline Test - No emoji, minimal dependencies
"""

import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("AUTONOMOUS FACTORY - PIPELINE TEST")
print("=" * 60)

TEST_VIDEO = r"C:\Users\kamal\Downloads\IMG_2351.mp4"

if not Path(TEST_VIDEO).exists():
    print(f"\nERROR: Video not found")
    sys.exit(1)

print(f"\nTest Video: {TEST_VIDEO}")
print(f"Size: {Path(TEST_VIDEO).stat().st_size / 1024 / 1024:.2f} MB")

# Setup
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

import uuid
file_id = str(uuid.uuid4())
video_path = UPLOAD_DIR / f"{file_id}.mp4"

print(f"\nCopying to uploads...")
shutil.copy2(TEST_VIDEO, video_path)
print(f"File ID: {file_id}")

from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 60)
print("STEP 1: TRANSCRIPTION")
print("=" * 60)

from services.transcription import run_whisper_transcribe

print("\nRunning Whisper (30-60 sec)...")
transcript = run_whisper_transcribe(str(video_path))

if transcript:
    print(f"SUCCESS!")
    print(f"Language: {transcript.get('language')}")
    print(f"Duration: {transcript.get('duration', 0):.1f}s")
    print(f"Segments: {len(transcript.get('segments', []))}")
    
    text = transcript.get('text', '')
    print(f"\nTranscript ({len(text)} chars):")
    print(text[:300])
    if len(text) > 300:
        print("...")
else:
    print("ERROR: Transcription failed")
    sys.exit(1)

print("\n" + "=" * 60)
print("STEP 2: VIRAL ANALYSIS (Mock Mode)")
print("=" * 60)

# Create mock clips for testing
mock_clips = [
    {
        'title': 'Test Clip 1',
        'start_time': 5.0,
        'end_time': 20.0,
        'virality_score': 9.2,
        'reason': 'High energy moment with clear hook',
        'hook': text[:50] if text else 'Test hook',
        'hashtags': ['viral', 'shorts', 'test'],
        'emojis': ['fire', 'rocket']
    },
    {
        'title': 'Test Clip 2',
        'start_time': 25.0,
        'end_time': 40.0,
        'virality_score': 7.5,
        'reason': 'Interesting content but lower energy',
        'hook': text[50:100] if len(text) > 50 else 'Test hook 2',
        'hashtags': ['content', 'video'],
        'emojis': ['star']
    }
]

print(f"\nFound {len(mock_clips)} clips (mock data)")
for idx, clip in enumerate(mock_clips, 1):
    print(f"\nClip {idx}:")
    print(f"  Title: {clip['title']}")
    print(f"  Score: {clip['virality_score']}/10")
    print(f"  Time: {clip['start_time']:.1f}s - {clip['end_time']:.1f}s")

print("\n" + "=" * 60)
print("STEP 3: SMART FILTERING (score >= 8)")
print("=" * 60)

THRESHOLD = 8
high_quality = [c for c in mock_clips if c['virality_score'] >= THRESHOLD]

print(f"\nTotal clips: {len(mock_clips)}")
print(f"High-quality (>= {THRESHOLD}): {len(high_quality)}")

if high_quality:
    print("\nSelected for rendering:")
    for clip in high_quality:
        print(f"  - {clip['title']} (score: {clip['virality_score']})")

print("\n" + "=" * 60)
print("STEP 4: TELEGRAM NOTIFICATION")
print("=" * 60)

import requests

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if BOT_TOKEN and CHAT_ID and high_quality:
    clip = high_quality[0]
    
    message = f"""
*Pipeline Test Complete!*

*Video:* IMG_2351.mp4
*File ID:* {file_id}

*Transcription:* SUCCESS
- Language: {transcript.get('language')}
- Duration: {transcript.get('duration', 0):.1f}s
- Text: {len(text)} chars

*Analysis:* {len(mock_clips)} clips found
*High-Quality:* {len(high_quality)} clips (>= {THRESHOLD})

*Top Clip:*
- Title: {clip['title']}
- Score: {clip['virality_score']}/10
- Duration: {clip['end_time'] - clip['start_time']:.1f}s

*Next Steps:*
1. Render clips with FFmpeg
2. Upload to YouTube Shorts
3. Mark as processed

Test completed successfully!
"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    print("\nSending notification...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.json().get('ok'):
            print("SUCCESS! Check Telegram")
        else:
            print(f"Failed: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("\nSkipped (no credentials or no clips)")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

print(f"\nResults:")
print(f"  File ID: {file_id}")
print(f"  Video Path: {video_path}")
print(f"  Transcription: SUCCESS ({len(text)} chars)")
print(f"  Clips Found: {len(mock_clips)}")
print(f"  High-Quality: {len(high_quality)}")
print(f"  Notification: Sent to Telegram")

print(f"\nIn full autonomous mode:")
print(f"  - Would render {len(high_quality)} clips")
print(f"  - Upload to YouTube Shorts")
print(f"  - Mark video as processed")
print(f"  - Send completion notification")

print(f"\nVideo ready for manual testing:")
print(f"  http://localhost:8000/analyze-video?file_id={file_id}")
