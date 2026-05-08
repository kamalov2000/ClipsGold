"""
Interview reframer: dynamic two-speaker face crop for 9:16 output.

Pipeline:
  1. Sample frames every SAMPLE_INTERVAL_S seconds via OpenCV
  2. Detect all faces with MediaPipe Face Detection (blaze_face_short_range)
  3. Cluster faces into two tracks: face_0 = left speaker, face_1 = right speaker
  4. Detect active speaker by comparing mouth-region pixel motion between frames
  5. Build + smooth speaker timeline (min MIN_SEGMENT_SECS per segment)
  6. Generate FFmpeg filter_complex: split -> trim -> crop -> concat

Server constraint: 2 GB RAM / 1 CPU — no PyTorch / pyannote.audio.
Requires only mediapipe (already in requirements.txt).
"""
from __future__ import annotations

import cv2
import numpy as np
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore", category=UserWarning, module="mediapipe")

SAMPLE_INTERVAL_S: float = 0.5   # analyze one frame every N seconds
MIN_SEGMENT_SECS: float = 1.5    # minimum speaker segment (prevents rapid jitter)
TWO_FACE_MIN_FRAMES: int = 3     # frames with 2 detected faces required for dynamic mode

MODEL_PATH = Path(__file__).parent.parent / "models" / "blaze_face_short_range.tflite"


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class FaceInfo:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2

    def mouth_roi(self, frame_h: int, frame_w: int) -> Tuple[int, int, int, int]:
        """Returns (y1, y2, x1, x2) of the mouth region."""
        y1 = max(0, self.y + int(self.h * 0.60))
        y2 = min(frame_h - 1, self.y + int(self.h * 0.85))
        x1 = max(0, self.x + int(self.w * 0.20))
        x2 = min(frame_w - 1, self.x + int(self.w * 0.80))
        return (y1, y2, x1, x2)


@dataclass
class SpeakerSegment:
    start: float    # seconds, 0-based from clip start
    end: float
    face_id: int    # 0 = left speaker, 1 = right speaker


@dataclass
class InterviewAnalysis:
    mode: str       # "dynamic_two" | "single" | "fallback"
    segments: List[SpeakerSegment]
    face_crops: Dict[int, Tuple[int, int, int, int]]  # face_id -> (cx, cy, cw, ch)
    video_width: int
    video_height: int
    clip_duration: float


