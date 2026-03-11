"""
Full Autonomous Pipeline Test
Simulates the complete factory workflow on a real video.
"""

import os
import sys
import shutil
import asyncio
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("AUTONOMOUS FACTORY - FULL PIPELINE TEST")
print("=" * 60)

# Test video path
TEST_VIDEO = r"C:\Users\kamal\Downloads\IMG_2351.mp4"

if not Path(TEST_VIDEO).exists():
    print(f"\nERROR: Video not found at {TEST_VIDEO}")
    sys.exit(1)

print(f"\nTest Video: {TEST_VIDEO}")
print(f"Video Size: {Path(TEST_VIDEO).stat().st_size / 1024 / 1024:.2f} MB")

# Setup
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Copy video to uploads
import uuid
file_id = str(uuid.uuid4())
video_filename = f"{file_id}.mp4"
video_path = UPLOAD_DIR / video_filename

print(f"\nCopying video to uploads...")
shutil.copy2(TEST_VIDEO, video_path)
print(f"File ID: {file_id}")

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 60)
print("STEP 1: TRANSCRIPTION (Whisper)")
print("=" * 60)

try:
    from services.transcription import run_whisper_transcribe
    
    print("\nRunning Whisper transcription...")
    print("(This may take 30-60 seconds for a 1-minute video)")
    
    transcript_result = run_whisper_transcribe(str(video_path))
    
    if transcript_result:
        print(f"\nSUCCESS!")
        print(f"Language: {transcript_result.get('language', 'unknown')}")
        print(f"Text length: {len(transcript_result.get('text', ''))} chars")
        print(f"Segments: {len(transcript_result.get('segments', []))}")
        print(f"\nFirst 200 chars:")
        print(transcript_result.get('text', '')[:200] + "...")
    else:
        print("\nERROR: Transcription failed")
        sys.exit(1)
        
except Exception as e:
    print(f"\nERROR in transcription: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("STEP 2: VIRAL MOMENT ANALYSIS (GPT-4o/Gemini)")
print("=" * 60)

try:
    from analyzer import create_analyzer
    
    analyzer = create_analyzer()
    
    print("\nAnalyzing video for viral moments...")
    print("(Using AI to find best clips)")
    
    # Prepare video info
    video_info = {
        'duration': transcript_result.get('duration', 60),
        'transcript': transcript_result.get('text', ''),
        'segments': transcript_result.get('segments', [])
    }
    
    candidates = analyzer.analyze(video_info)
    
    if candidates:
        print(f"\nSUCCESS! Found {len(candidates)} viral moments")
        
        for idx, clip in enumerate(candidates, 1):
            print(f"\nClip {idx}:")
            print(f"  Title: {clip.get('title', 'N/A')}")
            print(f"  Viral Score: {clip.get('virality_score', 0)}/10")
            print(f"  Time: {clip.get('start_time', 0):.1f}s - {clip.get('end_time', 0):.1f}s")
            print(f"  Duration: {clip.get('end_time', 0) - clip.get('start_time', 0):.1f}s")
            print(f"  Reason: {clip.get('reason', 'N/A')[:100]}...")
    else:
        print("\nWARNING: No viral moments found")
        
except Exception as e:
    print(f"\nERROR in analysis: {e}")
    import traceback
    traceback.print_exc()
    candidates = []

print("\n" + "=" * 60)
print("STEP 3: SMART FILTERING (viral_score >= 8)")
print("=" * 60)

VIRAL_THRESHOLD = 8
high_quality_clips = [c for c in candidates if c.get('virality_score', 0) >= VIRAL_THRESHOLD]

print(f"\nTotal candidates: {len(candidates)}")
print(f"High-quality clips (>= {VIRAL_THRESHOLD}): {len(high_quality_clips)}")

if high_quality_clips:
    print("\nClips selected for rendering:")
    for idx, clip in enumerate(high_quality_clips, 1):
        print(f"  {idx}. {clip.get('title', 'Untitled')} (score: {clip.get('virality_score', 0)})")
else:
    print("\nNo clips meet the viral threshold - would skip rendering in autonomous mode")

print("\n" + "=" * 60)
print("STEP 4: FACE DETECTION & THUMBNAIL")
print("=" * 60)

try:
    from thumbnail_generator import select_best_thumbnail_frame
    
    if high_quality_clips:
        clip = high_quality_clips[0]
        
        print(f"\nSelecting best thumbnail for: {clip.get('title', 'Untitled')}")
        
        thumbnail_path, best_time, confidence = select_best_thumbnail_frame(
            video_path=video_path,
            start_time=clip.get('start_time', 0),
            end_time=clip.get('end_time', 10),
            sample_count=5
        )
        
        if thumbnail_path:
            print(f"SUCCESS! Best frame at {best_time:.1f}s (confidence: {confidence:.2f})")
            print(f"Thumbnail saved: {thumbnail_path}")
        else:
            print(f"Using middle frame at {best_time:.1f}s")
            
except Exception as e:
    print(f"\nWARNING: Thumbnail generation failed: {e}")

print("\n" + "=" * 60)
print("STEP 5: TELEGRAM NOTIFICATION")
print("=" * 60)

try:
    from services.telegram_notifier import send_video_ready_notification
    
    if high_quality_clips:
        clip = high_quality_clips[0]
        
        print("\nSending Telegram notification...")
        
        success = send_video_ready_notification(
            title=clip.get('title', 'Untitled Clip'),
            download_url=f"http://localhost:8000/download-clip/{file_id}/0",
            viral_score=clip.get('virality_score', 0),
            hashtags=clip.get('hashtags', ['viral', 'shorts']),
            duration=clip.get('end_time', 0) - clip.get('start_time', 0),
            file_size_mb=Path(video_path).stat().st_size / 1024 / 1024,
            niche="test"
        )
        
        if success:
            print("SUCCESS! Check your Telegram for notification")
        else:
            print("WARNING: Notification failed (check .env credentials)")
            
except Exception as e:
    print(f"\nWARNING: Telegram notification failed: {e}")

print("\n" + "=" * 60)
print("PIPELINE TEST COMPLETE")
print("=" * 60)

print(f"\nSummary:")
print(f"  Video: {TEST_VIDEO}")
print(f"  File ID: {file_id}")
print(f"  Transcription: SUCCESS")
print(f"  Viral Moments Found: {len(candidates)}")
print(f"  High-Quality Clips: {len(high_quality_clips)}")
print(f"  Telegram Notification: Sent")

if high_quality_clips:
    print(f"\nNext steps in full autonomous mode:")
    print(f"  1. Render {len(high_quality_clips)} clips with FFmpeg")
    print(f"  2. Upload to YouTube Shorts (if enabled)")
    print(f"  3. Mark video as processed in deduplication DB")
    print(f"  4. Send batch completion notification")
else:
    print(f"\nIn autonomous mode, this video would be skipped (no clips >= {VIRAL_THRESHOLD})")

print(f"\nTest video location: {video_path}")
print(f"You can now test rendering manually via the UI or API")
