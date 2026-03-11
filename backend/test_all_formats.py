"""
Final pipeline test — 6 video formats.
For each: download → transcribe → analyze → render → Telegram.
"""

import os, sys, time, json, subprocess, textwrap
sys.stdout.reconfigure(line_buffering=True)
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
CLIPS_DIR  = BASE_DIR / "clips"
TEMP_DIR   = OUTPUT_DIR / "temp"
DL_DIR     = BASE_DIR / "test_videos"
FFMPEG     = str(BASE_DIR / "ffmpeg.exe") if (BASE_DIR / "ffmpeg.exe").exists() else "ffmpeg"
YDLP       = str(BASE_DIR / "venv312" / "Scripts" / "yt-dlp.exe") if (BASE_DIR / "venv312" / "Scripts" / "yt-dlp.exe").exists() else "yt-dlp"

for d in [OUTPUT_DIR, CLIPS_DIR, TEMP_DIR, DL_DIR]:
    d.mkdir(exist_ok=True)

# ── Test definitions ────────────────────────────────────────────────────────
TESTS = [
    {
        "id": 1,
        "name": "Short English 16:9",
        "lang": "en",
        # ytsearch: picks first available result in 2-5 min range
        "url": "ytsearch1:short english motivational speech 3 minutes",
        "local": None,
        "min_dur": 120, "max_dur": 360,
    },
    {
        "id": 2,
        "name": "Long English 16:9",
        "lang": "en",
        # ytsearch: long lecture/podcast 20-40 min
        "url": "ytsearch5:startup advice lecture 2023 english",
        "local": None,
        "min_dur": 1200, "max_dur": 3600,
    },
    {
        "id": 3,
        "name": "Short Russian 16:9",
        "lang": "ru",
        "url": "ytsearch1:короткое мотивационное видео 3 минуты",
        "local": None,
        "min_dur": 120, "max_dur": 360,
    },
    {
        "id": 4,
        "name": "Long Russian 16:9",
        "lang": "ru",
        "url": "ytsearch5:интервью подкаст бизнес русский 2023",
        "local": None,
        "min_dur": 1200, "max_dur": 3600,
    },
    {
        "id": 5,
        "name": "Vertical 9:16",
        "lang": "ru",
        "url": None,
        "local": Path(r"C:\Users\kamal\Downloads\IMG_2351.mp4"),
        "min_dur": 0, "max_dur": 99999,
    },
    {
        "id": 6,
        "name": "Non-standard 4:3",
        "lang": "en",
        "url": "ytsearch1:interview 2008 old format 4:3 english",
        "local": None,
        "min_dur": 120, "max_dur": 1200,
    },
]

# Allow running specific tests: python test_all_formats.py 2 4
_only = {int(a) for a in sys.argv[1:] if a.isdigit()}
if _only:
    TESTS = [t for t in TESTS if t["id"] in _only]

results = []

# ── Helpers ─────────────────────────────────────────────────────────────────

