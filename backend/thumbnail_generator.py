"""
Thumbnail generator for video clip candidates.
Extracts single frames from video at specified timestamps.
Includes face detection to calculate 9:16 crop coordinates.
"""

import subprocess
import cv2
import numpy as np
import os
import sys
import warnings
from pathlib import Path
from typing import Optional, Dict, Tuple

# Suppress MediaPipe inference_feedback_manager warnings (Python level only)
warnings.filterwarnings('ignore', category=UserWarning, module='mediapipe')
os.environ['GLOG_minloglevel'] = '2'  # Suppress glog INFO/WARNING

# Note: Avoid suppressing stderr handle as it breaks yt-dlp and other tools

# Try to import MediaPipe for face detection (new tasks API)
try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    print("MediaPipe tasks API loaded successfully")
except ImportError as e:
    MEDIAPIPE_AVAILABLE = False
    python = None
    vision = None
    mp = None
    print(f"MediaPipe not available: {e}")

# Model file path
MODEL_PATH = Path(__file__).parent / "models" / "blaze_face_short_range.tflite"

def ensure_model_downloaded() -> bool:
    """Check if model file exists, download if needed"""
    if MODEL_PATH.exists():
        return True
    
    print(f"[WARN] Face detection model not found at {MODEL_PATH}")
    print("  -> Please download from: https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite")
    print(f"  -> Save to: {MODEL_PATH}")
    return False


# Right 15% of 9:16 crop = platform UI (Like/Comment). Face must stay in left 85%.
UI_ZONE_RIGHT_PERCENT = 0.15
SAFE_ZONE_LEFT_PERCENT = 1.0 - UI_ZONE_RIGHT_PERCENT  # 0.85

# Black border detection: mean pixel below this = black (letterbox/pillarbox)
BLACK_THRESHOLD = 25


def get_content_rect(frame) -> Optional[Tuple[int, int, int, int]]:
    """
    Detect non-black content bounding box (ignores letterbox/pillarbox from Shorts etc).
    Returns (x, y, w, h) or None if frame has no clear black bars.
    """
    if frame is None or frame.size == 0:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    # Sample rows/columns: find first/last where mean > BLACK_THRESHOLD
    col_means = gray.mean(axis=0)
    row_means = gray.mean(axis=1)
    non_black_cols = np.where(col_means > BLACK_THRESHOLD)[0]
    non_black_rows = np.where(row_means > BLACK_THRESHOLD)[0]
    if len(non_black_cols) < 2 or len(non_black_rows) < 2:
        return None
    x1, x2 = int(non_black_cols[0]), int(non_black_cols[-1])
    y1, y2 = int(non_black_rows[0]), int(non_black_rows[-1])
    cw = x2 - x1 + 1
    ch = y2 - y1 + 1
    # Only consider it "content rect" if we actually cropped a meaningful amount (e.g. >5% each side)
    margin_w = w - cw
    margin_h = h - ch
    if margin_w < w * 0.05 and margin_h < h * 0.05:
        return None
    return (x1, y1, cw, ch)


def detect_all_faces_in_frame(frame, video_width: int, video_height: int) -> Tuple[list, float]:
    """
    Detect ALL faces in a single frame and return list of bounding boxes with confidence.
    Uses MediaPipe tasks API (FaceDetector).
    
    Args:
        frame: OpenCV frame (BGR)
        video_width: Video width in pixels
        video_height: Video height in pixels
    
    Returns:
        Tuple of (faces: List[tuple], avg_confidence: float)
        - faces: List of tuples (x, y, w, h) for each detected face, sorted left-to-right
        - avg_confidence: Average detection confidence (0.0-1.0)
    """
    if not MEDIAPIPE_AVAILABLE:
        return [], 0.0
    
    # Check model file exists
    if not ensure_model_downloaded():
        return [], 0.0
    
    try:
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Configure FaceDetector with local model file
        base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=0.5
        )
        
        # Detect faces
        with vision.FaceDetector.create_from_options(options) as detector:
            detection_result = detector.detect(mp_image)
            
            faces = []
            confidences = []
            
            if detection_result.detections:
                for detection in detection_result.detections:
                    # Get bounding box
                    bbox = detection.bounding_box
                    
                    # Convert to absolute coordinates
                    x = int(bbox.origin_x)
                    y = int(bbox.origin_y)
                    w = int(bbox.width)
                    h = int(bbox.height)
                    
                    # Get confidence score
                    confidence = detection.categories[0].score if detection.categories else 0.5
                    
                    faces.append((x, y, w, h))
                    confidences.append(confidence)
                
                # Sort faces left-to-right by x coordinate
                sorted_pairs = sorted(zip(faces, confidences), key=lambda p: p[0][0])
                faces = [f for f, c in sorted_pairs]
                confidences = [c for f, c in sorted_pairs]
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return faces, avg_confidence
            
    except Exception as e:
        # Graceful fallback - don't spam logs with traceback
        return [], 0.0


