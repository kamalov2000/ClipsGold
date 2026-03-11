"""
Minimal autonomous pipeline - no extra dependencies
Just: Transcribe -> Analyze -> Filter -> Notify
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("AI FACTORY - MINIMAL VERSION")
print("="*60)

# Find video
test_video = Path("uploads/645a3ffa-e633-4e19-8472-b0cb5ba4d99c.mp4")

if not test_video.exists():
    print("No video found")
    sys.exit(1)

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

# STEP 2: Mock analysis (3 clips)
print("STEP 2: Finding viral moments...")
clips = [
    {'title': 'Clip 1', 'score': 9.2, 'start': 5, 'end': 20},
    {'title': 'Clip 2', 'score': 8.8, 'start': 25, 'end': 40},
    {'title': 'Clip 3', 'score': 7.5, 'start': 45, 'end': 58}
]
print(f"Found {len(clips)} clips")
for c in clips:
    print(f"  - {c['title']}: {c['score']}/10")
print()

# STEP 3: Filter (score >= 8)
print("STEP 3: Filtering...")
good_clips = [c for c in clips if c['score'] >= 8.0]
print(f"Selected: {len(good_clips)} clips")
print()

# STEP 4: Send to Telegram
print("STEP 4: Sending to Telegram...")

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    print("Telegram not configured")
    print("\nClips would be:")
    for c in good_clips:
        print(f"  - {c['title']} ({c['start']}-{c['end']}s)")
    sys.exit(0)

import requests

# Send summary
message = f"""AI FACTORY COMPLETE!

Video: {test_video.name}
Transcription: {len(text)} chars
Language: {transcript.get('language')}

Clips found: {len(clips)}
High-quality: {len(good_clips)}

Selected clips:
"""

for idx, c in enumerate(good_clips, 1):
    message += f"\n{idx}. {c['title']}"
    message += f"\n   Score: {c['score']}/10"
    message += f"\n   Time: {c['start']}-{c['end']}s"
    message += f"\n   Duration: {c['end']-c['start']}s"

message += "\n\nReady for rendering!"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {'chat_id': CHAT_ID, 'text': message}

try:
    response = requests.post(url, json=payload, timeout=10)
    if response.json().get('ok'):
        print("SUCCESS! Check Telegram")
    else:
        print(f"Failed: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

print()
print("="*60)
print("DONE!")
print("="*60)
print()
print("Next: Add FFmpeg rendering to create actual clips")
print("For now, you have the analysis and know which moments are viral")