def run(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def probe_video(path):
    r = run([FFMPEG, "-i", str(path)], timeout=15)
    info = {"width": 0, "height": 0, "duration": 0.0, "fps": 30}
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            info["duration"] = int(h)*3600 + int(m)*60 + float(s)
        if "Video:" in line and "x" in line:
            import re
            m2 = re.search(r"(\d{3,5})x(\d{3,5})", line)
            if m2:
                info["width"], info["height"] = int(m2.group(1)), int(m2.group(2))
            m3 = re.search(r"(\d+(?:\.\d+)?) fps", line)
            if m3:
                info["fps"] = float(m3.group(1))
    return info


def download_video(url, out_path, min_dur, max_dur):
    """Download via yt-dlp at 360p (fast), with duration filter."""
    if out_path.exists() and out_path.stat().st_size > 100_000:
        print(f"    Already downloaded: {out_path.name}", flush=True)
        return True

    # Duration filter for search queries
    dur_filter = f"duration>{min_dur} & duration<{max_dur}"

    # Single-file formats only (no DASH split streams that require ffmpeg merge)
    # Prefer smallest single-file mp4; max-filesize 80M to avoid huge downloads
    fmt = "worst[ext=mp4]/18/best[height<=360][ext=mp4]/best[height<=360]"

    cmd = [YDLP, "--no-playlist",
           "--format", fmt,
           "--merge-output-format", "mp4",
           "--max-filesize", "80M",
           "--match-filter", dur_filter,
           "-o", str(out_path), url]

    print(f"    Downloading ({url[:60]}...)  filter: {dur_filter}", flush=True)
    r = subprocess.run(cmd, timeout=1200)  # 20 min timeout
    if r.returncode != 0 or not out_path.exists():
        # Fallback: single-file worst quality (avoids DASH merge requirement)
        cmd2 = [YDLP, "--no-playlist", "--format", "worst[ext=mp4]/worst",
                "--max-filesize", "80M",
                "--match-filter", dur_filter,
                "--merge-output-format", "mp4", "-o", str(out_path), url]
        r2 = subprocess.run(cmd2, timeout=1200)
        if not out_path.exists():
            print(f"    Download FAILED", flush=True)
            return False
    print(f"    Downloaded: {out_path.stat().st_size//1024} KB", flush=True)
    return True


def build_vf_chain(width, height, rel_sub):
    """Choose correct scale/crop based on source aspect ratio."""
    if width == 0 or height == 0:
        ratio = 1.0
    else:
        ratio = width / height

    if abs(ratio - 9/16) < 0.05:
        # Already vertical 9:16
        scale = "scale=1080:1920"
    elif ratio > 1.4:
        # Landscape 16:9 or wider → fill 9:16, center crop
        scale = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    elif abs(ratio - 4/3) < 0.1 or abs(ratio - 1.0) < 0.1:
        # 4:3 or 1:1 → scale to fill height, center crop width
        scale = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    else:
        # Default: fill + crop
        scale = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    return f"{scale},subtitles={rel_sub}"


def send_telegram(video_path, caption):
    import requests
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    with open(video_path, "rb") as f:
        r = requests.post(url, data={"chat_id": chat_id, "caption": caption},
                          files={"video": f}, timeout=300)
    return r.status_code == 200 and r.json().get("ok")


# ── Main loop ────────────────────────────────────────────────────────────────

from services.transcription import run_whisper_transcribe
from subtitle_generator_v2 import create_subtitle_generator
from analyzer import create_analyzer

analyzer = create_analyzer()
sub_gen  = create_subtitle_generator(use_semantic_chunking=False)

for cfg in TESTS:
    tid   = cfg["id"]
    tname = cfg["name"]
    print(f"\n{'='*60}")
    print(f"TEST {tid}: {tname}")
    print(f"{'='*60}")

    row = {"id": tid, "name": tname, "status": "FAIL",
           "time_s": 0, "clips": 0, "problems": []}
    t_start = time.time()

    try:
        # ── 1. Get video ──────────────────────────────────────────
        if cfg["local"]:
            video_path = Path(cfg["local"])
            if not video_path.exists():
                raise FileNotFoundError(f"Local file not found: {video_path}")
            print(f"  Using local file: {video_path.name}", flush=True)
        else:
            video_path = DL_DIR / f"test_{tid}.mp4"
            ok = download_video(cfg["url"], video_path, cfg["min_dur"], cfg["max_dur"])
            if not ok:
                raise RuntimeError("Download failed")

        info = probe_video(video_path)
        dur  = info["duration"]
        w, h = info["width"], info["height"]
        print(f"  Video: {w}x{h}, {dur:.0f}s ({dur/60:.1f} min)")
        if dur < 10:
            raise RuntimeError(f"Video too short: {dur:.1f}s")

        # ── 2. Transcribe ─────────────────────────────────────────
        print(f"  Transcribing ({dur/60:.1f} min video)...")
        t_tr = time.time()
        transcript = run_whisper_transcribe(str(video_path), word_timestamps=True)
        tr_secs = time.time() - t_tr
        segs  = transcript.get("segments", [])
        words = sum(len(s.get("words", [])) for s in segs)
        text  = transcript.get("text", "")
        print(f"  Transcription: {len(segs)} segs, {words} words in {tr_secs:.0f}s")
        if not text.strip():
            raise RuntimeError("Transcription empty")

        # ── 3. Analyze viral moments ──────────────────────────────
        print(f"  Analyzing viral moments...")
        clips = analyzer.analyze_transcription(text, dur)
        print(f"  Found {len(clips)} clips:")
        for c in clips:
            s, e = c.get("start_time",0), c.get("end_time",0)
            print(f"    [{s:.0f}s–{e:.0f}s] {c.get('title','')} score={c.get('virality_score','?')}")
            # Validate clip duration
            if (e - s) < 5 or (e - s) > 120:
                row["problems"].append(f"clip duration {e-s:.0f}s out of range")
        if not clips:
            raise RuntimeError("No viral clips found")

        row["clips"] = len(clips)

        # ── 4. Render best clip ───────────────────────────────────
        best = max(clips, key=lambda c: c.get("virality_score", 0))
        cs, ce = best["start_time"], best["end_time"]
        cdur   = ce - cs
        print(f"  Rendering best clip: {cs:.0f}s–{ce:.0f}s ({cdur:.0f}s)")

        # Pass 1 — cut
        temp_cut = TEMP_DIR / f"t{tid}_cut.mp4"
        r1 = run([FFMPEG,
                  "-ss", str(cs), "-t", str(cdur), "-i", str(video_path),
                  "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                  "-c:a", "aac", "-b:a", "128k", "-y", str(temp_cut)], timeout=120)
        if r1.returncode != 0 or not temp_cut.exists():
            raise RuntimeError(f"Pass 1 failed: {r1.stderr[-200:]}")

        # Generate subtitles
        sub_path = OUTPUT_DIR / f"t{tid}_subs.ass"
        sub_gen.generate_ass_from_transcription(
            transcription_data=transcript,
            output_path=sub_path,
            hook_text="",
            clip_start_time=cs,
            clip_end_time=ce,
            clip_duration=cdur,
            platform="tiktok",
            subtitle_style="hormozi",
        )
        dl_lines = [l for l in sub_path.read_text("utf-8-sig").splitlines()
                    if l.startswith("Dialogue:") and ",Default," in l]
        print(f"  Subtitle lines: {len(dl_lines)}")
        if len(dl_lines) == 0:
            row["problems"].append("0 subtitle Dialogue lines")

        # Pass 2 — scale + subtitles
        rel_sub  = os.path.relpath(sub_path, os.getcwd()).replace("\\", "/").replace(":", "\\:")
        vf_chain = build_vf_chain(w, h, rel_sub)
        clip_out = CLIPS_DIR / f"test_{tid}_result.mp4"
        r2 = run([FFMPEG, "-i", str(temp_cut),
                  "-vf", vf_chain,
                  "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                  "-c:a", "aac", "-b:a", "128k",
                  "-r", "30", "-pix_fmt", "yuv420p",
                  "-y", str(clip_out)], timeout=180)
        if r2.returncode != 0 or not clip_out.exists():
            raise RuntimeError(f"Pass 2 failed:\n{r2.stderr[-300:]}")

        # Verify output dimensions
        out_info = probe_video(clip_out)
        ow, oh = out_info["width"], out_info["height"]
        print(f"  Output: {ow}x{oh}, {clip_out.stat().st_size//1024} KB")
        if ow != 1080 or oh != 1920:
            row["problems"].append(f"wrong output size {ow}x{oh}")

        # ── 5. Send to Telegram ───────────────────────────────────
        size_mb = clip_out.stat().st_size / 1024 / 1024
        caption = (
            f"TEST {tid}: {tname}\n"
            f"{best.get('title','')} | score {best.get('virality_score','?')}/10\n"
            f"{w}x{h} → 1080x1920 | {cdur:.0f}s | {len(dl_lines)} subtitle lines"
        )
        if size_mb <= 50:
            ok_tg = send_telegram(str(clip_out), caption)
            if not ok_tg:
                row["problems"].append("Telegram send failed")
            print(f"  Telegram: {'OK' if ok_tg else 'FAILED'}")
        else:
            row["problems"].append(f"file {size_mb:.1f}MB > 50MB limit")
            print(f"  Telegram skipped ({size_mb:.1f} MB)")

        row["status"] = "OK" if not row["problems"] else "WARN"

    except Exception as e:
        row["problems"].append(str(e)[:120])
        print(f"  ERROR: {e}")

    row["time_s"] = int(time.time() - t_start)
    results.append(row)
    print(f"  Time: {row['time_s']}s | Status: {row['status']}")

# ── Summary table ─────────────────────────────────────────────────────────────

print("\n" + "="*70)
print("RESULTS")
print("="*70)
header = f"{'Test':<4} {'Name':<22} {'Status':<6} {'Time':>6} {'Clips':>5}  Problems"
print(header)
print("-"*70)
for r in results:
    prob = "; ".join(r["problems"]) if r["problems"] else "—"
    prob = textwrap.shorten(prob, 30)
    print(f"{r['id']:<4} {r['name']:<22} {r['status']:<6} {r['time_s']:>5}s {r['clips']:>5}  {prob}")
print("="*70)

ok_count = sum(1 for r in results if r["status"] in ("OK", "WARN"))
print(f"\nPassed: {ok_count}/{len(results)}")