def detect_faces_multi_frame(
    video_path: Path,
    clip_start: float,
    clip_end: float,
    video_width: int,
    video_height: int
) -> Tuple[list, float, float, Optional[Tuple[int, int, int, int]]]:
    """
    DEEP SCAN: Detect faces across multiple frames to handle cases where speaker isn't in frame at 0.0s.
    Samples 5 frames: 0s, 0.5s, 1s, 2s, 3s (relative to clip start).
    Returns faces from the frame with highest detection confidence.
    Also returns content_rect (non-black area) so crop avoids letterbox/pillarbox.
    
    Returns:
        Tuple of (best_faces, best_confidence, best_timestamp, content_rect)
        - content_rect: (x,y,w,h) of non-black area or None
    """
    if not MEDIAPIPE_AVAILABLE:
        return [], 0.0, 0.0, None
    
    clip_duration = clip_end - clip_start
    
    # Define sample points (relative to clip start).
    # Skip the first 10% of the clip (or at least 0.5s) to avoid dark fade-in frames.
    # Scan from that offset at 1s intervals — pick frame with highest MediaPipe confidence.
    min_offset = max(0.5, clip_duration * 0.10)
    sample_offsets = [min_offset + i for i in [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]]
    sample_offsets = [offset for offset in sample_offsets if offset < clip_duration]
    
    # If clip is very short, at least sample start and middle
    if len(sample_offsets) < 2:
        sample_offsets = [0.0, clip_duration / 2]
    
    print(f"    🔍 Deep Scan: Sampling {len(sample_offsets)} frames at {sample_offsets}s (picking max confidence)")
    
    best_faces = []
    best_confidence = 0.0
    best_timestamp = 0.0
    content_rect = None
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return [], 0.0, 0.0, None
    
    try:
        for offset in sample_offsets:
            timestamp = clip_start + offset
            
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Detect non-black content area (for Shorts with black bars)
            rect = get_content_rect(frame)
            if rect is not None and content_rect is None:
                content_rect = rect
                print(f"      • Content rect (no black): x={rect[0]}, w={rect[2]}, h={rect[3]}")
            
            faces, confidence = detect_all_faces_in_frame(frame, video_width, video_height)
            
            if len(faces) > 0:
                print(f"      • {offset}s: {len(faces)} face(s), confidence={confidence:.2f}")
                
                if confidence > best_confidence:
                    best_faces = faces
                    best_confidence = confidence
                    best_timestamp = offset
                    if rect is not None:
                        content_rect = rect
            else:
                print(f"      • {offset}s: No faces")
        
        if best_faces:
            print(f"    [OK] Best detection at {best_timestamp}s (confidence={best_confidence:.2f})")
        else:
            print(f"    [WARN] No faces found in any frame, using center crop")
        if content_rect:
            print(f"    [OK] Content rect: avoid black bars (UI zone still applied)")
    
    finally:
        cap.release()
    
    return best_faces, best_confidence, best_timestamp, content_rect


