"""
Renderer constants and helpers: subtitle positioning, ASS styling, blurred background.
"""

# 9:16 vertical resolution
PLAY_RES_X = 1080
PLAY_RES_Y = 1920

# Subtitle position: center-third vertically = 70% from top
# In ASS, MarginV is distance from bottom for Alignment 2. 70% from top = 30% from bottom.
SUBTITLE_MARGIN_V_70_PCT_FROM_TOP = int(PLAY_RES_Y * 0.30)  # 576

# Drop shadow depth for ASS (Outline, Shadow) for better readability
ASS_OUTLINE = 6
ASS_SHADOW = 10


def get_ffmpeg_blurred_background_filter(
    input_label: str = "0:v",
    output_label: str = "out",
    blur_size: int = 20,
    scale_factor: float = 2.0,
) -> str:
    """
    Build filter_complex for a blurred, scaled background (for letterboxed output).
    Use when the main video is scaled to fit and has black bars; this fills the bars
    with a blurred version of the same video.
    Example: [0:v]split[main][bg];[bg]scale=iw*2:ih*2,boxblur=20,scale=1080:1920:force_original_aspect_ratio=decrease,crop=1080:1920[bg];[bg][main]overlay=(W-w)/2:(H-h)/2[out]
    """
    # Scale up, blur, then scale to target; use as background layer
    w, h = PLAY_RES_X, PLAY_RES_Y
    return (
        f"[{input_label}]split[main][bg];"
        f"[bg]scale=iw*{scale_factor}:ih*{scale_factor},boxblur={blur_size},"
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,crop={w}:{h}[bg];"
        f"[bg][main]overlay=(W-w)/2:(H-h)/2[{output_label}]"
    )
