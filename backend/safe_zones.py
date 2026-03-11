"""
Safe Zones configuration for different social media platforms.
Defines margin values to avoid UI overlap (bottom bars, buttons, etc.)
"""

from typing import Dict, Tuple

# Platform-specific safe zone margins (in pixels for 1080x1920 resolution)
# MarginV: Vertical margin from bottom (higher = more space from bottom)
# MarginL/R: Left/Right margins (for horizontal safety)

PLATFORM_SAFE_ZONES: Dict[str, Dict[str, int]] = {
    "tiktok": {
        "MarginV": 280,  # TikTok has description, profile, and action buttons at bottom
        "MarginL": 50,
        "MarginR": 50,
        "description": "Avoid bottom 280px for TikTok UI (description, buttons, profile)"
    },
    "youtube": {
        "MarginV": 200,  # YouTube Shorts has less UI at bottom
        "MarginL": 50,
        "MarginR": 50,
        "description": "Avoid bottom 200px for YouTube Shorts UI"
    },
    "instagram": {
        "MarginV": 250,  # Instagram Reels has action buttons on right side
        "MarginL": 50,
        "MarginR": 100,  # More space on right for action buttons
        "description": "Avoid bottom 250px and right 100px for Instagram Reels UI"
    },
    "default": {
        "MarginV": 250,
        "MarginL": 50,
        "MarginR": 50,
        "description": "Default safe zone for unknown platforms"
    }
}


def get_safe_zone(platform: str) -> Dict[str, int]:
    """
    Get safe zone margins for a specific platform.
    
    Args:
        platform: Platform name (tiktok, youtube, instagram)
    
    Returns:
        Dictionary with MarginV, MarginL, MarginR values
    """
    platform_lower = platform.lower()
    
    if platform_lower in PLATFORM_SAFE_ZONES:
        return PLATFORM_SAFE_ZONES[platform_lower]
    
    # Fallback to default
    return PLATFORM_SAFE_ZONES["default"]


def get_subtitle_margin(platform: str) -> int:
    """
    Get vertical margin for subtitles based on platform.
    
    Args:
        platform: Platform name (tiktok, youtube, instagram)
    
    Returns:
        MarginV value in pixels
    """
    safe_zone = get_safe_zone(platform)
    return safe_zone["MarginV"]


def get_safe_zone_info(platform: str) -> str:
    """
    Get human-readable description of safe zone for a platform.
    
    Args:
        platform: Platform name
    
    Returns:
        Description string
    """
    safe_zone = get_safe_zone(platform)
    return safe_zone.get("description", "No description available")


# Visual representation for debugging
def print_safe_zones():
    """Print all configured safe zones"""
    print("\n" + "="*60)
    print("SAFE ZONES CONFIGURATION")
    print("="*60)
    
    for platform, config in PLATFORM_SAFE_ZONES.items():
        if platform == "default":
            continue
        print(f"\n{platform.upper()}:")
        print(f"  MarginV: {config['MarginV']}px (from bottom)")
        print(f"  MarginL: {config['MarginL']}px (from left)")
        print(f"  MarginR: {config['MarginR']}px (from right)")
        print(f"  Info: {config['description']}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    print_safe_zones()