def analyze_face_layout(faces: list, video_width: int) -> Dict:
    """
    Analyze face positions to determine if split_screen mode is needed.
    
    Args:
        faces: List of (x, y, w, h) face bounding boxes (sorted left-to-right)
        video_width: Video width in pixels
    
    Returns:
        Dictionary with layout info: {"mode": "single"|"split_screen", "faces": [...], "distance_percent": float}
    """
    if len(faces) == 0:
        return {"mode": "center_crop", "faces": [], "distance_percent": 0}
    
    if len(faces) == 1:
        return {"mode": "single_face", "faces": faces, "distance_percent": 0}
    
    # Check distance between leftmost and rightmost faces
    left_face = faces[0]
    right_face = faces[-1]
    
    left_center_x = left_face[0] + left_face[2] // 2
    right_center_x = right_face[0] + right_face[2] // 2
    
    distance = abs(right_center_x - left_center_x)
    distance_percent = (distance / video_width) * 100
    
    # If faces are far apart (>30% of width), use split screen
    if distance_percent > 30:
        return {
            "mode": "split_screen",
            "faces": faces,
            "distance_percent": distance_percent,
            "left_face": left_face,
            "right_face": right_face
        }
    else:
        # Faces are close together, treat as single group
        return {
            "mode": "group_face",
            "faces": faces,
            "distance_percent": distance_percent
        }


