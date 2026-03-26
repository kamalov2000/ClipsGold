import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, List, Optional
import subprocess
import json
import os
import sys
import warnings

# Suppress MediaPipe inference_feedback_manager warnings (Python level only)
warnings.filterwarnings('ignore', category=UserWarning, module='mediapipe')
os.environ['GLOG_minloglevel'] = '2'  # Suppress glog INFO/WARNING

# Note: Avoid suppressing stderr handle as it breaks yt-dlp and other tools

# MediaPipe for face tracking - New Tasks API
try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    print("MediaPipe (Tasks API) loaded successfully")
    print(f"   Version: {mp.__version__ if hasattr(mp, '__version__') else 'unknown'}")
except ImportError as e:
    MEDIAPIPE_AVAILABLE = False
    python = None
    vision = None
    mp = None
    print("MediaPipe library not found")
    print("  Install with: pip install mediapipe")
    print("  Falling back to center crop for 9:16 reframing")
except Exception as e:
    MEDIAPIPE_AVAILABLE = False
    python = None
    vision = None
    mp = None
    print(f"MediaPipe failed to load: {e}")
    print("  Falling back to center crop for 9:16 reframing")

# Model file path
MODEL_PATH = Path(__file__).parent / "models" / "blaze_face_short_range.tflite"


