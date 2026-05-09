"""
Interview reframer: smart-pan two-speaker crop for 9:16 output.

Pipeline:
  1. Sample frames to find two face horizontal positions (left / right speaker)
  2. Use transcription segment boundaries for speaker-alternation timing
  3. Generate FFmpeg filter_complex: split -> trim -> crop -> concat

No zoom, no mouth-motion detection — pure horizontal pan + lanczos scale.
Server constraint: 2 GB RAM / 1 CPU.
"""
from __future__ import annotations

import cv2
import numpy as np
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore", category=UserWarning, module="mediapipe")

SAMPLE_INTERVAL_S: float = 0.5   # one frame every N seconds for face detection
MIN_SEGMENT_SECS: float = 1.5    # minimum speaker segment length (prevents jitter)
TWO_FACE_MIN_FRAMES: int = 3     # frames with 2 detected faces required for dynamic mode

MODEL_PATH = Path(__file__).parent.parent / "models" / "blaze_face_short_range.tflite"


# ── Shared math ──────────────────────────────────────────────────────────────

def get_face_crop_window(
    source_width: int, source_height: int, face_x_center: float
) -> Tuple[int, int, int]:
    """
    Compute 9:16 crop window shifted horizontally to center on a face.
    Returns (x_offset, crop_width, crop_height). No zoom.
    """
    crop_width = int(source_height * 9 / 16)
    if crop_width % 2 == 1:
        crop_width += 1  # libx264 requires even dimensions
    crop_height = source_height
    x_offset = int(face_x_center - crop_width / 2)
    x_offset = max(0, min(x_offset, source_width - crop_width))
    x_offset = (x_offset // 2) * 2
    return x_offset, crop_width, crop_height


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class FaceInfo:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> int:
        return self.x + self.w // 2


@dataclass
class SpeakerSegment:
    start: float    # seconds, 0-based from clip start
    end: float
    face_id: int    # 0 = left speaker, 1 = right speaker


@dataclass
class InterviewAnalysis:
    mode: str       # "dynamic_two" | "single" | "fallback"
    segments: List[SpeakerSegment]
    # face_id -> (crop_x, crop_y, crop_w, crop_h) in source pixels
    face_crops: Dict[int, Tuple[int, int, int, int]]
    video_width: int
    video_height: int
    clip_duration: float


# ── Core class ───────────────────────────────────────────────────────────────

class InterviewReframer:

    def __init__(self) -> None:
        self._detector = None
        self._mp = None
        self._init_detector()

    def _init_detector(self) -> None:
        if not MODEL_PATH.exists():
            print(f"[interview] Model not found: {MODEL_PATH}")
            return
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            opts = vision.FaceDetectorOptions(
                base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
                min_detection_confidence=0.65,
            )
            self._detector = vision.FaceDetector.create_from_options(opts)
            self._mp = mp
            print("[interview] Face detector initialized")
        except Exception as e:
            print(f"[interview] Detector init failed: {e}")

    # ── Detection ────────────────────────────────────────────────

    def _detect(self, rgb: np.ndarray) -> List[FaceInfo]:
        if self._detector is None:
            return []
        try:
            img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
            dets = self._detector.detect(img).detections
            return [
                FaceInfo(
                    x=int(d.bounding_box.origin_x),
                    y=int(d.bounding_box.origin_y),
                    w=int(d.bounding_box.width),
                    h=int(d.bounding_box.height),
                )
                for d in dets
            ]
        except Exception:
            return []

    def _assign_face_id(self, face: FaceInfo, canonical: Dict[int, float]) -> int:
        if not canonical:
            return 0
        return min(canonical, key=lambda fid: abs(face.cx - canonical[fid]))

    # ── Crop calculation ─────────────────────────────────────────

    @staticmethod
    def _face_crop(face_cx: int, vw: int, vh: int) -> Tuple[int, int, int, int]:
        """Smart pan: 9:16 window shifted to face center. Returns (cx, cy, cw, ch)."""
        x_off, cw, ch = get_face_crop_window(vw, vh, face_cx)
        return x_off, 0, cw, ch

    # ── Analysis ─────────────────────────────────────────────────

    def analyze(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        transcription_segments: Optional[List[dict]] = None,
    ) -> InterviewAnalysis:
        """
        Find face positions and build a speaker timeline from transcription segments.
        Falls back to even split when no transcription is provided.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return _fallback(end_time - start_time)

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        clip_dur = end_time - start_time

        step = max(1, int(fps * SAMPLE_INTERVAL_S))
        frame_start = int(start_time * fps)
        frame_end = min(int(end_time * fps), total_frames)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_start)

        canonical_x: Dict[int, float] = {}
        face_sightings: Dict[int, List[FaceInfo]] = {0: [], 1: []}
        two_face_count = 0
        fi = frame_start

        while fi < frame_end:
            ret, frame = cap.read()
            if not ret:
                break
            if (fi - frame_start) % step == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                raw_faces = self._detect(rgb)
                sorted_by_x = sorted(raw_faces, key=lambda f: f.cx)

                if len(sorted_by_x) >= 2 and not canonical_x:
                    canonical_x[0] = float(sorted_by_x[0].cx)
                    canonical_x[1] = float(sorted_by_x[-1].cx)

                clustered: Dict[int, FaceInfo] = {}
                for face in sorted_by_x[:2]:
                    fid = self._assign_face_id(face, canonical_x)
                    if fid not in clustered:
                        clustered[fid] = face
                        face_sightings[fid].append(face)

                if len(clustered) >= 2:
                    two_face_count += 1
            fi += 1

        cap.release()

        # Build stable face positions from median across all sightings
        face_crops: Dict[int, Tuple[int, int, int, int]] = {}
        for fid in [0, 1]:
            sightings = face_sightings[fid]
            if not sightings:
                continue
            med_cx = int(np.median([f.cx for f in sightings]))
            face_crops[fid] = self._face_crop(med_cx, vw, vh)

        # Single-speaker fallback
        if two_face_count < TWO_FACE_MIN_FRAMES or len(face_crops) < 2:
            if not face_crops:
                return _fallback(clip_dur)
            print(f"[interview] mode=single (two-face frames={two_face_count})")
            return InterviewAnalysis(
                mode="single",
                segments=[SpeakerSegment(0.0, clip_dur, next(iter(face_crops)))],
                face_crops=face_crops,
                video_width=vw,
                video_height=vh,
                clip_duration=clip_dur,
            )

        # Build timeline from transcription segments
        segs = _build_segments_from_transcription(
            transcription_segments or [], start_time, end_time, clip_dur
        )
        segs = self._smooth_timeline(segs)

        print(f"[interview] mode=dynamic_two | segments={len(segs)} | two-face frames={two_face_count}")
        for seg in segs:
            print(f"  [{seg.start:.1f}s-{seg.end:.1f}s] face_{seg.face_id}")

        return InterviewAnalysis(
            mode="dynamic_two",
            segments=segs,
            face_crops=face_crops,
            video_width=vw,
            video_height=vh,
            clip_duration=clip_dur,
        )

    # ── Timeline helpers ──────────────────────────────────────────

    @staticmethod
    def _smooth_timeline(segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """Merge short segments (<MIN_SEGMENT_SECS) into their neighbours."""
        segs = list(segments)
        for _ in range(40):
            if len(segs) <= 1:
                break
            short_idx = next(
                (i for i, s in enumerate(segs) if s.end - s.start < MIN_SEGMENT_SECS),
                None,
            )
            if short_idx is None:
                break
            if short_idx > 0:
                prev = segs[short_idx - 1]
                cur = segs[short_idx]
                segs[short_idx - 1] = SpeakerSegment(prev.start, cur.end, prev.face_id)
                segs.pop(short_idx)
            else:
                cur = segs[0]
                nxt = segs[1]
                segs[0] = SpeakerSegment(cur.start, nxt.end, nxt.face_id)
                segs.pop(1)
        return segs

    # ── FFmpeg filter generation ──────────────────────────────────

    def generate_filter_complex(self, analysis: InterviewAnalysis) -> Optional[str]:
        """
        Build FFmpeg filter_complex for smart-pan speaker crop.
        Reads [0:v], produces [out] at 1080×1920. Audio not included.
        Returns None if analysis cannot produce a valid filter.
        """
        if analysis.mode == "fallback" or not analysis.segments or not analysis.face_crops:
            return None

        segs = analysis.segments

        # Single segment — simple crop, no split/concat
        if len(segs) == 1:
            fid = segs[0].face_id
            if fid not in analysis.face_crops:
                fid = next(iter(analysis.face_crops))
            cx, cy, cw, ch = analysis.face_crops[fid]
            return f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale=1080:1920:flags=lanczos[out]"

        n = len(segs)
        parts: List[str] = []

        split_labels = "".join(f"[s{i}]" for i in range(n))
        parts.append(f"[0:v]split={n}{split_labels}")

        valid: List[int] = []
        for i, seg in enumerate(segs):
            fid = seg.face_id
            if fid not in analysis.face_crops:
                fid = next(iter(analysis.face_crops), None)
            if fid is None:
                continue
            cx, cy, cw, ch = analysis.face_crops[fid]
            parts.append(
                f"[s{i}]trim=start={seg.start:.3f}:end={seg.end:.3f},"
                f"setpts=PTS-STARTPTS,"
                f"crop={cw}:{ch}:{cx}:{cy},"
                f"scale=1080:1920:flags=lanczos[v{i}]"
            )
            valid.append(i)

        if not valid:
            return None

        concat_in = "".join(f"[v{i}]" for i in valid)
        parts.append(f"{concat_in}concat=n={len(valid)}:v=1:a=0[out]")
        return ";".join(parts)

    def close(self) -> None:
        if self._detector:
            try:
                self._detector.close()
            except Exception:
                pass


# ── Factory ──────────────────────────────────────────────────────────────────

def create_interview_reframer() -> InterviewReframer:
    return InterviewReframer()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_segments_from_transcription(
    transcription_segments: List[dict],
    clip_start: float,
    clip_end: float,
    clip_dur: float,
) -> List[SpeakerSegment]:
    """
    Build speaker alternation using transcription segment boundaries.
    Each transcript segment flips face_id: 0, 1, 0, 1, …
    """
    clip_segs = []
    for seg in transcription_segments:
        s = seg.get("start", 0)
        e = seg.get("end", 0)
        if e > clip_start and s < clip_end:
            clip_segs.append({
                "start": max(s - clip_start, 0.0),
                "end": min(e - clip_start, clip_dur),
            })

    if not clip_segs:
        # No transcription: even split between two speakers
        mid = clip_dur / 2
        return [SpeakerSegment(0.0, mid, 0), SpeakerSegment(mid, clip_dur, 1)]

    result = []
    for i, seg in enumerate(clip_segs):
        result.append(SpeakerSegment(seg["start"], seg["end"], i % 2))
    return result


def _fallback(clip_dur: float) -> InterviewAnalysis:
    return InterviewAnalysis(
        mode="fallback",
        segments=[SpeakerSegment(0.0, clip_dur, -1)],
        face_crops={},
        video_width=0,
        video_height=0,
        clip_duration=clip_dur,
    )