# ── Core class ──────────────────────────────────────────────────────────────

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
                min_detection_confidence=0.45,
            )
            self._detector = vision.FaceDetector.create_from_options(opts)
            self._mp = mp
            print("[interview] Face detector initialized")
        except Exception as e:
            print(f"[interview] Detector init failed: {e}")

    # ── Detection helpers ────────────────────────────────────────────────

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

    @staticmethod
    def _mouth_motion(
        prev_gray: np.ndarray,
        curr_gray: np.ndarray,
        face: FaceInfo,
        fh: int,
        fw: int,
    ) -> float:
        """Mean absolute difference in face's mouth region between two grayscale frames."""
        y1, y2, x1, x2 = face.mouth_roi(fh, fw)
        if y2 <= y1 or x2 <= x1:
            return 0.0
        roi_p = prev_gray[y1:y2, x1:x2]
        roi_c = curr_gray[y1:y2, x1:x2]
        if roi_p.shape != roi_c.shape or roi_p.size == 0:
            return 0.0
        return float(np.mean(cv2.absdiff(roi_p, roi_c)))

    @staticmethod
    def _calc_crop(face: FaceInfo, vw: int, vh: int) -> Tuple[int, int, int, int]:
        """9:16 crop centered on face. Returns (crop_x, crop_y, crop_w, crop_h)."""
        cw = int(vh * 9 / 16)
        ch = vh
        if cw > vw:
            cw = vw
            ch = int(vw * 16 / 9)
        # Enforce minimum crop size — prevents over-zoom on small sources
        cw = max(cw, min(720, vw))
        ch = max(ch, min(1280, vh))
        # Center face horizontally; face center at 50% height (less aggressive zoom)
        cx = face.cx - cw // 2
        cy = face.cy - ch // 2
        cx = max(0, min(cx, vw - cw))
        cy = max(0, min(cy, vh - ch))
        # even values required by libx264
        return ((cx // 2) * 2, (cy // 2) * 2, (cw // 2) * 2, (ch // 2) * 2)

    def _assign_face_id(self, face: FaceInfo, canonical: Dict[int, float]) -> int:
        """Match face to nearest canonical speaker by horizontal position."""
        if not canonical:
            return 0
        return min(canonical, key=lambda fid: abs(face.cx - canonical[fid]))

    # ── Analysis ─────────────────────────────────────────────────────────

    def analyze(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
    ) -> InterviewAnalysis:
        """
        Analyze clip to build a speaker timeline.
        Returns InterviewAnalysis describing mode, segments, and per-speaker crop coords.
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

        # canonical_x: face_id -> established center_x (set on first two-face frame)
        canonical_x: Dict[int, float] = {}
        face_sightings: Dict[int, List[FaceInfo]] = {0: [], 1: []}
        samples: List[Tuple[float, int]] = []   # (rel_time, active_face_id)
        two_face_count = 0

        prev_gray: Optional[np.ndarray] = None
        fi = frame_start

        while fi < frame_end:
            ret, frame = cap.read()
            if not ret:
                break

            if (fi - frame_start) % step == 0:
                rel_t = (fi - frame_start) / fps
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                raw_faces = self._detect(rgb)
                sorted_by_x = sorted(raw_faces, key=lambda f: f.cx)

                # Establish canonical left/right positions from first two-face frame
                if len(sorted_by_x) >= 2 and not canonical_x:
                    canonical_x[0] = float(sorted_by_x[0].cx)
                    canonical_x[1] = float(sorted_by_x[-1].cx)

                # Assign face IDs to detected faces
                clustered: Dict[int, FaceInfo] = {}
                for face in sorted_by_x[:2]:
                    fid = self._assign_face_id(face, canonical_x)
                    if fid not in clustered:
                        clustered[fid] = face
                        face_sightings[fid].append(face)

                if len(clustered) >= 2:
                    two_face_count += 1

                # Active speaker = face with most mouth motion since last sample
                active_id = -1
                if prev_gray is not None and len(clustered) >= 2:
                    scores = {
                        fid: self._mouth_motion(prev_gray, gray, face, vh, vw)
                        for fid, face in clustered.items()
                    }
                    active_id = max(scores, key=scores.__getitem__)
                elif len(clustered) == 1:
                    active_id = next(iter(clustered))

                samples.append((rel_t, active_id))
                prev_gray = gray

            fi += 1

        cap.release()

        if not samples:
            return _fallback(clip_dur)

        # Build stable crop for each face using median position across all sightings
        face_crops: Dict[int, Tuple[int, int, int, int]] = {}
        for fid in [0, 1]:
            sightings = face_sightings[fid]
            if not sightings:
                continue
            med_cx = int(np.median([f.cx for f in sightings]))
            med_cy = int(np.median([f.cy for f in sightings]))
            med_w = int(np.median([f.w for f in sightings]))
            med_h = int(np.median([f.h for f in sightings]))
            med_face = FaceInfo(
                x=med_cx - med_w // 2,
                y=med_cy - med_h // 2,
                w=med_w,
                h=med_h,
            )
            face_crops[fid] = self._calc_crop(med_face, vw, vh)

        # Single-speaker fallback: not enough two-face frames
        if two_face_count < TWO_FACE_MIN_FRAMES or len(face_crops) < 2:
            if not face_crops:
                return _fallback(clip_dur)
            print(f"[interview] mode=single (two-face frames={two_face_count})")
            return InterviewAnalysis(
                mode="single",
                segments=[SpeakerSegment(0.0, clip_dur, 0)],
                face_crops=face_crops,
                video_width=vw,
                video_height=vh,
                clip_duration=clip_dur,
            )

        # Build smoothed speaker timeline
        raw_segs = self._build_timeline(samples, clip_dur)
        smooth_segs = self._smooth_timeline(raw_segs)

        print(f"[interview] mode=dynamic_two | segments={len(smooth_segs)} | two-face frames={two_face_count}")
        for seg in smooth_segs:
            print(f"  [{seg.start:.1f}s-{seg.end:.1f}s] face_{seg.face_id}")

        return InterviewAnalysis(
            mode="dynamic_two",
            segments=smooth_segs,
            face_crops=face_crops,
            video_width=vw,
            video_height=vh,
            clip_duration=clip_dur,
        )

    # ── Timeline construction ─────────────────────────────────────────────

    @staticmethod
    def _build_timeline(
        samples: List[Tuple[float, int]], clip_dur: float,
    ) -> List[SpeakerSegment]:
        if not samples:
            return []
        segs: List[SpeakerSegment] = []
        t0, fid0 = samples[0]
        if fid0 < 0:
            fid0 = 0
        for t, fid in samples[1:]:
            if fid < 0:
                fid = fid0   # keep current speaker on detection failure
            if fid != fid0:
                segs.append(SpeakerSegment(t0, t, fid0))
                t0, fid0 = t, fid
        segs.append(SpeakerSegment(t0, clip_dur, fid0))
        return segs

    @staticmethod
    def _smooth_timeline(segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """Iteratively merge the first short segment into its neighbor until stable."""
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
                # Merge into previous segment
                prev = segs[short_idx - 1]
                cur = segs[short_idx]
                segs[short_idx - 1] = SpeakerSegment(prev.start, cur.end, prev.face_id)
                segs.pop(short_idx)
            else:
                # First segment: merge into the next
                cur = segs[0]
                nxt = segs[1]
                segs[0] = SpeakerSegment(cur.start, nxt.end, nxt.face_id)
                segs.pop(1)
        return segs

    # ── FFmpeg filter generation ──────────────────────────────────────────

    def generate_filter_complex(self, analysis: InterviewAnalysis) -> Optional[str]:
        """
        Build FFmpeg filter_complex for dynamic speaker crop.

        The returned string:
          - reads from [0:v]
          - produces [out] at 1080x1920
          - does NOT include audio (caller maps [0:a] separately)

        Returns None if analysis cannot produce a valid filter.
        """
        if analysis.mode == "fallback" or not analysis.segments or not analysis.face_crops:
            return None

        segs = analysis.segments

        # Single segment — simple crop, no split/concat needed
        if len(segs) == 1:
            fid = segs[0].face_id
            if fid not in analysis.face_crops:
                fid = next(iter(analysis.face_crops))
            cx, cy, cw, ch = analysis.face_crops[fid]
            return f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale=1080:1920:flags=lanczos[out]"

        n = len(segs)
        parts: List[str] = []

        # Split input into N streams (one per speaker segment)
        split_labels = "".join(f"[s{i}]" for i in range(n))
        parts.append(f"[0:v]split={n}{split_labels}")

        # Trim + crop + scale each segment
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

        # Concat all valid segments
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


def _fallback(clip_dur: float) -> InterviewAnalysis:
    return InterviewAnalysis(
        mode="fallback",
        segments=[SpeakerSegment(0.0, clip_dur, -1)],
        face_crops={},
        video_width=0,
        video_height=0,
        clip_duration=clip_dur,
    )
