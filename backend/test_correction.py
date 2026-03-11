"""
Test GPT correction - show before/after for each segment
"""
import sys, asyncio, json
from pathlib import Path
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from services.transcription import run_whisper_transcribe
from services.ai_engine import fix_segments_with_openai

test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")

print("Transcribing...")
result = run_whisper_transcribe(str(test_video), word_timestamps=True)
segments = result.get('segments', [])

print("\n=== BEFORE CORRECTION ===")
for i, seg in enumerate(segments, 1):
    print(f"\nSeg {i}: {seg['text'].strip()}")

print("\n\nRunning GPT-4o correction...")
asyncio.run(fix_segments_with_openai(segments))

print("\n=== AFTER CORRECTION ===")
for i, seg in enumerate(segments, 1):
    print(f"\nSeg {i}: {seg['text'].strip()}")

# Save AFTER correction with word-level data
data_after = {'segments': []}
for s in segments:
    data_after['segments'].append({
        'text': s['text'],
        'words': [{'word': w['word'], 'start': w['start'], 'end': w['end'], 'filler': w.get('_filler', False)} for w in s.get('words', [])]
    })
Path('transcript_corrected.json').write_text(
    json.dumps(data_after, ensure_ascii=False, indent=2), encoding='utf-8'
)
print("\nSaved to transcript_corrected.json - check word-level changes!")