class FaceReframer:
    def __init__(self):
        self.face_detector = None
        self.smoothing_window = []  # For smoothing face positions
        self.smoothing_size = 5  # Number of frames to average
        
        if not MEDIAPIPE_AVAILABLE:
            print("[i] MediaPipe face detection disabled - using center crop")
            return
        
        # Check if model file exists
        if not MODEL_PATH.exists():
            print(f"[WARN] Face detection model not found at {MODEL_PATH}")
            print("  -> Falling back to center crop (no face tracking)")
            self.face_detector = None
            return
            
        try:
            # Initialize MediaPipe face detector with Tasks API and local model
            base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
            options = vision.FaceDetectorOptions(
                base_options=base_options,
                min_detection_confidence=0.5
            )
            self.face_detector = vision.FaceDetector.create_from_options(options)
            print("[OK] MediaPipe face detector initialized with Tasks API")
        except Exception as e:
            # Graceful fallback - don't spam logs
            print("  -> Face detection unavailable, using center crop")
            self.face_detector = None
    
    def get_video_info(self, video_path: Path) -> dict:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,duration",
                "-of", "json",
                str(video_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        
        fps_parts = stream["r_frame_rate"].split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1])
        
        return {
            "width": int(stream["width"]),
            "height": int(stream["height"]),
            "fps": fps,
            "duration": float(stream.get("duration", 0))
        }
    
    def smooth_face_position(self, new_box: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Apply smoothing to face position to prevent camera shake"""
        self.smoothing_window.append(new_box)
        
        # Keep only last N frames
        if len(self.smoothing_window) > self.smoothing_size:
            self.smoothing_window.pop(0)
        
        # Average the positions
        if len(self.smoothing_window) == 0:
            return new_box
        
        avg_x = sum(box[0] for box in self.smoothing_window) // len(self.smoothing_window)
        avg_y = sum(box[1] for box in self.smoothing_window) // len(self.smoothing_window)
        avg_w = sum(box[2] for box in self.smoothing_window) // len(self.smoothing_window)
        avg_h = sum(box[3] for box in self.smoothing_window) // len(self.smoothing_window)
        
        return (avg_x, avg_y, avg_w, avg_h)
    
    def detect_faces(
        self,
        video_path: Path,
        start_time: float = 0,
        end_time: Optional[float] = None,
        sample_rate: int = 30
    ) -> List[Tuple[int, int, int, int]]:
        # If MediaPipe not available, return empty list (no face detection)
        if not MEDIAPIPE_AVAILABLE or self.face_detector is None:
            print("MediaPipe not available, skipping face detection - using center crop")
            return []
            
        # Reset smoothing window for new clip
        self.smoothing_window = []
        
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        video_info = self.get_video_info(video_path)
        fps = video_info["fps"]
        width = video_info["width"]
        height = video_info["height"]
        
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps) if end_time else int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        face_boxes = []
        frame_count = start_frame
        last_valid_box = None
        
        while frame_count < end_frame:
            ret, frame = cap.read()
            if not ret:
                break
            
            if (frame_count - start_frame) % sample_rate == 0:
                # Convert frame to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Create MediaPipe Image
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                
                # Detect faces using Tasks API
                detection_result = self.face_detector.detect(mp_image)
                
                if detection_result.detections:
                    for detection in detection_result.detections:
                        bbox = detection.bounding_box
                        # Get absolute coordinates
                        x = int(bbox.origin_x)
                        y = int(bbox.origin_y)
                        w = int(bbox.width)
                        h = int(bbox.height)
                        
                        # Apply smoothing to prevent camera shake
                        smoothed_box = self.smooth_face_position((x, y, w, h))
                        face_boxes.append(smoothed_box)
                        last_valid_box = smoothed_box
                        break  # Use first detected face only
                elif last_valid_box:
                    # If no face detected, use last known position
                    face_boxes.append(last_valid_box)
            
            frame_count += 1
        
        cap.release()
        return face_boxes
    
    def calculate_crop_for_916(
        self,
        face_boxes: List[Tuple[int, int, int, int]],
        video_width: int,
        video_height: int,
        target_aspect: Tuple[int, int] = (9, 16)
    ) -> Tuple[int, int, int, int]:
        """Calculate crop coordinates for 9:16 aspect ratio with face tracking or center crop"""
        if not face_boxes:
            print(f"  -> No faces detected, using center crop for {video_width}x{video_height}")
            return self._default_center_crop(video_width, video_height, target_aspect)
        
        # Calculate average face center + dimensions
        avg_x = int(np.mean([x + w // 2 for x, y, w, h in face_boxes]))
        avg_y = int(np.mean([y + h // 2 for x, y, w, h in face_boxes]))
        avg_face_w = int(np.mean([w for x, y, w, h in face_boxes]))
        avg_face_h = int(np.mean([h for x, y, w, h in face_boxes]))

        # Calculate target dimensions for 9:16 aspect ratio
        target_width = int(video_height * target_aspect[0] / target_aspect[1])
        target_height = video_height

        if target_width > video_width:
            target_width = video_width
            target_height = int(video_width * target_aspect[1] / target_aspect[0])

        # Center crop on face position
        crop_x = max(0, min(avg_x - target_width // 2, video_width - target_width))
        crop_y = max(0, min(avg_y - target_height // 2, video_height - target_height))

        # 40% padding: constrain so face + 40% of its size stays within crop
        pad_w = int(avg_face_w * 0.4)
        pad_h = int(avg_face_h * 0.4)
        face_left = avg_x - avg_face_w // 2
        face_top = avg_y - avg_face_h // 2
        crop_x_min_pad = max(0, face_left + avg_face_w + pad_w - target_width)
        crop_x_max_pad = min(video_width - target_width, face_left - pad_w)
        if crop_x_min_pad <= crop_x_max_pad:
            crop_x = max(crop_x_min_pad, min(crop_x, crop_x_max_pad))
        crop_y_min_pad = max(0, face_top + avg_face_h + pad_h - target_height)
        crop_y_max_pad = min(video_height - target_height, face_top - pad_h)
        if crop_y_min_pad <= crop_y_max_pad:
            crop_y = max(crop_y_min_pad, min(crop_y, crop_y_max_pad))
        
        # Ensure even numbers for FFmpeg
        crop_x = (crop_x // 2) * 2
        crop_y = (crop_y // 2) * 2
        target_width = (target_width // 2) * 2
        target_height = (target_height // 2) * 2
        
        print(f"  -> Face-centered crop: offset=({crop_x},{crop_y}), size={target_width}x{target_height}")
        return (crop_x, crop_y, target_width, target_height)
    
    def _default_center_crop(
        self,
        video_width: int,
        video_height: int,
        target_aspect: Tuple[int, int]
    ) -> Tuple[int, int, int, int]:
        """CORRECT center crop: x_offset = (original_width - target_width) // 2"""
        print(f"\n  DEBUG: Input video dimensions: {video_width}x{video_height}")
        print(f"  DEBUG: Target aspect ratio: {target_aspect[0]}:{target_aspect[1]}")
        
        # Calculate target dimensions for 9:16 aspect ratio
        target_width = int(video_height * target_aspect[0] / target_aspect[1])
        target_height = video_height
        print(f"  DEBUG: Initial target: {target_width}x{target_height}")
        
        # If target is wider than video, crop height instead
        if target_width > video_width:
            print(f"  DEBUG: Target width {target_width} > video width {video_width}, cropping height instead")
            target_width = video_width
            target_height = int(video_width * target_aspect[1] / target_aspect[0])
            print(f"  DEBUG: Adjusted target: {target_width}x{target_height}")
        
        # URGENT FIX 2: Correct center crop formula
        # x = (input_width - crop_width) / 2
        # y = (input_height - crop_height) / 2
        crop_x = (video_width - target_width) // 2
        crop_y = (video_height - target_height) // 2
        print(f"  DEBUG: Before rounding - crop_x={(video_width - target_width) // 2}, crop_y={(video_height - target_height) // 2}")
        
        # Ensure even numbers for FFmpeg (required for H.264)
        crop_x = (crop_x // 2) * 2
        crop_y = (crop_y // 2) * 2
        target_width = (target_width // 2) * 2
        target_height = (target_height // 2) * 2
        
        print(f"  [OK] FINAL CENTER CROP: video={video_width}x{video_height}, crop={target_width}x{target_height}, offset=({crop_x},{crop_y})")
        
        # Sanity check
        if crop_x == 0 and video_width > target_width:
            print(f"  [WARN] WARNING: crop_x is 0 but video is wider than target! This is WRONG!")
        
        return (crop_x, crop_y, target_width, target_height)
    
    def get_crop_filter(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        crop_preview: dict = None
    ) -> str:
        """
        Generate FFmpeg crop filter based on layout mode.
        Uses crop_preview data from multi-frame deep scan if available.
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            end_time: End time in seconds
            crop_preview: Optional crop preview data with mode and face coordinates
        
        Returns:
            FFmpeg filter string for cropping
        """
        video_info = self.get_video_info(video_path)
        video_width = video_info["width"]
        video_height = video_info["height"]
        
        # Check if split_screen mode is requested
        if crop_preview and crop_preview.get("mode") == "split_screen":
            print("  -> Using SPLIT SCREEN mode (dual 1:1 crops + vstack)")
            return self._create_split_screen_filter(
                video_width,
                video_height,
                crop_preview["left_face"],
                crop_preview["right_face"]
            )
        
        # If crop_preview is available from multi-frame deep scan, use it directly
        if crop_preview and "crop_x" in crop_preview:
            crop_x = crop_preview["crop_x"]
            crop_y = crop_preview["crop_y"]
            crop_w = crop_preview["crop_width"]
            crop_h = crop_preview["crop_height"]
            
            mode = crop_preview.get("mode", "unknown")
            print(f"  -> Using crop from deep scan: mode={mode}, crop={crop_w}x{crop_h} at ({crop_x},{crop_y})")
            
            return f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"
        
        # Fallback: Standard single crop mode - detect faces in the clip
        print("  -> No crop_preview available, detecting faces...")
        face_boxes = self.detect_faces(
            video_path,
            start_time=start_time,
            end_time=end_time,
            sample_rate=30
        )
        
        # Calculate crop coordinates
        crop_x, crop_y, crop_w, crop_h = self.calculate_crop_for_916(
            face_boxes,
            video_width,
            video_height
        )
        
        # Return FFmpeg crop filter
        return f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"
    
    def _create_split_screen_filter(
        self,
        video_width: int,
        video_height: int,
        left_face: dict,
        right_face: dict
    ) -> str:
        """
        Create FFmpeg filter for split screen mode.
        Crops two 1:1 squares centered on each face and stacks them vertically.
        
        Args:
            video_width: Original video width
            video_height: Original video height
            left_face: Dict with x, y, w, h for left face
            right_face: Dict with x, y, w, h for right face
        
        Returns:
            FFmpeg filter string for split screen
        """
        # Calculate 1:1 crop size (use video height as reference)
        crop_size = video_height // 2  # Each crop is half the height for 9:16 final
        crop_size = (crop_size // 2) * 2  # Ensure even
        
        # Calculate crop positions centered on each face
        left_center_x = left_face["x"] + left_face["w"] // 2
        left_center_y = left_face["y"] + left_face["h"] // 2
        
        right_center_x = right_face["x"] + right_face["w"] // 2
        right_center_y = right_face["y"] + right_face["h"] // 2
        
        # Calculate crop offsets
        left_crop_x = max(0, min(left_center_x - crop_size // 2, video_width - crop_size))
        left_crop_y = max(0, min(left_center_y - crop_size // 2, video_height - crop_size))
        
        right_crop_x = max(0, min(right_center_x - crop_size // 2, video_width - crop_size))
        right_crop_y = max(0, min(right_center_y - crop_size // 2, video_height - crop_size))
        
        # Ensure even numbers
        left_crop_x = (left_crop_x // 2) * 2
        left_crop_y = (left_crop_y // 2) * 2
        right_crop_x = (right_crop_x // 2) * 2
        right_crop_y = (right_crop_y // 2) * 2
        
        print(f"  -> Left crop: {crop_size}x{crop_size} at ({left_crop_x},{left_crop_y})")
        print(f"  -> Right crop: {crop_size}x{crop_size} at ({right_crop_x},{right_crop_y})")
        
        # FFmpeg filter: split input, crop each stream, stack vertically
        # [0:v] splits into [left] and [right]
        # Each gets cropped to 1:1
        # vstack combines them vertically to create 9:16
        filter_str = (
            f"[0:v]split=2[left][right];"
            f"[left]crop={crop_size}:{crop_size}:{left_crop_x}:{left_crop_y}[left_crop];"
            f"[right]crop={crop_size}:{crop_size}:{right_crop_x}:{right_crop_y}[right_crop];"
            f"[left_crop][right_crop]vstack=inputs=2"
        )
        
        return filter_str
    
    def create_satisfying_split_screen_filter(
        self,
        video_width: int,
        video_height: int,
        face: dict,
        background_video_path: str,
        clip_duration: float
    ) -> str:
        """
        Create FFmpeg filter for "satisfying" split screen mode.
        Top 50%: Speaker (face-detected crop)
        Bottom 50%: Background video (Minecraft, Subway Surfers, etc.)
        
        Args:
            video_width: Original video width
            video_height: Original video height
            face: Dict with x, y, w, h for primary face
            background_video_path: Path to background video file
            clip_duration: Duration of clip in seconds
        
        Returns:
            FFmpeg filter_complex string for satisfying split screen
        """
        # Calculate 1080x960 crop size for each half (top and bottom)
        # Final output: 1080x1920 (9:16)
        crop_width = 1080
        crop_height = 960
        
        # Calculate crop position centered on face
        face_center_x = face["x"] + face["w"] // 2
        face_center_y = face["y"] + face["h"] // 2
        
        # Calculate crop offset for speaker (top half)
        crop_x = max(0, min(face_center_x - crop_width // 2, video_width - crop_width))
        crop_y = max(0, min(face_center_y - crop_height // 2, video_height - crop_height))
        
        # Ensure even numbers
        crop_x = (crop_x // 2) * 2
        crop_y = (crop_y // 2) * 2
        
        print(f"  -> Speaker crop (top 50%): {crop_width}x{crop_height} at ({crop_x},{crop_y})")
        print(f"  -> Background video (bottom 50%): {background_video_path}")
        print(f"  -> Clip duration: {clip_duration}s")
        
        # FFmpeg filter_complex:
        # [0:v] = main video (speaker)
        # [1:v] = background video
        # 
        # Steps:
        # 1. Crop speaker to 1080x960
        # 2. Loop/trim background video to match duration
        # 3. Crop/scale background to 1080x960
        # 4. Stack vertically (speaker on top, background on bottom)
        # 5. Scale to final 1080x1920
        
        filter_str = (
            # Crop speaker from main video
            f"[0:v]crop={crop_width}:{crop_height}:{crop_x}:{crop_y}[speaker];"
            
            # Process background video: loop if needed, trim to duration, scale to 1080x960
            f"[1:v]loop=loop=-1:size=1:start=0,trim=duration={clip_duration},"
            f"scale=1080:960:force_original_aspect_ratio=decrease,"
            f"pad=1080:960:(ow-iw)/2:(oh-ih)/2[background];"
            
            # Stack vertically: speaker on top, background on bottom
            f"[speaker][background]vstack=inputs=2[stacked];"
            
            # Final scale to 1080x1920 (9:16)
            f"[stacked]scale=1080:1920[out]"
        )
        
        return filter_str
    
    def close(self):
        if hasattr(self, 'face_detector') and self.face_detector is not None:
            try:
                self.face_detector.close()
            except:
                pass  # Ignore close errors


def create_reframer() -> FaceReframer:
    return FaceReframer()
