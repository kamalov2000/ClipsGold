import sys
from pathlib import Path
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from services.transcription import run_whisper_transcribe

result = run_whisper_transcribe(r'C:\Users\kamal\Downloads\IMG_2351.mp4', word_timestamps=True)
segments = result.get('segments', [])

out = []
out.append('=== FULL TRANSCRIPT ===')
for i, seg in enumerate(segments, 1):
    out.append(f"[{seg['start']:.1f}-{seg['end']:.1f}s] {seg['text'].strip()}")

out.append('')
out.append('=== WORD BY WORD ===')
for seg in segments:
    for w in seg.get('words', []):
        out.append(f"  {w['start']:.2f}-{w['end']:.2f}s: {w['word']}")

import json
output_file = Path('transcript_check.json')
data = {'segments': []}
for seg in segments:
    data['segments'].append({
        'start': seg['start'],
        'end': seg['end'],
        'text': seg['text'].strip(),
        'words': [{'start': w['start'], 'end': w['end'], 'word': w['word']} for w in seg.get('words', [])]
    })
output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Saved to: {output_file.absolute()}")
