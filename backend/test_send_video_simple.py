"""
Send video directly to Telegram - simplified version
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Check video
test_video = Path("clips/test_clip_645a3ffa.mp4")

if not test_video.exists():
    print("Video not found")
    exit(1)

file_size_mb = test_video.stat().st_size / 1024 / 1024

print(f"Video: {test_video}")
print(f"Size: {file_size_mb:.2f} MB")

if file_size_mb > 50:
    print(f"ERROR: Video too large ({file_size_mb:.1f}MB > 50MB Telegram limit)")
    exit(1)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    print("Telegram credentials not set")
    exit(1)

caption = f"""VIDEO READY!

Title: Test Clip
Viral Score: 9.2/10
Duration: 15s
Size: {file_size_mb:.1f}MB

#viral #shorts #test

Watch directly in Telegram or download to phone!
"""

print("\nSending video to Telegram...")
print("(May take 10-30 seconds...)")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

try:
    with open(test_video, 'rb') as video:
        files = {'video': video}
        data = {
            'chat_id': CHAT_ID,
            'caption': caption,
            'supports_streaming': True
        }
        
        response = requests.post(url, data=data, files=files, timeout=120)
        response.raise_for_status()
        
        if response.json().get('ok'):
            print("\nSUCCESS!")
            print("\nCheck your Telegram!")
            print("\nYou can now:")
            print("  - Watch video directly in Telegram")
            print("  - Download to phone with one tap")
            print("  - Share to Instagram/TikTok/YouTube")
            print("  - Works on mobile without server access!")
        else:
            print(f"Failed: {response.json()}")
            
except Exception as e:
    print(f"Error: {e}")
