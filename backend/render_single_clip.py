"""
Single clip rendering endpoint with WebSocket progress tracking.
Separated from main.py for cleaner code organization.
"""

from pathlib import Path
from typing import Optional, List, Tuple
import asyncio
import json
import subprocess
from fastapi import HTTPException
from subtitle_generator_v2 import create_subtitle_generator
from services.social_meta import generate_social_metadata
from emoji_overlay import extract_emojis_from_metadata, create_multi_emoji_sequence
from services.interview_reframer import get_face_crop_window


def _probe_source_dimensions(input_file: Path) -> Tuple[Optional[int], Optional[int]]:
    """Return (width, height) via ffprobe, or (None, None) on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "csv=p=0",
                str(input_file),
            ],
            capture_output=True, text=True, timeout=15,
        )
        parts = result.stdout.strip().split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return None, None


async def _fire_social_metadata(clip_transcript: str, clip_title: str, platform: str, meta_path: Path) -> None:
    try:
        await generate_social_metadata(
            clip_transcript=clip_transcript,
            clip_title=clip_title,
            platform=platform,
            output_path=meta_path,
        )
    except Exception as e:
        print(f"  [WARN] Social metadata generation failed: {e}")


def _build_jump_cut_segments(
    transcription_data: dict,
    clip_start: float,
    clip_end: float,
    pause_threshold: float = 1.5,
) -> Optional[List[dict]]:
    """
    Scan word-level timestamps for pauses > pause_threshold seconds.
    Returns list of {start, end} keep-segments if any pauses found, else None.
    """
    segments = transcription_data.get("segments", []) if transcription_data else []
    words = []
    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        if seg_end < clip_start or seg_start > clip_end:
            continue
        for w in seg.get("words", []):
            ws = w.get("start", 0)
            we = w.get("end", 0)
            if we > clip_start and ws < clip_end:
                words.append({"start": ws, "end": we})

    if not words:
        return None

    keep_segments = []
    seg_start = max(words[0]["start"], clip_start)
    prev_end = words[0]["end"]

    for w in words[1:]:
        gap = w["start"] - prev_end
        if gap > pause_threshold:
            keep_segments.append({"start": seg_start - clip_start, "end": prev_end - clip_start})
            seg_start = w["start"]
        prev_end = w["end"]

    keep_segments.append({"start": seg_start - clip_start, "end": min(prev_end, clip_end) - clip_start})

    if len(keep_segments) <= 1:
        return None  # No meaningful cuts

    print(f"  [CUT] Jump-cut: {len(keep_segments)} segments (removed {len(keep_segments)-1} pause(s) >{pause_threshold}s)")
    return keep_segments


async def render_single_clip_with_progress(
    file_id: str,
    clip_index: int,
    platform: str,
    task_id: str,
    clip_candidates_store: dict,
    UPLOAD_DIR: Path,
    CLIPS_DIR: Path,
    OUTPUT_DIR: Path,
    transcription_store: dict,
    cut_video_segment_enhanced_func,
    manual_crop_x: Optional[int] = None,
    show_hook: bool = True,
    subtitle_style: str = "podcast",
    enable_jump_cut: bool = False,
    enable_sfx: bool = True,
    use_semantic_chunking: bool = True,
    start_time_override: Optional[float] = None,
    end_time_override: Optional[float] = None,
    subtitle_language: str = "auto",
    render_mode: str = "auto",
    enable_filler_removal: bool = False,
    show_subtitles: bool = True,
):
    """
    Render a single clip with WebSocket progress tracking.
    
    Args:
        file_id: Video file ID
        clip_index: Index of clip to render (0-based)
        task_id: Unique task ID for WebSocket progress tracking
        platform: Target platform (tiktok, youtube, instagram)
        clip_candidates_store: Store with clip candidates
        UPLOAD_DIR: Upload directory path
        CLIPS_DIR: Clips output directory path
        OUTPUT_DIR: Output directory path
        transcription_store: Store with transcriptions
        cut_video_segment_enhanced_func: Async function for video rendering
        manual_crop_x: Manual override for crop X position
    
    Returns:
        dict with clip info and task_id for WebSocket connection
    """
    # Use the task_id from the caller so the client can connect to the same WebSocket
    # Get clip candidates
    candidates = clip_candidates_store.get(file_id)
    if not candidates:
        # Fallback: restore from disk after backend restart
        analysis_file = OUTPUT_DIR / f"{file_id}_analysis.json"
        if analysis_file.exists():
            with analysis_file.open("r", encoding="utf-8") as f:
                candidates = json.load(f)
            clip_candidates_store[file_id] = candidates
            print(f"  -> Restored {len(candidates)} candidates from disk (was not in memory)")
        else:
            raise HTTPException(status_code=404, detail="No candidates found for this file")
    
    if clip_index >= len(candidates):
        raise HTTPException(status_code=404, detail="Clip index out of range")
    
    clip = dict(candidates[clip_index])  # shallow copy so we don't mutate the store
    if start_time_override is not None:
        print(f"  -> start_time override: {clip['start_time']} -> {start_time_override}")
        clip["start_time"] = start_time_override
    if end_time_override is not None:
        print(f"  -> end_time override: {clip['end_time']} -> {end_time_override}")
        clip["end_time"] = end_time_override
    
    # Get input file
    input_file = UPLOAD_DIR / f"{file_id}.mp4"
    if not input_file.exists():
        raise HTTPException(status_code=404, detail="Source video not found")
    
    # Get transcription (from memory or file) - MUST use latest edited version
    transcription_data = transcription_store.get(file_id)
    if not transcription_data:
        # Fallback: load from file if not in memory
        transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
        if transcription_file.exists():
            import json
            with transcription_file.open("r", encoding="utf-8") as f:
                transcription_data = json.load(f)
            print(f"  -> Loaded transcription from file (not in memory)")
        else:
            print(f"  [WARN] No transcription found for {file_id}")
    
    # Generate content hash for cache busting (includes clip_id + show_hook + subtitle content)
    import hashlib
    content_parts = [
        str(clip_index),
        str(show_hook),
        clip.get("hook", "") if show_hook else "",
    ]
    
    # Add subtitle text content to hash (if edited, hash changes -> new filename)
    if transcription_data and transcription_data.get("segments"):
        for seg in transcription_data["segments"]:
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            # Only include segments within clip time range
            if seg_end >= clip["start_time"] and seg_start <= clip["end_time"]:
                content_parts.append(seg.get("text", ""))
    
    content_string = "|".join(content_parts)
    content_hash = hashlib.md5(content_string.encode()).hexdigest()[:6]
    
    # Setup output path with content hash (forces new render on any content change)
    hook_flag = "h1" if show_hook else "h0"
    style_flag = subtitle_style[:2]  # ho/be/mi
    clip_filename = f"{file_id}_clip_{clip_index + 1}_{hook_flag}_{style_flag}_s{content_hash}_VIRAL_GOLD.mp4"
    clip_path = CLIPS_DIR / clip_filename
    
    print(f"  -> Content hash: {content_hash} (clip={clip_index}, hook={show_hook})")
    print(f"  -> Filename: {clip_filename}")
    
    # Get crop filter
    crop_filter = None
    crop_preview = clip.get("crop_preview")

    # Two render modes only: blur_background (full frame + blur) or interview (dynamic face crop)
    _force_blur = render_mode == "blur_background"
    subtitle_gen = create_subtitle_generator()
    video_info = None

    # Probe source resolution once (validation + smart pan math)
    _src_w, _src_h = _probe_source_dimensions(input_file)

    if _force_blur:
        print("  -> Blur background mode")

    # Interview mode: dynamic two-speaker smart pan (overrides standard crop_filter)
    is_interview_mode = False
    if render_mode == "interview" and not _force_blur:
        from services.interview_reframer import create_interview_reframer
        print("  -> INTERVIEW MODE: Smart pan speaker crop...")

        # Fall back to blur background if source is below 1080p
        if _src_h is not None and _src_h < 1080:
            print(f"  [WARN] Face crop requires 1080p+, source is {_src_w}×{_src_h} — falling back to blur background")
            _force_blur = True
        else:
            _irf = create_interview_reframer()
            try:
                _trans_segs = (transcription_data or {}).get("segments", [])
                _ia = _irf.analyze(
                    input_file,
                    clip["start_time"],
                    clip["end_time"],
                    transcription_segments=_trans_segs,
                )
                _if = _irf.generate_filter_complex(_ia)
                if _if:
                    is_interview_mode = True
                    crop_filter = _if
                    print(f"  -> Interview: mode={_ia.mode}, segments={len(_ia.segments)}")
                else:
                    print("  -> Interview filter generation failed, using standard crop")
            except Exception as e:
                print(f"  [WARN] Interview mode failed: {e}")
            finally:
                _irf.close()

    # Auto mode: smart pan using face center from crop_preview
    if not is_interview_mode and not _force_blur and crop_preview and "crop_x" in crop_preview:
        if _src_w and _src_h and _src_h >= 1080:
            face_cx = crop_preview["crop_x"] + crop_preview["crop_width"] / 2
            x_off, cw, ch = get_face_crop_window(_src_w, _src_h, face_cx)
            crop_filter = f"crop={cw}:{ch}:{x_off}:0"
            print(f"  -> Smart pan: face_cx={face_cx:.0f}, window={cw}×{ch} @ x={x_off}")

    # In blur/full-frame mode, place subtitles at the bottom edge of the
    # letterboxed video band instead of the platform UI safe-zone (which would
    # float them in the blurred strip below the actual video).
    _sub_margin_v = None
    if _force_blur and _src_w and _src_h:
        _fg_h = round((1080 * _src_h / _src_w) / 2) * 2  # foreground height after scale=1080:-1 (even)
        if 0 < _fg_h < 1920:
            _sub_margin_v = (1920 - _fg_h) // 2          # MarginV from bottom = video's bottom edge
            print(f"  -> Subtitles at video bottom edge: MarginV={_sub_margin_v} (fg_h={_fg_h})")

    # Generate subtitles (skipped entirely when show_subtitles is False → clean video)
    subtitle_path = None
    if subtitle_gen and transcription_data and show_subtitles:
        try:
            import time
            timestamp = int(time.time() * 1000)
            clip_id = f"{file_id}_clip_{clip_index + 1}"
            subtitle_path = OUTPUT_DIR / f"subs_{clip_id}_{timestamp}.ass"
            
            is_split_screen = crop_preview and crop_preview.get("mode") == "split_screen"
            
            subtitle_gen.generate_ass_from_transcription(
                transcription_data,
                subtitle_path,
                hook_text=clip.get("hook", "") if show_hook else "",
                emojis=clip.get("emojis", []),
                clip_start_time=clip["start_time"],
                clip_end_time=clip["end_time"],
                clip_duration=clip["end_time"] - clip["start_time"],
                platform=platform,
                is_split_screen=is_split_screen,
                crop_preview=crop_preview,
                subtitle_style=subtitle_style,
                subtitle_language=subtitle_language,
                margin_v_override=_sub_margin_v,
            )
        except Exception as e:
            print(f"[FAIL] Subtitle generation failed: {e}")
    
    is_split_screen_mode = False
    letterbox_with_blur = _force_blur
    background_video_path = None
    
    # ── Step 8: Smart Jump-Cut ──────────────────────────────────────────
    jump_cut_segments = None
    if enable_jump_cut and transcription_data:
        try:
            jump_cut_segments = _build_jump_cut_segments(
                transcription_data,
                clip["start_time"],
                clip["end_time"],
                pause_threshold=1.5,
            )
        except Exception as e:
            print(f"  [WARN] Jump-cut detection failed: {e}")

    # ── Step 8b: Filler Word Removal ────────────────────────────────────
    if enable_filler_removal and transcription_data and not jump_cut_segments:
        try:
            from services.pipeline_upgrades import find_filler_segments, build_keep_segments_without_fillers
            filler_ivs = find_filler_segments(
                transcription_data, clip["start_time"], clip["end_time"]
            )
            if filler_ivs:
                clip_dur = clip["end_time"] - clip["start_time"]
                filler_segs = build_keep_segments_without_fillers(clip_dur, filler_ivs)
                if filler_segs:
                    jump_cut_segments = filler_segs
                    print(f"  -> Filler removal: {len(filler_ivs)} words removed, {len(filler_segs)} keep-segments")
        except Exception as e:
            print(f"  [WARN] Filler removal failed: {e}")

    # ── Step 5: Auto-SFX ────────────────────────────────────────────────
    sfx_path = None
    if enable_sfx:
        sfx_dir = Path(__file__).parent / "assets" / "sfx"
        for sfx_name in ("pop.mp3", "whoosh.mp3"):
            candidate = sfx_dir / sfx_name
            if candidate.exists():
                sfx_path = candidate
                print(f"  -> SFX: {sfx_name}")
                break
        if not sfx_path:
            print(f"  -> No SFX files in assets/sfx/ — skipping")

    # ── Step 9: Emoji Pop-ups ───────────────────────────────────────────
    # Disabled: FFmpeg drawtext with emoji (NotoColorEmoji) crashes on Ubuntu with libx264 (exit code 234)
    emoji_sequence = []

    print(f"\n-> Rendering Clip {clip_index + 1}: {clip['title'][:40]}...")
    print(f"  -> Task ID: {task_id}")
    print(f"  -> Platform: {platform}")
    print(f"  -> Style: {subtitle_style}")
    _mode_label = "[!] INTERVIEW" if is_interview_mode else "LETTERBOX+BLUR" if letterbox_with_blur else "STANDARD"
    print(f"  -> Mode: {_mode_label}")
    if is_interview_mode:
        _crop_label = "Кроп лица (интервью)"
    elif letterbox_with_blur:
        _crop_label = "Полный кадр (размытие по краям)"
    elif crop_filter:
        _crop_label = "Кроп лица"
    else:
        _crop_label = "Кроп 9:16 (центр)"
    _lang_label = {"ru": "Русский", "en": "English"}.get(subtitle_language, "Оригинал")

    # Render with progress tracking
    await cut_video_segment_enhanced_func(
        input_file,
        clip_path,
        clip["start_time"],
        clip["end_time"],
        subtitle_path=subtitle_path,
        crop_filter=crop_filter,
        zoom_filter=None,
        video_fps=video_info['fps'] if video_info else None,
        is_split_screen=is_split_screen_mode,
        task_id=task_id,
        background_video_path=background_video_path,
        manual_crop_x=manual_crop_x,
        letterbox_with_blur=letterbox_with_blur,
        sfx_path=sfx_path,
        jump_cut_segments=jump_cut_segments,
        emoji_sequence=emoji_sequence,
        is_interview_mode=is_interview_mode,
    )

    print(f"[OK] Clip {clip_index + 1} rendered successfully: {clip_filename}")

    # ── Step 6: Social Metadata Generator ───────────────────────────────
    clip_transcript = ""
    if transcription_data:
        segs = transcription_data.get("segments", [])
        clip_transcript = " ".join(
            s.get("text", "") for s in segs
            if s.get("end", 0) >= clip["start_time"] and s.get("start", 0) <= clip["end_time"]
        ).strip()

    meta_path = OUTPUT_DIR / f"{file_id}_clip_{clip_index + 1}_meta.json"
    asyncio.create_task(_fire_social_metadata(
        clip_transcript=clip_transcript,
        clip_title=clip.get("title", ""),
        platform=platform,
        meta_path=meta_path,
    ))

    return {
        "task_id": task_id,
        "clip_id": clip_index + 1,
        "filename": clip_filename,
        "title": clip["title"],
        "status": "completed",
        "meta": {},
        "source_width": _src_w,
        "source_height": _src_h,
        "crop_label": _crop_label,
        "lang_label": _lang_label,
    }
