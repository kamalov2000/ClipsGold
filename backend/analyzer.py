import os
import json
import random
import re
import time
from typing import List, Dict, Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None  # type: ignore

from services.claude_llm import CLAUDE_ANALYSIS_MODEL


# ── System prompt shared across all Claude calls ──────────────
_SYSTEM_PROMPT = (
    "You are an expert viral content analyst specialising in short-form video "
    "for TikTok, Instagram Reels, and YouTube Shorts. "
    "You identify moments with the highest chance of being shared, saved, and driving follower growth. "
    "Always respond with valid JSON only — no markdown fences, no explanations outside the JSON."
)


def _build_analysis_prompt(
    transcription: str,
    video_duration: float,
    clip_count: int,
) -> str:
    return f"""Analyze the transcript below and identify exactly {clip_count} viral-worthy moments (no more, no fewer).

Video duration: {video_duration:.1f} seconds ({video_duration / 60:.1f} minutes)

## TRANSCRIPT:
{transcription}

## EVALUATION — each clip must score strongly on at least one dimension:

EMOTION (pick the best match):
  - laugh        : humour or absurdity that catches the viewer off guard
  - surprise     : information that defies expectations or common knowledge
  - conflict     : disagreement, confrontation, or tension between parties
  - mood_shift   : sharp transition from calm to intense, or serious to funny

STRUCTURE (pick the best match):
  - twist             : the ending subverts or contradicts the setup
  - counter_intuitive : a claim that sounds wrong but turns out to be true
  - story_arc         : complete narrative — setup, escalation, resolution — within one clip

HOOK QUALITY (pick the best match):
  - question    : clip opens with a compelling question or unsolved mystery
  - provocation : clip opens with a bold, controversial, or challenging statement
  - punchline   : clip builds to a clear, memorable conclusion or reveal

## CLIP RULES:
- Length: minimum 30 seconds, maximum 90 seconds
- CRITICAL: No overlapping clips — each clip's start_time must be strictly after the previous clip's end_time
- Start at a natural sentence or pause boundary
- End at a natural sentence ending or pause
- Spread clips across the full video — do not cluster them at the start
- Prefer diversity: vary emotion types and moments from different parts of the video

## OUTPUT FORMAT (return ONLY this JSON object, no other text):
{{
  "clips": [
    {{
      "start_time": 12.5,
      "end_time": 58.3,
      "title": "Catchy title in 5-8 words",
      "opening_line": "Exact first sentence spoken in this clip",
      "hook": "3-5 WORD ALL-CAPS HOOK FOR VIDEO OVERLAY",
      "moment_type": "emotion",
      "emotion_trigger": "surprise",
      "structure_type": "counter_intuitive",
      "hook_type": "provocation",
      "best_platform": "TikTok",
      "virality_score": 8,
      "reason": "Specific explanation of why this will go viral — what makes it shareable (2-3 sentences).",
      "emojis": ["😱", "🔥"]
    }}
  ]
}}

Identify exactly {clip_count} highest-potential moments. Use precise timestamps aligned to sentence boundaries.
The JSON \"clips\" array MUST contain exactly {clip_count} objects."""


# ── Mock analyzer (no API calls — for testing) ────────────────

class MockAnalyzer:
    """Returns deterministic fake clips for pipeline testing."""

    def __init__(self, provider: str = "mock"):
        self.provider = "mock"

    def analyze_transcription(
        self, transcription: str, video_duration: float, max_clips: int = 5
    ) -> List[Dict]:
        clip_duration = 45.0
        count = min(max_clips, max(1, int(video_duration / clip_duration)))

        titles = [
            "Epic Opening Hook",
            "Mind-Blowing Revelation",
            "Powerful Conclusion",
            "Golden Moment",
            "Viral-Worthy Segment",
        ]
        reasons = [
            "Strong emotional hook that grabs attention immediately",
            "Surprising insight that creates curiosity and engagement",
            "Powerful delivery with high energy and memorable content",
            "Perfect pacing with actionable value for viewers",
            "Authentic moment that resonates with the audience",
        ]
        hooks = ["WAIT FOR IT", "THIS IS INSANE", "MIND BLOWN", "WATCH THIS", "YOU WON'T BELIEVE"]
        platforms = ["TikTok", "Reels", "Shorts"]

        clips = []
        for i in range(count):
            start = i * clip_duration
            end = min(start + clip_duration, video_duration)
            if end - start < 10:
                continue
            clips.append({
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "title": titles[i % len(titles)],
                "opening_line": "Here's the moment you've been waiting for...",
                "hook": hooks[i % len(hooks)],
                "moment_type": "emotion",
                "emotion_trigger": "surprise",
                "structure_type": "story_arc",
                "hook_type": "provocation",
                "best_platform": platforms[i % len(platforms)],
                "reason": reasons[i % len(reasons)],
                "virality_score": random.randint(7, 10),
                "emojis": ["🔥", "💯"],
            })

        if not clips and video_duration >= 10:
            clips.append({
                "start_time": 0.0,
                "end_time": min(45.0, video_duration),
                "title": "Viral Clip",
                "opening_line": "You won't believe what happens next...",
                "hook": "WATCH THIS",
                "moment_type": "emotion",
                "emotion_trigger": "surprise",
                "structure_type": "story_arc",
                "hook_type": "provocation",
                "best_platform": "TikTok",
                "reason": "Engaging content with high viral potential",
                "virality_score": 8,
                "emojis": ["🔥", "💯"],
            })

        return clips


