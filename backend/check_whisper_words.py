"""
Check if Whisper returns word-level timestamps
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from services.transcription import run_whisper_transcribe

test_video = Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4")

print("Transcribing with word timestamps...")
result = run_whisper_transcribe(str(test_video), word_timestamps=True)

print(f"\nSegments: {len(result.get('segments', []))}")

for i, seg in enumerate(result.get('segments', [])[:2], 1):
    print(f"\n--- Segment {i} ---")
    print(f"Time: {seg['start']:.1f}-{seg['end']:.1f}s")
    print(f"Text: {seg['text']}")
    
    words = seg.get('words', [])
    print(f"Words: {len(words)}")
    
    if words:
        print("\nFirst 5 words with timestamps:")
        for w in words[:5]:
            print(f"  {w.get('start', 0):.2f}-{w.get('end', 0):.2f}s: '{w.get('word', '')}'")
    else:
        print("  NO WORD TIMESTAMPS!")

# Save full result for inspection
output_file = Path("outputs/whisper_debug.json")
output_file.parent.mkdir(exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\nFull result saved to: {output_file}")
