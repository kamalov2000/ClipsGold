"""
Viral Scout: AI-powered viral moment detection using Claude (Anthropic).
Analyzes full transcripts to identify high-impact segments with emotional hooks.
"""

import json
import os
import re
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv

from services.claude_llm import claude_completion_async

load_dotenv()

VIRAL_SCOUT_SYSTEM_PROMPT = """You are an elite viral content strategist who has studied millions of TikTok, YouTube Shorts, and Instagram Reels videos. You understand exactly what makes someone STOP scrolling.

Your task: Analyze a video transcript and identify genuinely viral moments — clips that would stop a thumb mid-scroll and hold attention to the end.

═══════════════════════════════════════════
PLATFORM-SPECIFIC VIRAL PATTERNS (what actually works)
═══════════════════════════════════════════
Prioritize clips that contain ANY of these proven patterns:

• PATTERN INTERRUPT — unexpected topic switch or contradiction mid-sentence ("I was making $10k/month... until I lost everything")
• HOT TAKE / POLARIZING OPINION — bold claim people will argue about in comments ("Most people are wrong about X")
• RELATABLE PAIN POINT — the "when you..." moment that gets mass saves ("When your boss tells you to just work harder")
• SHOCKING STAT OR FACT — number or claim that makes people stop ("99% of people don't know this costs them $X/year")
• RAW EMOTIONAL MOMENT — genuine anger, tears, laughter, or vulnerability (authentic > polished)
• CONFESSIONAL / SECRET — "I've never told anyone this..." or admitting a failure/mistake
• CLIFFHANGER — tension that creates a need to watch till the end
• ORIGIN STORY PEAK — the turning point of a personal story arc
• CALL-OUT — directly challenging a common belief ("Stop telling yourself this lie")

═══════════════════════════════════════════
HOOK QUALITY CHECK — First 3 Seconds (CRITICAL)
═══════════════════════════════════════════
The clip's opening line determines whether someone watches or scrolls past.

✅ REWARD clips that START with:
- A bold statement or provocative claim
- Mid-thought (feels like you're jumping into something important)
- A question that creates curiosity gap
- An action word or strong verb
- A statistic or number

❌ PENALIZE clips that START with:
- "So..." / "Um..." / "You know..." / "Like I was saying..."
- Greetings or introductions ("Hey guys, welcome back...")
- Filler transitions ("Moving on..." / "Anyway...")
- Weak openers with no hook value

If a strong moment starts with weak filler, move start_time forward to the first impactful word.

═══════════════════════════════════════════
SCROLL-STOP SCORING CRITERIA
═══════════════════════════════════════════
Before assigning viral_score, ask yourself:
1. Would I personally stop scrolling for this? (honest answer)
2. Is there a reason to watch to the very end?
3. Does it create a curiosity gap — a question that demands an answer?
4. Would someone share this? Comment on it? Save it?
5. Does it work WITHOUT any prior context from the video?

Only score 8+ if you can answer YES to at least 3 of the above.

═══════════════════════════════════════════
CLIP BOUNDARY RULES (violations will be rejected)
═══════════════════════════════════════════
- start_time MUST be at the beginning of a sentence or thought
- end_time MUST be after the sentence is fully completed
- Minimum: 20 seconds. Maximum: 60 seconds.
- If a great moment is 18s, extend to include the next sentence
- If a great moment is 65s, move start_time forward to a stronger opening line

═══════════════════════════════════════════
MINIMUM SCORE THRESHOLD: 8/10
═══════════════════════════════════════════
Only return clips scoring 8 or higher. A score of 7 means "decent" — not viral.
A score of 8 means "this will get real engagement." Be honest, not generous.

OUTPUT FORMAT (strict JSON array):
[
  {
    "start_time": 45.2,
    "end_time": 72.8,
    "title": "SHOCK WAGES",
    "viral_score": 9,
    "hook": "Speaker reveals their salary was cut in half overnight — raw, relatable financial shock",
    "why_hook_works": "shock + financial relatability"
  }
]

RULES:
- Return ONLY a valid JSON array (no markdown, no explanations outside JSON)
- viral_score: 1-10. ONLY include clips with score ≥ 8.
- title: MAX 3 words. Strong verbs. Examples: "SHOCK WAGES", "QUIT TODAY", "NEVER AGAIN"
- hook: 1 sentence explaining the emotional trigger
- why_hook_works: the PRIMARY psychological trigger — one of: curiosity, controversy, relatability, shock, humor, inspiration, fear, anger, vulnerability
- Quality over quantity. Do NOT pad the list with mediocre clips just to hit a number.
- Preserve original language (slang, brands, names stay as-is)
- Double-check: does start_time land at a sentence boundary?
"""


