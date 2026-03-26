import os
import json
import random
import time
from typing import List, Dict, Optional

# Optional imports for AI providers (not needed for mock mode)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False
    OpenAI = None


class MockAnalyzer:
    """Mock analyzer for testing without API keys"""
    
    def __init__(self, provider: str = "mock"):
        self.provider = "mock"
    
    def analyze_transcription(self, transcription: str, video_duration: float, max_clips: int = 5) -> List[Dict]:
        clips = []

        # Generate mock clips based on video duration
        clip_duration = 30.0
        max_clips = min(max_clips, int(video_duration / clip_duration))
        
        titles = [
            "Epic Opening Hook",
            "Mind-Blowing Revelation",
            "Powerful Conclusion",
            "Golden Moment",
            "Viral-Worthy Segment"
        ]
        
        reasons = [
            "Strong emotional hook that grabs attention immediately",
            "Surprising insight that creates curiosity and engagement",
            "Powerful delivery with high energy and memorable content",
            "Perfect pacing with actionable value for viewers",
            "Authentic moment that resonates with the audience"
        ]
        
        hooks = [
            "WAIT FOR IT",
            "THIS IS INSANE",
            "MIND BLOWN",
            "WATCH THIS",
            "YOU WON'T BELIEVE"
        ]
        
        for i in range(max_clips):
            start_time = i * clip_duration
            end_time = min(start_time + clip_duration, video_duration)
            
            if end_time - start_time < 10:  # Skip if less than 10 seconds
                continue
            
            clips.append({
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "title": titles[i % len(titles)],
                "description": f"This clip will blow your mind! {reasons[i % len(reasons)]} Don't miss it! 🔥",
                "hashtags": ["#viral", "#fyp", "#trending", "#motivation", "#mindset", "#success"],
                "reason": reasons[i % len(reasons)],
                "virality_score": random.randint(7, 10),
                "hook": hooks[i % len(hooks)],
                "emojis": ["🔥", "💯"]
            })
        
        # If no clips generated, create at least one
        if not clips and video_duration >= 10:
            clips.append({
                "start_time": 0.0,
                "end_time": min(30.0, video_duration),
                "title": "Viral Clip",
                "reason": "Engaging content with high viral potential",
                "virality_score": 8,
                "hook": "WATCH THIS"
            })
        
        return clips


