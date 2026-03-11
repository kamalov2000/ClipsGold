"""
Emoji overlay generator for viral video pop-ups.
Creates FFmpeg drawtext filters for animated emoji overlays.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# Emoji to Unicode mapping for drawtext filter
EMOJI_MAP = {
    "🔥": "\\U0001F525",
    "💯": "\\U0001F4AF",
    "😱": "\\U0001F631",
    "🤯": "\\U0001F92F",
    "💰": "\\U0001F4B0",
    "[!]": "\\U000026A1",
    "👀": "\\U0001F440",
    "🚀": "\\U0001F680",
    "💪": "\\U0001F4AA",
    "🎯": "\\U0001F3AF",
    "✨": "\\U00002728",
    "❤️": "\\U00002764\\U0000FE0F",
    "😂": "\\U0001F602",
    "🙏": "\\U0001F64F",
    "💎": "\\U0001F48E",
    "🎉": "\\U0001F389",
    "🔴": "\\U0001F534",
    "⭐": "\\U00002B50",
    "🎥": "\\U0001F3A5",
    "📈": "\\U0001F4C8",
}


def get_emoji_unicode(emoji: str) -> Optional[str]:
    """Convert emoji character to Unicode escape sequence for FFmpeg."""
    return EMOJI_MAP.get(emoji)


def create_emoji_overlay_filter(
    emoji_list: List[str],
    start_time: float = 0.0,
    duration: float = 1.5,
    video_width: int = 1080,
    video_height: int = 1920,
    font_size: int = 120,
    enable_zoom: bool = True,
) -> str:
    """
    Create FFmpeg drawtext filter for emoji pop-up overlay.
    
    Args:
        emoji_list: List of emoji characters to display
        start_time: When to show emoji (seconds from clip start)
        duration: How long to show emoji (seconds)
        video_width: Video width in pixels
        video_height: Video height in pixels
        font_size: Base emoji size
        enable_zoom: Enable zoom-in animation effect
    
    Returns:
        FFmpeg drawtext filter string
    """
    if not emoji_list:
        return ""
    
    # Take first emoji only (or you can stack multiple)
    emoji = emoji_list[0] if isinstance(emoji_list, list) else emoji_list
    unicode_emoji = get_emoji_unicode(emoji)
    
    if not unicode_emoji:
        # Fallback: use text representation
        unicode_emoji = emoji
    
    # Center position
    y_pos = video_height // 3  # Upper third of screen
    
    end_time = start_time + duration
    
    # SIMPLIFIED: Use static fontsize to avoid complex expressions that break FFmpeg
    # Windows FFmpeg has issues parsing nested if() expressions in fontsize parameter
    fontsize_value = font_size
    
    # Fade in/out alpha - SIMPLIFIED to avoid parsing errors
    fade_duration = 0.2  # 200ms fade
    
    # Detect Windows font path
    if os.name == 'nt':
        # Windows: Use Segoe UI Emoji (built-in)
        fontfile = "C\\:/Windows/Fonts/seguiemj.ttf"
    else:
        # Linux/Mac: Try NotoColorEmoji
        fontfile = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
    
    # SIMPLIFIED filter without complex expressions
    # Use basic enable timing instead of alpha animations
    filter_str = (
        f"drawtext="
        f"text='{unicode_emoji}':"
        f"fontfile={fontfile}:"
        f"fontsize={fontsize_value}:"
        f"x=(w-text_w)/2:"
        f"y={y_pos}:"
        f"fontcolor=white:"
        f"borderw=3:"
        f"bordercolor=black:"
        f"enable='between(t,{start_time},{end_time})'"
    )
    
    return filter_str


def extract_emojis_from_metadata(clip_metadata: Dict) -> List[str]:
    """
    Extract emoji list from clip metadata returned by AI analysis.
    
    Args:
        clip_metadata: Dictionary with 'emojis' key
    
    Returns:
        List of emoji characters
    """
    emojis = clip_metadata.get("emojis", [])
    if isinstance(emojis, list) and emojis:
        return emojis
    return []


def create_multi_emoji_sequence(
    emojis: List[str],
    clip_duration: float,
    max_emojis: int = 3,
) -> List[Dict]:
    """
    Create a sequence of emoji pop-ups throughout the clip.
    
    Args:
        emojis: List of emoji characters from AI analysis
        clip_duration: Total clip duration in seconds
        max_emojis: Maximum number of emoji pop-ups
    
    Returns:
        List of emoji timing configs: [{"emoji": "🔥", "start": 2.0, "duration": 1.5}, ...]
    """
    if not emojis or clip_duration < 5:
        return []
    
    sequence = []
    emoji_count = min(len(emojis), max_emojis)
    
    # Space emojis evenly throughout clip
    # First emoji at 10% of clip, last at 70% (leave end clean)
    interval = (0.6 * clip_duration) / max(emoji_count, 1)
    
    for i, emoji in enumerate(emojis[:emoji_count]):
        start_time = 0.1 * clip_duration + (i * interval)
        sequence.append({
            "emoji": emoji,
            "start": round(start_time, 2),
            "duration": 1.5,
        })
    
    return sequence


def add_emoji_overlays_to_filter_chain(
    base_video_filter: str,
    emoji_sequence: List[Dict],
    video_width: int = 1080,
    video_height: int = 1920,
) -> str:
    """
    Append emoji drawtext filters to existing video filter chain.
    
    Args:
        base_video_filter: Existing filter chain (zoom, crop, scale, etc.)
        emoji_sequence: List of emoji timing configs
        video_width: Video width
        video_height: Video height
    
    Returns:
        Complete filter chain with emoji overlays
    """
    if not emoji_sequence:
        return base_video_filter
    
    filters = [base_video_filter] if base_video_filter else []
    
    for emoji_config in emoji_sequence:
        emoji_filter = create_emoji_overlay_filter(
            emoji_list=[emoji_config["emoji"]],
            start_time=emoji_config["start"],
            duration=emoji_config.get("duration", 1.5),
            video_width=video_width,
            video_height=video_height,
        )
        if emoji_filter:
            filters.append(emoji_filter)
    
    return ",".join(filters)