def calculate_crop_coordinates(
    video_width: int,
    video_height: int,
    layout_info: Dict,
    content_rect: Optional[Tuple[int, int, int, int]] = None
) -> Dict[str, int]:
    """
    Calculate 9:16 crop coordinates. Reserves right 15% for platform UI (Like/Comment).
    If content_rect (non-black area) is given, crop stays within it and center uses content center.
    """
    target_aspect = (9, 16)
    mode = layout_info["mode"]
    
    target_width = int(video_height * target_aspect[0] / target_aspect[1])
    target_height = video_height
    
    if target_width > video_width:
        target_width = video_width
        target_height = int(video_width * target_aspect[1] / target_aspect[0])
    
    # Effective bounds: content area if present, else full frame
    if content_rect:
        cx, cy, cw, ch = content_rect
        eff_min_x, eff_min_y = cx, cy
        eff_max_x = cx + cw - target_width
        eff_max_y = cy + ch - target_height
        eff_max_x = max(eff_min_x, eff_max_x)
        eff_max_y = max(eff_min_y, eff_max_y)
        center_x = cx + cw // 2
        center_y = cy + ch // 2
    else:
        eff_min_x, eff_min_y = 0, 0
        eff_max_x = max(0, video_width - target_width)
        eff_max_y = max(0, video_height - target_height)
        center_x = video_width // 2
        center_y = video_height // 2
    
    # Face must stay in left 85% of crop (right 15% = UI zone)
    ui_safe_left = int(SAFE_ZONE_LEFT_PERCENT * target_width)
    
    if mode == "single_face":
        face = layout_info["faces"][0]
        face_x, face_y, face_w, face_h = face
        face_center_x = face_x + face_w // 2
        face_center_y = face_y + face_h // 2

        # 40% padding: ensure face + 40% of its size is visible on each side
        pad_w = int(face_w * 0.4)
        pad_h = int(face_h * 0.4)

        # Center crop on face, then constrain so padded region stays inside crop
        crop_x = face_center_x - target_width // 2
        crop_x = max(crop_x, face_center_x - ui_safe_left)
        # Left padding: crop must start before (face_x - pad_w)
        # Right padding: crop must end after (face_x + face_w + pad_w)
        crop_x_min_pad = max(eff_min_x, face_x + face_w + pad_w - target_width)
        crop_x_max_pad = min(eff_max_x, face_x - pad_w)
        if crop_x_min_pad <= crop_x_max_pad:
            crop_x = max(crop_x_min_pad, min(crop_x, crop_x_max_pad))
        else:
            crop_x = max(eff_min_x, min(crop_x, eff_max_x))

        # Y: center with 40% padding constraint
        crop_y_center = face_center_y - target_height // 2
        crop_y_min_pad = max(eff_min_y, face_y + face_h + pad_h - target_height)
        crop_y_max_pad = min(eff_max_y, face_y - pad_h)
        if crop_y_min_pad <= crop_y_max_pad:
            crop_y = max(crop_y_min_pad, min(crop_y_center, crop_y_max_pad))
        else:
            crop_y = max(eff_min_y, min(crop_y_center, eff_max_y))
    
    elif mode == "group_face":
        faces = layout_info["faces"]
        avg_x = sum(f[0] + f[2] // 2 for f in faces) // len(faces)
        avg_y = sum(f[1] + f[3] // 2 for f in faces) // len(faces)
        
        crop_x = avg_x - target_width // 2
        crop_x = max(crop_x, avg_x - ui_safe_left)
        crop_x = max(eff_min_x, min(crop_x, eff_max_x))
        crop_y = max(eff_min_y, min(avg_y - target_height // 2, eff_max_y))
    
    elif mode == "split_screen":
        # For split screen, return info about both faces
        # Crop coordinates will be calculated differently in reframer
        left_face = layout_info["left_face"]
        right_face = layout_info["right_face"]
        
        return {
            "mode": "split_screen",
            "left_face": {
                "x": left_face[0],
                "y": left_face[1],
                "w": left_face[2],
                "h": left_face[3]
            },
            "right_face": {
                "x": right_face[0],
                "y": right_face[1],
                "w": right_face[2],
                "h": right_face[3]
            },
            "distance_percent": layout_info["distance_percent"]
        }
    
    else:
        # Center crop (no faces): use content center if content_rect, else frame center
        crop_x = max(eff_min_x, min(center_x - target_width // 2, eff_max_x))
        crop_y = max(eff_min_y, min(center_y - target_height // 2, eff_max_y))
    
    # Ensure even numbers for FFmpeg
    crop_x = (crop_x // 2) * 2
    crop_y = (crop_y // 2) * 2
    target_width = (target_width // 2) * 2
    target_height = (target_height // 2) * 2
    
    return {
        "mode": mode,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "crop_width": target_width,
        "crop_height": target_height
    }


def generate_thumbnail(
    input_video: Path,
    output_path: Path,
    timestamp: float,
    quality: int = 2,
    detect_crop: bool = True
) -> Tuple[bool, Optional[Dict[str, int]]]:
    """
    Extract a single frame from video at specified timestamp.
    Also calculates 9:16 crop coordinates with face detection.
    
    Args:
        input_video: Path to input video file
        output_path: Path to save thumbnail JPEG
        timestamp: Time in seconds to extract frame
        quality: JPEG quality (1=best, 31=worst), default 2
        detect_crop: Whether to detect face and calculate crop coordinates
    
    Returns:
        Tuple of (success: bool, crop_coords: Optional[Dict])
    """
    crop_coords = None
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # FFmpeg command to extract single frame
        # -ss: seek to timestamp (before -i for faster seeking)
        # -i: input file
        # -vframes 1: extract only 1 frame
        # -q:v: quality (lower is better for JPEG)
        cmd = [
            'ffmpeg',
            '-ss', str(timestamp),
            '-i', str(input_video),
            '-vframes', '1',
            '-q:v', str(quality),
            '-y',  # Overwrite output file
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        # If crop detection enabled, analyze the extracted frame
        if detect_crop and output_path.exists():
            try:
                # Read the thumbnail to get video dimensions and detect face
                cap = cv2.VideoCapture(str(input_video))
                if cap.isOpened():
                    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    # Seek to timestamp and read frame
                    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret:
                        # Detect ALL faces in this frame
                        faces = detect_all_faces_in_frame(frame, video_width, video_height)
                        
                        # Analyze face layout
                        layout_info = analyze_face_layout(faces, video_width)
                        
                        # Calculate crop coordinates based on layout
                        crop_coords = calculate_crop_coordinates(
                            video_width,
                            video_height,
                            layout_info
                        )
                        
                        # Log detection results
                        if len(faces) > 0:
                            print(f"    [OK] Faces detected: {len(faces)}")
                        
                        if layout_info["mode"] == "split_screen":
                            print(f"    [!] SPLIT SCREEN MODE: {len(faces)} faces ({layout_info['distance_percent']:.1f}% apart, >30% threshold)")
                        elif layout_info["mode"] == "single_face":
                            print(f"    [OK] Single face detected, crop centered on face")
                        elif layout_info["mode"] == "group_face":
                            print(f"    [OK] {len(faces)} faces grouped together ({layout_info['distance_percent']:.1f}% apart, <30% threshold)")
                            print(f"    -> Using single crop centered on group midpoint")
                        else:
                            print(f"    -> No faces detected, using center crop")
            except Exception as e:
                print(f"    [WARN] Crop detection failed: {e}")
        
        return (output_path.exists(), crop_coords)
        
    except subprocess.CalledProcessError as e:
        print(f"[ERR] Thumbnail generation failed: {e}")
        print(f"   stderr: {e.stderr.decode()[:200]}")
        return (False, None)
    except Exception as e:
        print(f"[ERR] Thumbnail generation error: {e}")
        return (False, None)


def generate_thumbnails_for_candidates(
    input_video: Path,
    candidates: list,
    output_dir: Path,
    file_id: str
) -> list:
    """
    Generate thumbnails for all candidates and add thumbnail URLs.
    Uses MULTI-FRAME DEEP SCAN for robust face detection.
    
    Args:
        input_video: Path to source video
        candidates: List of candidate dictionaries
        output_dir: Directory to save thumbnails
        file_id: Unique file identifier
    
    Returns:
        Updated candidates list with thumbnail_url field and crop_preview
    """
    updated_candidates = []
    
    # Get video dimensions once
    cap = cv2.VideoCapture(str(input_video))
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    for idx, candidate in enumerate(candidates):
        start_time = candidate.get('start_time', 0)
        end_time = candidate.get('end_time', start_time + 30)
        
        print(f"\n  -> Candidate {idx + 1}: {start_time:.1f}s - {end_time:.1f}s")
        
        # Generate thumbnail filename
        thumbnail_filename = f"{file_id}_candidate_{idx + 1}_thumb.jpg"
        thumbnail_path = output_dir / thumbnail_filename
        
        # MULTI-FRAME DEEP SCAN: Detect faces + content rect (non-black area for Shorts)
        best_faces, best_confidence, best_timestamp, content_rect = detect_faces_multi_frame(
            input_video,
            start_time,
            end_time,
            video_width,
            video_height
        )
        
        # Decision tree: choose crop mode based on face count + confidence
        n_faces = len(best_faces)
        if n_faces == 0:
            layout_info = {"mode": "center_crop", "faces": [], "distance_percent": 0}
        elif n_faces > 2:
            print(f"    -> {n_faces} faces detected (>2) — forcing blur background mode")
            layout_info = {"mode": "center_crop", "faces": [], "distance_percent": 0}
        elif n_faces == 1 and best_confidence < 0.7:
            print(f"    -> Low confidence {best_confidence:.2f} (<0.7) — forcing blur background mode")
            layout_info = {"mode": "center_crop", "faces": [], "distance_percent": 0}
        else:
            layout_info = analyze_face_layout(best_faces, video_width)

        # Crop: respect content rect (no black) and reserve right 15% for platform UI
        crop_coords = calculate_crop_coordinates(
            video_width,
            video_height,
            layout_info,
            content_rect=content_rect
        )
        
        # Add video dimensions to crop_coords for satisfying split-screen
        if crop_coords:
            crop_coords['video_width'] = video_width
            crop_coords['video_height'] = video_height
            crop_coords['faces'] = [
                {"x": f[0], "y": f[1], "w": f[2], "h": f[3]} 
                for f in best_faces
            ]
        
        # Log detection results
        if len(best_faces) > 0:
            print(f"    [OK] Faces detected: {len(best_faces)}")
        
        if layout_info["mode"] == "split_screen":
            print(f"    [!] SPLIT SCREEN MODE: {len(best_faces)} faces ({layout_info['distance_percent']:.1f}% apart)")
        elif layout_info["mode"] == "single_face":
            print(f"    [OK] Single face mode, crop centered on face")
        elif layout_info["mode"] == "group_face":
            print(f"    [OK] Group face mode: {len(best_faces)} faces grouped")
        else:
            print(f"    -> Center crop (no faces detected)")
        
        # Extract thumbnail frame at best_timestamp (or 15% into clip if no faces — avoids dark fade-in)
        clip_duration_here = end_time - start_time
        thumbnail_timestamp = start_time + best_timestamp if best_faces else start_time + clip_duration_here * 0.15
        success, _ = generate_thumbnail(input_video, thumbnail_path, thumbnail_timestamp, detect_crop=False)
        
        # Add thumbnail URL and crop coordinates to candidate
        candidate_copy = candidate.copy()
        if success:
            candidate_copy['thumbnail_url'] = f"/thumbnails/{thumbnail_filename}"
            if crop_coords:
                candidate_copy['crop_preview'] = crop_coords
            print(f"  [OK] Generated thumbnail for candidate {idx + 1}")
        else:
            candidate_copy['thumbnail_url'] = None
            print(f"  [WARN] Failed to generate thumbnail for candidate {idx + 1}")
        
        updated_candidates.append(candidate_copy)
    
    return updated_candidates


def select_best_thumbnail_frame(
    video_path: Path,
    start_time: float,
    end_time: float,
    sample_count: int = 10
) -> Tuple[Optional[str], float, float]:
    """
    Automatically select the best frame for thumbnail based on face detection confidence.
    Used in autonomous mode to pick the most visually appealing frame.
    
    Args:
        video_path: Path to video file
        start_time: Clip start time in seconds
        end_time: Clip end time in seconds
        sample_count: Number of frames to sample
    
    Returns:
        Tuple of (thumbnail_path, best_timestamp, confidence)
    """
    if not MEDIAPIPE_AVAILABLE or not ensure_model_downloaded():
        print("[WARN] MediaPipe not available, using middle frame")
        mid_time = (start_time + end_time) / 2
        return None, mid_time, 0.0
    
    duration = end_time - start_time
    if duration <= 0:
        return None, start_time, 0.0
    
    # Sample frames evenly throughout the clip
    interval = duration / (sample_count + 1)
    sample_times = [start_time + (i + 1) * interval for i in range(sample_count)]
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[WARN] Failed to open video: {video_path}")
        return None, start_time, 0.0
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    best_frame = None
    best_time = start_time
    best_confidence = 0.0
    
    print(f"  🔍 Scanning {sample_count} frames for best thumbnail...")
    
    for sample_time in sample_times:
        frame_number = int(sample_time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if not ret or frame is None:
            continue
        
        # Detect faces
        faces, avg_confidence = detect_all_faces_in_frame(frame, video_width, video_height)
        
        if avg_confidence > best_confidence:
            best_confidence = avg_confidence
            best_time = sample_time
            best_frame = frame.copy()
    
    cap.release()
    
    if best_frame is None:
        print("  [WARN] No faces detected, using middle frame")
        return None, (start_time + end_time) / 2, 0.0
    
    # Save best frame as thumbnail
    thumbnail_dir = Path(__file__).parent / "thumbnails"
    thumbnail_dir.mkdir(exist_ok=True)
    
    timestamp = int(best_time * 1000)
    thumbnail_filename = f"auto_thumb_{timestamp}.jpg"
    thumbnail_path = thumbnail_dir / thumbnail_filename
    
    cv2.imwrite(str(thumbnail_path), best_frame)
    
    print(f"  [OK] Best thumbnail at {best_time:.1f}s (confidence: {best_confidence:.2f})")
    
    return str(thumbnail_path), best_time, best_confidence


if __name__ == "__main__":
    # Test thumbnail generation
    test_video = Path("uploads/test.mp4")
    test_output = Path("thumbnails/test_thumb.jpg")
    
    if test_video.exists():
        print("Testing thumbnail generation...")
        success = generate_thumbnail(test_video, test_output, 5.0)
        print(f"Result: {'[OK] Success' if success else '[FAIL] Failed'}")
    else:
        print("No test video found")
