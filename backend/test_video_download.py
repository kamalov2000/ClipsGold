"""
Test video download notification with real download link
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Simulate rendered clip
CLIPS_DIR = Path("clips")
CLIPS_DIR.mkdir(exist_ok=True)

# Create a test file (or use existing)
test_clip = CLIPS_DIR / "test_clip_645a3ffa.mp4"

# Check if we have the uploaded video to use as test
uploaded_video = Path("uploads/645a3ffa-e633-4e19-8472-b0cb5ba4d99c.mp4")

if uploaded_video.exists() and not test_clip.exists():
    print(f"Creating test clip from uploaded video...")
    import shutil
    shutil.copy2(uploaded_video, test_clip)
    print(f"Test clip created: {test_clip}")
elif test_clip.exists():
    print(f"Test clip already exists: {test_clip}")
else:
    print("No video available for testing")
    exit(0)

# Get file info
file_size_mb = test_clip.stat().st_size / 1024 / 1024

# Build download URL
# In production, this would be your public server URL
# For local testing, use localhost
SERVER_URL = "http://localhost:8000"
download_url = f"{SERVER_URL}/clips/{test_clip.name}"

print(f"\nClip Info:")
print(f"  Filename: {test_clip.name}")
print(f"  Size: {file_size_mb:.2f} MB")
print(f"  Download URL: {download_url}")

# Send Telegram notification with download link
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    print("\nTelegram not configured - skipping notification")
    print(f"\nTo download the video:")
    print(f"1. Start backend: uvicorn main:app --reload")
    print(f"2. Open in browser: {download_url}")
    exit(0)

message = f"""VIDEO READY!

Title: Test Clip from IMG_2351

Viral Score: 9.2/10
Duration: 15.0s
Size: {file_size_mb:.1f} MB
Niche: test

Hashtags:
#viral #shorts #test

DOWNLOAD VIDEO:
{download_url}

Filename: {test_clip.name}

Ready to upload to YouTube Shorts / TikTok / Instagram Reels

---
NOTE: Start backend first with:
uvicorn main:app --reload

Then click the download link above!
"""

print("\nSending Telegram notification with download link...")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    'chat_id': CHAT_ID,
    'text': message
}

try:
    response = requests.post(url, json=payload, timeout=10)
    if response.json().get('ok'):
        print("SUCCESS! Check Telegram for download link")
        print(f"\nThe download link is: {download_url}")
        print(f"\nTo download:")
        print(f"1. Start backend: uvicorn main:app --reload")
        print(f"2. Click link in Telegram")
        print(f"3. Or open in browser: {download_url}")
    else:
        print(f"Failed: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
