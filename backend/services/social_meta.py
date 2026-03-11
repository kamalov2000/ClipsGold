"""
Social Metadata Generator: GPT-4o generates title, description, hashtags for a rendered clip.
Saves result as {clip_id}_meta.json in the output directory.
"""

import json
import os
import re
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SOCIAL_META_SYSTEM_PROMPT = """You are a viral social media expert for TikTok, YouTube Shorts and Instagram Reels.
Given a short video transcript, generate optimized metadata.

Return ONLY valid JSON (no markdown):
{
  "title": "Short punchy title ≤60 chars, ALL CAPS key words, no hashtags",
  "description": "2-3 sentence hook for the caption. Conversational, emoji-rich.",
  "hashtags": ["#viral", "#fyp", "#trending", ...],
  "cta": "One-line call-to-action (e.g. 'Follow for more 🔥')"
}

Rules:
- title: ≤60 chars, punchy, curiosity-driven
- description: 150-200 chars, ends with emoji
- hashtags: 5-7 tags, mix of niche + broad
- cta: short, energetic
"""


async def generate_social_metadata(
    clip_transcript: str,
    clip_title: str,
    platform: str = "tiktok",
    output_path: Optional[Path] = None,
) -> dict:
    """
    Generate social metadata for a clip using GPT-4o.
    Saves to output_path as JSON if provided.
    Returns dict with title, description, hashtags, cta.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    fallback = {
        "title": clip_title[:60].upper(),
        "description": f"{clip_title} 🔥 Watch till the end!",
        "hashtags": ["#viral", "#fyp", "#trending", "#shorts", "#reels"],
        "cta": "Follow for more 🔥",
    }

    if not api_key or not clip_transcript.strip():
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
        return fallback

    user_prompt = f"""Platform: {platform.upper()}
Clip title: {clip_title}
Transcript excerpt:
{clip_transcript[:800]}

Generate metadata JSON."""

    raw = None
    last_err = None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        for attempt in range(1, 4):
            try:
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SOCIAL_META_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=512,
                )
                raw = (response.choices[0].message.content or "").strip()
                break
            except Exception as e:
                last_err = e
                wait = 2 ** (attempt - 1)
                print(f"⚠ Social meta attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
    except Exception as e:
        print(f"⚠ Social meta OpenAI init failed: {e}")

    if not raw:
        print(f"⚠ Social meta: all retries failed ({last_err}), using fallback")
        result = fallback
    else:
        try:
            raw = re.sub(r"^```\w*\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
            result = json.loads(raw)
            # Ensure required keys
            for k, v in fallback.items():
                result.setdefault(k, v)
            print(f"✓ Social metadata generated: {result.get('title', '')[:50]}")
        except Exception as e:
            print(f"⚠ Social meta JSON parse failed: {e}")
            result = fallback

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  → Saved social metadata: {output_path.name}")

    return result