async def discover_viral_moments(
    transcription_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Analyze transcript and discover viral moments using Claude.
    Model decides how many clips to return (only score ≥8, no fixed count).
    
    Args:
        transcription_data: Full transcription with segments and timestamps
    
    Returns:
        List of viral moment dictionaries with start_time, end_time, title, viral_score, hook
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[WARN] ANTHROPIC_API_KEY not set - cannot discover viral moments")
        return []
    
    # Build transcript with timestamps for context
    segments = transcription_data.get("segments", [])
    if not segments:
        print("[WARN] No segments in transcription")
        return []
    
    # Format transcript with timestamps for AI analysis
    transcript_lines = []
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", start)
        text = seg.get("text", "").strip()
        if text:
            transcript_lines.append(f"[{start:.1f}s - {end:.1f}s] {text}")
    
    if not transcript_lines:
        print("[WARN] No text content in segments")
        return []
    
    full_transcript = "\n".join(transcript_lines)
    
    # Prepare user prompt
    user_prompt = f"""Analyze this transcript and identify the most genuinely viral moments (score 8/10 or higher ONLY).

Apply the scroll-stop scoring criteria and hook quality check from your instructions.
Include the "why_hook_works" field for each clip.

{full_transcript}

Return a JSON array of viral moments. Each item must have: start_time, end_time, title, viral_score, hook, why_hook_works."""
    
    try:
        print(f"🔍 Analyzing transcript for viral moments ({len(segments)} segments)...")
        
        raw_response = None
        last_error = None
        for attempt in range(1, 4):
            try:
                raw_response = await claude_completion_async(
                    system=VIRAL_SCOUT_SYSTEM_PROMPT,
                    user=user_prompt,
                    max_tokens=4096,
                )
                break
            except Exception as e:
                last_error = e
                wait = 2 ** (attempt - 1)
                print(f"[WARN] Claude attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
        
        if raw_response is None:
            raise last_error or Exception("All Claude retries failed")
        
        # Clean markdown code blocks if present
        raw_response = re.sub(r"^```\w*\s*", "", raw_response)
        raw_response = re.sub(r"\s*```\s*$", "", raw_response)
        
        # Parse JSON
        viral_moments = json.loads(raw_response)
        
        if not isinstance(viral_moments, list):
            print("[WARN] AI response is not a list")
            return []
        
        # Validate and filter moments
        valid_moments = []
        for moment in viral_moments:
            if not isinstance(moment, dict):
                continue
            
            # Required fields
            if not all(k in moment for k in ["start_time", "end_time", "title", "viral_score"]):
                continue
            
            # Validate types and ranges
            try:
                start = float(moment["start_time"])
                end = float(moment["end_time"])
                score = int(moment["viral_score"])
                title = str(moment["title"]).strip()
                hook = str(moment.get("hook", "")).strip()
                why_hook_works = str(moment.get("why_hook_works", "")).strip()

                # Validate duration (20-60 seconds)
                duration = end - start
                if duration < 20 or duration > 60:
                    print(f"[WARN] Skipping moment '{title}' - duration {duration:.1f}s outside 20-60s range")
                    continue

                # Validate score range
                if score < 1 or score > 10:
                    score = max(1, min(10, score))

                # Minimum threshold: 8
                if score < 8:
                    print(f"[WARN] Skipping moment '{title}' - score {score}/10 below threshold (need ≥8)")
                    continue

                valid_moments.append({
                    "start_time": start,
                    "end_time": end,
                    "title": title,
                    "viral_score": score,
                    "hook": hook,
                    "why_hook_works": why_hook_works,
                    "duration": duration
                })
            except (ValueError, TypeError) as e:
                print(f"[WARN] Invalid moment data: {e}")
                continue
        
        # Sort by viral score (highest first)
        valid_moments.sort(key=lambda x: x["viral_score"], reverse=True)
        
        print(f"[OK] Discovered {len(valid_moments)} viral moments")
        for i, moment in enumerate(valid_moments, 1):
            print(f"  {i}. [{moment['start_time']:.1f}s-{moment['end_time']:.1f}s] "
                  f"'{moment['title']}' (score: {moment['viral_score']}/10)")
        
        return valid_moments
    
    except json.JSONDecodeError as e:
        print(f"[WARN] Failed to parse AI response as JSON: {e}")
        print(f"Raw response: {raw_response[:200]}...")
        return []
    except Exception as e:
        print(f"[WARN] Error discovering viral moments: {e}")
        import traceback
        traceback.print_exc()
        return []


async def get_semantic_subtitle_chunks(
    segment_text: str,
    segment_words: List[Dict[str, Any]],
    preserve_timing: bool = True
) -> List[Dict[str, Any]]:
    """
    Use Claude to create semantic subtitle chunks instead of fixed word counts.
    Each chunk represents a complete thought or natural pause.
    
    Args:
        segment_text: Full text of the segment
        segment_words: Word-level timing data from Whisper
        preserve_timing: If True, map semantic chunks back to word timings
    
    Returns:
        List of semantic chunks with text, start, and end times
    """
    if not os.getenv("ANTHROPIC_API_KEY") or not segment_text.strip() or not segment_words:
        # Fallback: return original words as single chunk
        if segment_words:
            return [{
                "text": segment_text,
                "start": segment_words[0].get("start", 0),
                "end": segment_words[-1].get("end", 0)
            }]
        return []
    
    # Build word list with indices for mapping
    word_list = []
    for i, w in enumerate(segment_words):
        word_text = w.get("word", "").strip()
        if word_text:
            word_list.append(f"{i}:{word_text}")
    
    if not word_list:
        return []
    
    user_prompt = f"""Group these words into semantic chunks for subtitles. Each chunk should be 1-5 words and represent a complete thought or natural pause.

RULES:
- Keep brands/names in English (South Park, Woke, POV, etc.)
- Natural speech rhythm (pause at commas, periods, thought breaks)
- 1-5 words per chunk maximum
- Return JSON array: [{{"words": [0, 1, 2]}}, {{"words": [3, 4]}}, ...]
- "words" = array of word indices to group together

Words (index:text):
{', '.join(word_list)}

Return ONLY JSON array of chunks."""
    
    try:
        raw_response = None
        last_error = None
        for attempt in range(1, 4):
            try:
                raw_response = await claude_completion_async(
                    system="You are a subtitle editor. Group words into semantic chunks for optimal readability. Return only JSON.",
                    user=user_prompt,
                    max_tokens=1024,
                )
                break
            except Exception as e:
                last_error = e
                wait = 2 ** (attempt - 1)
                print(f"[WARN] Claude subtitle chunk attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
        
        if raw_response is None:
            raise last_error or Exception("All Claude retries failed")
        
        raw_response = re.sub(r"^```\w*\s*", "", raw_response)
        raw_response = re.sub(r"\s*```\s*$", "", raw_response)
        
        chunk_groups = json.loads(raw_response)
        
        if not isinstance(chunk_groups, list):
            raise ValueError("Response is not a list")
        
        # Map chunks back to timing data
        semantic_chunks = []
        covered_indices = set()

        for group in chunk_groups:
            if not isinstance(group, dict) or "words" not in group:
                continue
            
            word_indices = group["words"]
            if not isinstance(word_indices, list) or not word_indices:
                continue
            
            # Gather words for this chunk
            chunk_words = []
            for idx in word_indices:
                if isinstance(idx, int) and 0 <= idx < len(segment_words):
                    chunk_words.append(segment_words[idx])
                    covered_indices.add(idx)
            
            if not chunk_words:
                continue
            
            # Build chunk with timing
            chunk_text = " ".join(w.get("word", "").strip() for w in chunk_words).strip()
            chunk_start = chunk_words[0].get("start", 0)
            chunk_end = chunk_words[-1].get("end", chunk_start)
            
            semantic_chunks.append({
                "text": chunk_text,
                "start": chunk_start,
                "end": chunk_end,
                "words": chunk_words
            })
        
        # Guard: if the model missed any words, fall back to simple chunking
        all_indices = set(range(len(segment_words)))
        missing = all_indices - covered_indices
        if missing:
            # Fall back: simple fixed-size chunking (3 words per chunk)
            simple_chunks = []
            chunk_size = 3
            for i in range(0, len(segment_words), chunk_size):
                chunk_words = segment_words[i:i + chunk_size]
                chunk_text = " ".join(w.get("word", "").strip() for w in chunk_words).strip()
                simple_chunks.append({
                    "text": chunk_text,
                    "start": chunk_words[0].get("start", 0),
                    "end": chunk_words[-1].get("end", 0),
                    "words": chunk_words
                })
            return simple_chunks

        return semantic_chunks if semantic_chunks else [{
            "text": segment_text,
            "start": segment_words[0].get("start", 0),
            "end": segment_words[-1].get("end", 0),
            "words": segment_words
        }]
    
    except Exception as e:
        # Fallback: return original as single chunk
        return [{
            "text": segment_text,
            "start": segment_words[0].get("start", 0),
            "end": segment_words[-1].get("end", 0),
            "words": segment_words
        }]