class ViralClipAnalyzer:
    def __init__(self, provider: str = "openai"):
        """
        Initialize analyzer with OpenAI GPT-4o.
        """
        self.provider = "openai"
        self.openai_client = None
        self.active_provider = None
        
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.openai_model = "gpt-4o-mini"
                self.active_provider = "openai"
                print(f"[OK] OpenAI client initialized with model: {self.openai_model}")
            except Exception as e:
                print(f"[WARN] OpenAI initialization failed: {e}")
        
        if not self.active_provider:
            raise ValueError(
                "No AI provider available. Please set OPENAI_API_KEY. "
                "Install: pip install openai"
            )
        
        print(f"[INFO] Active Provider: {self.active_provider.upper()}")
    
    def generate_hook(self, clip_title: str, clip_reason: str, transcription_segment: str) -> str:
        prompt = f"""Generate a SHORT, attention-grabbing hook text (3-5 words MAX) for a viral video clip.

Clip Title: {clip_title}
Why It's Viral: {clip_reason}
Content Preview: {transcription_segment[:200]}

The hook should:
- Be 3-5 words MAXIMUM
- Create curiosity or urgency
- Use powerful emotional words
- Be in ALL CAPS format
- Grab attention immediately

Examples of good hooks:
- "WAIT FOR IT"
- "THIS CHANGED EVERYTHING"
- "YOU WON'T BELIEVE THIS"
- "THE SECRET REVEALED"
- "MIND = BLOWN"

Return ONLY the hook text, nothing else."""

        hook = None
        
        if self.openai_client:
            for attempt in range(1, 4):
                try:
                    response = self.openai_client.chat.completions.create(
                        model=self.openai_model,
                        messages=[
                            {"role": "system", "content": "You are a viral content expert. Generate short, punchy hooks."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.8,
                        max_tokens=20
                    )
                    hook = response.choices[0].message.content.strip()
                    print(f"[OK] OpenAI hook generated: {hook}")
                    break
                except Exception as e:
                    wait = 2 ** (attempt - 1)
                    print(f"[WARN] OpenAI hook attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
        
        # Final fallback to default
        if not hook:
            print("→ Using default hook")
            return "WATCH THIS"
        
        # Clean up hook
        hook = hook.strip('"\'')
        hook = hook.upper()
        
        words = hook.split()
        if len(words) > 5:
            hook = ' '.join(words[:5])
        
        return hook
    
    def analyze_transcription(self, transcription: str, video_duration: float, max_clips: int = 5) -> List[Dict]:
        """
        Analyze transcription with hybrid provider logic.
        Tries active provider first, falls back to secondary if available.
        """
        prompt = f"""You are an expert viral content strategist. Analyze this video transcription and find the TOP {max_clips} most viral-worthy clips.

Video Duration: {video_duration} seconds
Transcription:
{transcription}

FIND CLIPS BASED ON:
- Semantic hooks (controversial statements, bold claims, shocking revelations)
- Emotional peaks (anger, excitement, surprise, inspiration)
- Complete thoughts (not mid-sentence cuts)
- Pattern interrupts (unexpected twists, "wait what?" moments)
- Actionable insights ("here's how to...")

CLIP LENGTH RULES:
- Minimum: 15 seconds (complete thought)
- Maximum: 60 seconds (attention span)
- Variable length based on content (NOT fixed 30s blocks)
- Each clip must be a COMPLETE idea or story arc

For each clip, provide:
1. start_time: When the clip starts (seconds)
2. end_time: When the clip ends (seconds) - based on natural pause/completion
3. title: Catchy, curiosity-driven title (5-8 words)
4. description: Engaging description for social media post (2-3 sentences, 150-200 chars)
5. hashtags: Array of 5-8 relevant hashtags (e.g., ["#viral", "#motivation", "#mindset"])
6. reason: Why this will go viral (be specific)
7. virality_score: 1-10 (be honest, not everything is a 9)
8. hook_text: 3-5 word ALL CAPS hook that appears at top of video
9. emojis: Array of 2-3 relevant emojis that match the emotion/topic (e.g., ["🔥", "💰", "😱"])
10. content_preview: Brief excerpt of what's said

Return ONLY valid JSON array:
[
  {{
    "start_time": 0.0,
    "end_time": 45.5,
    "title": "The Secret They Don't Want You To Know",
    "description": "This revelation will change how you see everything. Watch till the end! 🤯",
    "hashtags": ["#viral", "#mindblown", "#truth", "#fyp", "#motivation"],
    "reason": "Controversial claim with emotional hook",
    "virality_score": 8,
    "hook_text": "WAIT FOR THIS",
    "emojis": ["🤯", "🔥"],
    "content_preview": "Brief excerpt..."
  }}
]

Return ONLY the JSON array, no other text."""

        content = None
        clips = None
        
        if self.openai_client:
            for attempt in range(1, 4):
                try:
                    print(f"Calling OpenAI API (attempt {attempt}/3) with model: {self.openai_model}")
                    response = self.openai_client.chat.completions.create(
                        model=self.openai_model,
                        messages=[
                            {"role": "system", "content": "You are a viral content expert. Always respond with ONLY a valid JSON array, no other text or markdown."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        response_format={"type": "json_object"}
                    )
                    content = response.choices[0].message.content
                    print(f"[OK] OpenAI API response received ({len(content)} chars)")
                    result = json.loads(content)
                    if isinstance(result, dict) and "clips" in result:
                        clips = result["clips"]
                    elif isinstance(result, list):
                        clips = result
                    else:
                        clips = [result]
                    print(f"[OK] Parsed {len(clips)} clips from OpenAI")
                    break
                except Exception as e:
                    wait = 2 ** (attempt - 1)
                    print(f"[WARN] OpenAI analysis attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
        
        # Final check
        if not clips:
            raise Exception("OpenAI analysis failed after 3 attempts. Check OPENAI_API_KEY and network.")
        
        validated_clips = self._validate_clips(clips, video_duration, max_clips=max_clips)
        return validated_clips
    
    def _parse_fallback(self, content: str) -> List[Dict]:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                if "clips" in result:
                    return result["clips"]
                return [result]
        except:
            pass
        
        return []
    
    def _validate_clips(self, clips: List[Dict], video_duration: float, max_clips: int = 5) -> List[Dict]:
        validated = []
        
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            
            start = float(clip.get("start_time", 0))
            end = float(clip.get("end_time", 30))
            
            # Validate bounds
            if start < 0:
                start = 0
            if end > video_duration:
                end = video_duration
            
            # Ensure minimum 15s, maximum 60s
            duration = end - start
            if duration < 15:
                end = min(start + 15, video_duration)
            if duration > 60:
                end = start + 60
            
            # Ensure clip fits in video
            if end > video_duration:
                end = video_duration
                start = max(0, end - 30)  # Fallback to 30s if needed
            
            title = clip.get("title", "Viral Clip")
            reason = clip.get("reason", "High engagement potential")
            content_preview = clip.get("content_preview", "")
            
            # Use AI-generated hook if available, otherwise generate one
            hook = clip.get("hook_text", "")
            if not hook:
                hook = self.generate_hook(title, reason, content_preview)
            
            # Get emojis from AI or default
            emojis = clip.get("emojis", ["🔥", "💯"])
            if not isinstance(emojis, list):
                emojis = ["🔥", "💯"]
            
            validated.append({
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "title": title,
                "reason": reason,
                "virality_score": min(10, max(1, int(clip.get("virality_score", 7)))),
                "hook": hook,
                "emojis": emojis[:3]  # Max 3 emojis
            })
        
        validated.sort(key=lambda x: x["virality_score"], reverse=True)
        return validated[:max_clips]


def create_analyzer(provider: str = "openai"):
    if provider.lower() == "mock":
        return MockAnalyzer()
    return ViralClipAnalyzer(provider=provider)
