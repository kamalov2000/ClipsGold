"""
Benchmark script: run on server via SSH.
Tests YouTube download + transcription pipeline end-to-end.
"""
import time
import json
import subprocess
import sys
import os
import uuid
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────
UPLOAD_DIR = Path("/opt/ClipsGold/backend/uploads")
OUTPUT_DIR = Path("/opt/ClipsGold/backend/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Test videos: well-known Russian YouTube content
TESTS = [
    {
        "label": "Test 1 (short ~10 min)",
        "url": "https://www.youtube.com/watch?v=wwbi9tNUoFk",  # Путин БРИКС 2024, 612s
        "expected_duration": "~10 min",
    },
    {
        "label": "Test 2 (long ~33 min)",
        "url": "https://www.youtube.com/watch?v=g6S8rLTVW44",  # Лекция Стэнфорд, 2009s
        "expected_duration": "~33 min",
    },
]

VENV_PYTHON = "/opt/ClipsGold/backend/venv/bin/python3.12"

results = []

for test in TESTS:
    print(f"\n{'='*60}")
    print(f"  {test['label']}")
    print(f"  URL: {test['url']}")
    print(f"{'='*60}")
    row = {"label": test["label"], "url": test["url"]}

    # ── Step 1: yt-dlp download ───────────────────────────────
    file_id = str(uuid.uuid4())[:8]
    out_path = UPLOAD_DIR / f"{file_id}.mp4"
    print(f"\n[1] Downloading with yt-dlp -> {out_path.name}")
    t0 = time.time()
    ytdlp_cmd = [
        "/opt/ClipsGold/backend/venv/bin/yt-dlp",
        "--js-runtimes", "node",
        "--no-playlist",
        "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-warnings",
        "-o", str(out_path),
        test["url"],
    ]
    r = subprocess.run(ytdlp_cmd, capture_output=True, text=True, timeout=600)
    t_download = time.time() - t0

    if r.returncode != 0 or not out_path.exists():
        print(f"  !! DOWNLOAD FAILED: {r.stderr[-300:]}")
        row["download_time"] = "FAILED"
        row["download_size_mb"] = 0
        row["video_duration"] = "?"
        row["transcription_time"] = "SKIPPED"
        row["transcript_sample"] = ""
        row["total_time"] = "FAILED"
        results.append(row)
        continue

    size_mb = out_path.stat().st_size / 1_048_576
    print(f"  -> Downloaded in {t_download:.1f}s  ({size_mb:.1f} MB)")
    row["download_time"] = f"{t_download:.1f}s"
    row["download_size_mb"] = f"{size_mb:.1f} MB"

    # Get video duration via ffprobe
    fp = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(out_path)],
        capture_output=True, text=True
    )
    try:
        dur = float(json.loads(fp.stdout)["format"]["duration"])
        dur_str = f"{int(dur//60)}m {int(dur%60)}s"
    except Exception:
        dur = 0
        dur_str = "?"
    print(f"  -> Video duration: {dur_str}")
    row["video_duration"] = dur_str

    # ── Step 2: Extract audio ─────────────────────────────────
    audio_path = OUTPUT_DIR / f"{file_id}_audio.wav"
    print(f"\n[2] Extracting audio...")
    t1 = time.time()
    subprocess.run([
        "ffmpeg", "-y", "-i", str(out_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(audio_path)
    ], capture_output=True, check=True)
    t_audio = time.time() - t1
    print(f"  -> Audio extracted in {t_audio:.1f}s")

    # ── Step 3: Transcribe with faster-whisper ────────────────
    print(f"\n[3] Transcribing with faster-whisper (medium, int8, CPU)...")
    bench_script = OUTPUT_DIR / f"{file_id}_bench_transcribe.py"
    bench_script.write_text(f"""
import time, json, sys
sys.path.insert(0, '/opt/ClipsGold/backend')
from services.transcription import run_whisper_transcribe
from pathlib import Path

t0 = time.time()
result = run_whisper_transcribe(Path('{audio_path}'), word_timestamps=True)
elapsed = time.time() - t0

out = {{
    'time': elapsed,
    'language': result.get('language','?'),
    'text': result.get('text',''),
    'segments': len(result.get('segments',[])),
}}
json.dump(out, open('{OUTPUT_DIR}/{file_id}_bench_result.json','w'), ensure_ascii=False)
print(f'DONE {{elapsed:.1f}}s')
""")

    t2 = time.time()
    r2 = subprocess.run(
        [VENV_PYTHON, str(bench_script)],
        capture_output=True, text=True, timeout=3600,
        cwd="/opt/ClipsGold/backend"
    )
    t_transcribe = time.time() - t2

    result_file = OUTPUT_DIR / f"{file_id}_bench_result.json"
    if result_file.exists():
        tr = json.loads(result_file.read_text(encoding='utf-8'))
        text_sample = tr['text'][:400].strip()
        lang = tr.get('language', '?')
        seg_count = tr.get('segments', 0)
        print(f"  -> Transcribed in {t_transcribe:.1f}s | lang={lang} | {seg_count} segments")
        print(f"  -> Sample: {text_sample[:200]}")
        row["transcription_time"] = f"{t_transcribe:.1f}s"
        row["language"] = lang
        row["segments"] = seg_count
        row["transcript_sample"] = text_sample[:300]
        row["transcription_error"] = r2.stderr[-200:] if r2.returncode != 0 else ""
    else:
        print(f"  !! TRANSCRIPTION FAILED: {r2.stderr[-400:]}")
        row["transcription_time"] = "FAILED"
        row["transcript_sample"] = r2.stderr[-300:]

    # ── Totals ────────────────────────────────────────────────
    total = t_download + t_audio + t_transcribe
    row["total_time"] = f"{total:.1f}s ({int(total//60)}m {int(total%60)}s)"
    print(f"\n  -> TOTAL: {row['total_time']}")
    results.append(row)

    # Cleanup
    for p in [out_path, audio_path, bench_script, result_file]:
        try: p.unlink()
        except: pass

# ── Print results table ───────────────────────────────────────
print("\n\n" + "="*70)
print("BENCHMARK RESULTS")
print("="*70)
for r in results:
    print(f"\n{r['label']}")
    print(f"  URL:               {r['url']}")
    print(f"  Video duration:    {r.get('video_duration','?')}")
    print(f"  Download time:     {r.get('download_time','?')}  ({r.get('download_size_mb','?')})")
    print(f"  Transcription:     {r.get('transcription_time','?')}  lang={r.get('language','?')}  segs={r.get('segments','?')}")
    print(f"  Total time:        {r.get('total_time','?')}")
    print(f"  Transcript sample:")
    sample = r.get('transcript_sample','')
    for line in (sample[:400] if sample else '(none)').split('. '):
        print(f"    {line.strip()}")

print("\n" + "="*70)
json.dump(results, open('/opt/ClipsGold/bench_results.json','w'), ensure_ascii=False, indent=2)
print("Full results saved to /opt/ClipsGold/bench_results.json")