# ── Claude-powered analyzer ───────────────────────────────────

class ClaudeAnalyzer:
    """Viral clip analyzer powered by Claude (Anthropic)."""

    _MODEL = CLAUDE_ANALYSIS_MODEL

    def __init__(self, provider: str = "claude"):
        self.provider = "claude"

        if not ANTHROPIC_AVAILABLE:
            raise ValueError(
                "anthropic SDK is not installed. Run: pip install 'anthropic>=0.40.0'"
            )

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        print(f"[OK] ClaudeAnalyzer initialised: {self._MODEL}")

    # ── Public interface (identical to original ViralClipAnalyzer) ──

    def generate_hook(
        self,
        clip_title: str,
        clip_reason: str,
        transcription_segment: str,
    ) -> str:
        """Generate a 3-5 word ALL-CAPS overlay hook via Claude."""
        prompt = (
            f"Generate a 3-5 word ALL CAPS hook for a viral video overlay.\n\n"
            f"Title: {clip_title}\n"
            f"Why viral: {clip_reason}\n"
            f"Content excerpt: {transcription_segment[:200]}\n\n"
            "Return ONLY the hook text — nothing else.\n"
            "Examples: WAIT FOR THIS | YOU WON'T BELIEVE | THIS CHANGES EVERYTHING"
        )
        try:
            message = self.client.messages.create(
                model=self._MODEL,
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip().strip("\"'").upper()
            words = raw.split()
            return " ".join(words[:5]) if words else "WATCH THIS"
        except Exception as e:
            print(f"[WARN] generate_hook failed: {e}")
            return "WATCH THIS"

    def analyze_transcription(
        self,
        transcription: str,
        video_duration: float,
        max_clips: int = 5,
    ) -> List[Dict]:
        """
        Find viral moments in the transcript using Claude.

        Respects caller's ``max_clips`` (clamped to 1–15): the prompt asks for
        exactly that many clips; results are capped to the same count.
        """
        clip_count = max(1, min(15, int(max_clips)))

        prompt = _build_analysis_prompt(transcription, video_duration, clip_count)

        print(
            f"[DEBUG] ClaudeAnalyzer.analyze_transcription: "
            f"requesting exactly {clip_count} clips, "
            f"video={video_duration:.1f}s"
        )

        last_error: Exception = Exception("No attempts made")

        for attempt in range(1, 4):
            try:
                print(f"[INFO] Claude API call (attempt {attempt}/3) …")
                message = self.client.messages.create(
                    model=self._MODEL,
                    max_tokens=4096,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_text = message.content[0].text
                print(f"[OK] Claude responded ({len(raw_text)} chars)")

                clips = self._parse_json_response(raw_text)
                if clips:
                    print(f"[OK] Parsed {len(clips)} clips from Claude")
                    return self._validate_clips(clips, video_duration, clip_count)

                print("[WARN] Claude returned an empty clips list — retrying …")
                last_error = ValueError("Empty clips list in Claude response")

            except anthropic.RateLimitError as exc:
                wait = 2 ** attempt
                print(f"[WARN] Rate-limited (attempt {attempt}/3): {exc}. Retry in {wait}s …")
                last_error = exc
                time.sleep(wait)

            except anthropic.APIStatusError as exc:
                wait = 2 ** (attempt - 1)
                print(f"[WARN] API error {exc.status_code} (attempt {attempt}/3): {exc.message}. Retry in {wait}s …")
                last_error = exc
                time.sleep(wait)

            except Exception as exc:
                wait = 2 ** (attempt - 1)
                print(f"[WARN] Unexpected error (attempt {attempt}/3): {exc}. Retry in {wait}s …")
                last_error = exc
                time.sleep(wait)

        raise Exception(
            f"Claude analysis failed after 3 attempts. Last error: {last_error}. "
            "Check ANTHROPIC_API_KEY and network connectivity."
        )

    # ── JSON parsing with multiple fallback strategies ────────

    def _parse_json_response(self, content: str) -> List[Dict]:
        """Try to extract a clips list from Claude's raw text output."""

        # Strategy 1: direct parse (Claude returns clean JSON most of the time)
        try:
            return self._extract_clips(json.loads(content.strip()))
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: ```json ... ``` fence
        m = re.search(r"```json\s*([\s\S]*?)\s*```", content)
        if m:
            try:
                return self._extract_clips(json.loads(m.group(1)))
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: plain ``` ... ``` fence
        m = re.search(r"```\s*([\s\S]*?)\s*```", content)
        if m:
            try:
                return self._extract_clips(json.loads(m.group(1)))
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 4: find the outermost { … } object in the text
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return self._extract_clips(json.loads(m.group(0)))
            except (json.JSONDecodeError, ValueError):
                pass

        print(
            f"[WARN] All JSON parse strategies failed. "
            f"Response preview: {content[:300]!r}"
        )
        return []

    def _extract_clips(self, parsed) -> List[Dict]:
        """Pull the clips list out of any parsed JSON shape."""
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("clips", "viral_clips", "moments", "results", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            # Single-clip object returned directly
            if "start_time" in parsed and "end_time" in parsed:
                return [parsed]
        raise ValueError(f"Cannot extract clips list from {type(parsed)}")

    # ── Validation & normalisation ────────────────────────────

    def _validate_clips(
        self,
        clips: List[Dict],
        video_duration: float,
        max_clips: int = 15,
    ) -> List[Dict]:
        """
        Validate timestamps, enforce 30-90s bounds, fill missing fields.
        Output dict is a superset of the original format — all existing
        pipeline keys are present so nothing in main.py breaks.
        """
        validated: List[Dict] = []

        for clip in clips:
            if not isinstance(clip, dict):
                continue

            try:
                start = float(clip.get("start_time", 0))
                end = float(clip.get("end_time", start + 45))
            except (TypeError, ValueError):
                continue

            # Clamp to video bounds
            start = max(0.0, min(start, video_duration - 30))
            end = max(start + 30, min(end, video_duration))

            # Enforce 30-90 second clip length
            duration = end - start
            if duration < 30:
                end = min(start + 30, video_duration)
            if duration > 90:
                end = start + 90
            if end > video_duration:
                end = video_duration
                start = max(0.0, end - 30)

            # hook — 3-5 word ALL-CAPS overlay (required by subtitle_generator)
            hook = str(clip.get("hook") or "").strip().upper()
            # Discard hooks that look like full sentences (> 6 words)
            if not hook or len(hook.split()) > 6:
                title = str(clip.get("title", "Viral Clip"))
                reason = str(clip.get("reason", ""))
                hook = self.generate_hook(title, reason, "")

            # emojis
            emojis = clip.get("emojis", ["🔥", "💯"])
            if not isinstance(emojis, list):
                emojis = ["🔥", "💯"]
            emojis = [str(e) for e in emojis[:3]]

            try:
                score = min(10, max(1, int(float(clip.get("virality_score", 7)))))
            except (TypeError, ValueError):
                score = 7

            validated.append({
                # ── Fields required by existing pipeline ──────────────
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "title": str(clip.get("title", "Viral Clip")),
                "reason": str(clip.get("reason", "High engagement potential")),
                "virality_score": score,
                "hook": hook,
                "emojis": emojis,
                # ── New enrichment fields (additive — pipeline ignores unknowns) ──
                "opening_line": str(clip.get("opening_line", "")),
                "moment_type": str(clip.get("moment_type", "emotion")),
                "emotion_trigger": str(clip.get("emotion_trigger", "")),
                "structure_type": str(clip.get("structure_type", "")),
                "hook_type": str(clip.get("hook_type", "")),
                "best_platform": str(clip.get("best_platform", "TikTok")),
            })

        # Sort by start_time for overlap detection
        validated.sort(key=lambda x: x["start_time"])

        # Remove clips that overlap the previous clip by more than 5 seconds
        deduped: List[Dict] = []
        for clip in validated:
            if not deduped:
                deduped.append(clip)
                continue
            prev_end = deduped[-1]["end_time"]
            overlap = max(0.0, prev_end - clip["start_time"])
            if overlap > 5.0:
                print(f"  [OVERLAP] Dropped '{clip['title'][:30]}' (start={clip['start_time']:.1f}s, overlap={overlap:.1f}s)")
                continue
            deduped.append(clip)

        deduped.sort(key=lambda x: x["virality_score"], reverse=True)
        return deduped[:max_clips]


# Backward-compatible alias — existing code that imports ViralClipAnalyzer still works
ViralClipAnalyzer = ClaudeAnalyzer


def create_analyzer(provider: str = "claude") -> "ClaudeAnalyzer | MockAnalyzer":
    """
    Factory for clip analyzers.

    - "mock"              → MockAnalyzer  (no API, for testing)
    - "claude" / "openai" → ClaudeAnalyzer (legacy alias "openai" → Claude)
    """
    if provider.lower() == "mock":
        return MockAnalyzer()
    return ClaudeAnalyzer(provider=provider)
