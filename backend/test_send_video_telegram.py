"""
Test sending video file directly to Telegram
Best solution for mobile access!
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

# Check if we have a test video
test_video = Path("clips/test_clip_645a3ffa.mp4")

if not test_video.exists():
    print("Test video not found. Creating from uploaded video...")
    uploaded = Path("uploads/645a3ffa-e633-4e19-8472-b0cb5ba4d99c.mp4")
    if uploaded.exists():
        import shutil
        test_video.parent.mkdir(exist_ok=True)
        shutil.copy2(uploaded, test_video)
        print(f"Created: {test_video}")
    else:
        print("No video available for testing")
        exit(1)

file_size_mb = test_video.stat().st_size / 1024 / 1024

print(f"\nVideo Info:")
print(f"  Path: {test_video}")
print(f"  Size: {file_size_mb:.2f} MB")

if file_size_mb > 50:
    print(f"\nWARNING: Video is {file_size_mb:.1f}MB (Telegram limit: 50MB)")
    print("Need to compress or use cloud storage for large files")
    exit(1)

# Build caption
caption = f"""VIDEO READY!

Title: Test Clip from IMG_2351
Viral Score: 9.2/10
Duration: 15s
Size: {file_size_mb:.1f}MB

#viral #shorts #test

Ready to upload to YouTube!
"""

print("\nSending video to Telegram...")
print("(This may take 10-30 seconds depending on file size)")

# Import after path setup
from services.telegram_notifier import send_video_file

success = send_video_file(
    video_path=str(test_video),
    caption=caption
)

if success:
    print("\nSUCCESS!")
    print("Check your Telegram - video should be there!")
    print("\nYou can now:")
    print("  - Watch it directly in Telegram")
    print("  - Download to phone with one tap")
    print("  - Share to Instagram/TikTok/YouTube")
    print("  - No need for server access!")
else:
    print("\nFailed to send video")
    print("Check that TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env")
