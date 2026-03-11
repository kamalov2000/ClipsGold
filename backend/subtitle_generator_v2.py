from pathlib import Path
from typing import List, Dict, Optional
import re
import asyncio
from services.renderer import ASS_OUTLINE, ASS_SHADOW
from services.viral_scout import get_semantic_subtitle_chunks
from services.pipeline_upgrades import get_safe_margin_v, get_hook_margin_v


# Font paths — checked in order: project assets (cross-platform) → Docker → fallback to font name
_ASSETS_DIR = Path(__file__).parent / "assets" / "fonts"
FONT_PATHS = {
    "Montserrat": [
        str(_ASSETS_DIR / "Montserrat-Bold.ttf"),          # project assets (always works)
        "/usr/share/fonts/truetype/custom/montserrat/Montserrat-Bold.ttf",  # Docker
    ],
    "Impact": [
        "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",  # Docker
        "C:/Windows/Fonts/impact.ttf",                          # Windows
    ],
    "Arial": [
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",   # Docker
        "C:/Windows/Fonts/arial.ttf",                           # Windows
    ],
}

# Subtitle style presets
# Format: (FontName, FontSize, PrimaryColour, HighlightColour, OutlineColour, Outline, Shadow, MarginV, Bold)
SUBTITLE_STYLES = {
    "hormozi": (
        "Montserrat", 62, "&H00FFFFFF", "&H0000FFFF", "&H00000000", 6, 10, 450, -1
    ),
    "beast": (
        "Impact", 78, "&H0000FFFF", "&H000000FF", "&H00FFFFFF", 8, 4, 420, -1
    ),
    "minimal": (
        "Arial", 44, "&H00FFFFFF", "&H00FFFFFF", "&H00000000", 2, 2, 120, 0
    ),
}


class SubtitleGeneratorV2:
    """Subtitle generator with multiple style presets and semantic chunking via GPT-4o"""
    
    def __init__(self, use_semantic_chunking: bool = True):
        self.use_semantic_chunking = use_semantic_chunking

    def _build_style_template(self, subtitle_style: str = "hormozi", platform: str = "tiktok") -> str:
        """
        Build ASS [Script Info] + [V4+ Styles] block.
        MarginV is computed from the platform safe-zone rules engine
        (pipeline_upgrades.get_safe_margin_v) so subtitles never overlap UI.
        Uses explicit font paths for Docker compatibility.
        """
        style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["hormozi"])
        font, size, primary, highlight, outline_col, outline, shadow, _style_margin_v, bold = style

        # Resolve font directory for fontsdir= option in FFmpeg subtitles filter.
        # ASS Fontname must be the font FAMILY NAME (e.g. "Montserrat"), NOT a file path.
        # File path goes to fontsdir so libass can discover the bundled .ttf.
        import os
        font_name = font  # always the family name for ASS Fontname field
        self._last_fonts_dir = None
        candidates = FONT_PATHS.get(font, [])
        if isinstance(candidates, str):
            candidates = [candidates]
        for candidate in candidates:
            if os.path.exists(candidate):
                self._last_fonts_dir = str(Path(candidate).parent)
                break

        # Safe-zone rules engine overrides the style's default margin
        margin_v = get_safe_margin_v(platform)
        hook_margin_v = get_hook_margin_v(platform)
        highlight_size = int(size * 1.12)

        return f"""[Script Info]
Title: ClipsGold Viral Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{size},{primary},&H000000FF,{outline_col},&H80000000,{bold},0,0,0,100,100,0,0,1,{outline},{shadow},2,50,50,{margin_v},1
Style: Highlight,{font_name},{highlight_size},{highlight},&H000000FF,{outline_col},&H80000000,{bold},0,0,0,110,110,0,0,1,{outline + 1},{shadow},2,50,50,{margin_v},1
Style: Hook,{font_name},72,&H00FFFF00,&H000000FF,&H00FF00FF,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},{shadow},8,50,50,{hook_margin_v},1
Style: Emoji,Arial,144,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,50,50,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def format_timestamp(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    def escape_ass_text(self, text: str) -> str:
        """Escape special ASS characters"""
        text = text.replace('\\', '\\\\')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        return text
    
    def chunk_words(self, words: List[Dict], max_words: int = 3) -> List[List[Dict]]:
        """Group words into chunks of 1-3 words for display"""
        chunks = []
        current_chunk = []
        
        for word_data in words:
            word = word_data.get("word", "").strip()
            if not word:
                continue
            
            current_chunk.append(word_data)
            
            # Create chunk if we hit max words or punctuation
            if len(current_chunk) >= max_words or word.rstrip('.,!?;:') != word:
                chunks.append(current_chunk)
                current_chunk = []
        
        # Add remaining words
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def create_chunk_subtitle(
        self,
        chunk: List[Dict],
        chunk_start: float,
        chunk_end: float,
        clip_start_time: float,
        platform: str = "tiktok",
        is_split_screen: bool = False
    ) -> str:
        """Create subtitle line for a chunk of 1-3 words with highlight effect"""
        if not chunk:
            return ""
        
        chunk_end = chunk[-1].get("end", chunk_start + 1)

        # Adjust times relative to clip start
        adjusted_start = max(0, chunk_start - clip_start_time)
        adjusted_end = chunk_end - clip_start_time
        
        if adjusted_end <= 0:
            return ""
        
        # Build text with word-by-word highlighting
        text_parts = []
        
        for i, word_data in enumerate(chunk):
            word = self.escape_ass_text(word_data.get("word", "").strip())
            if not word:
                continue
            
            word_start = word_data.get("start", chunk_start)
            word_end = word_data.get("end", chunk_end)
            
            word_start_adj = max(0, word_start - clip_start_time)
            word_end_adj = word_end - clip_start_time
            
            start_ms = int((word_start_adj - adjusted_start) * 1000)
            end_ms = int((word_end_adj - adjusted_start) * 1000)
            
            # Highlight current word with yellow + scaling
            if start_ms == 0:
                # First word starts highlighted
                text_parts.append(f"{{\\c&H0000FFFF&\\fscx110\\fscy110\\t({end_ms},{end_ms},\\c&H00FFFFFF&\\fscx100\\fscy100)}}{word}")
            else:
                # Other words: white -> yellow -> white with scale
                text_parts.append(f"{{\\c&H00FFFFFF&\\t({start_ms},{start_ms},\\c&H0000FFFF&\\fscx110\\fscy110)\\t({end_ms},{end_ms},\\c&H00FFFFFF&\\fscx100\\fscy100)}}{word}")
        
        subtitle_text = " ".join(text_parts)
        
        start_time = self.format_timestamp(adjusted_start)
        end_time = self.format_timestamp(adjusted_end)
        
        # Use style-defined MarginV (1632 for 85% from top) - no override needed
        # Split-screen mode uses same positioning as standard mode now
        return f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{subtitle_text}\n"
    
    def get_sentence_start_times(self, transcription_data: Dict, clip_start_time: float, clip_end_time: Optional[float]) -> List[float]:
        """Extract sentence start times for zoom effect"""
        sentence_starts = []
        segments = transcription_data.get("segments", [])
        
        for segment in segments:
            seg_start = segment.get("start", 0)
            seg_end = segment.get("end", seg_start + 1)
            
            # Skip segments outside clip range
            if clip_end_time and seg_start > clip_end_time:
                continue
            if seg_end < clip_start_time:
                continue
            
            # Segment start is considered a sentence start
            adjusted_start = max(0, seg_start - clip_start_time)
            sentence_starts.append(adjusted_start)
        
        return sentence_starts
    
    def generate_ass_from_transcription(
        self,
        transcription_data: Dict,
        output_path: Path,
        hook_text: str = "",
        emojis: List[str] = None,
        clip_start_time: float = 0,
        clip_end_time: Optional[float] = None,
        clip_duration: Optional[float] = None,
        platform: str = "tiktok",
        is_split_screen: bool = False,
        crop_preview: Optional[Dict] = None,
        subtitle_style: str = "hormozi",
    ) -> List[float]:
        """Generate ASS subtitle file with word-level highlighting.
        subtitle_style: 'hormozi' | 'beast' | 'minimal'
        Returns list of sentence start times for zoom effect."""
        
        segments = transcription_data.get("segments", [])
        if not segments:
            return []
        
        # Calculate clip duration
        if clip_duration is None:
            clip_duration = clip_end_time - clip_start_time if clip_end_time else 30
        
        # Start with style template (dynamic per subtitle_style + platform safe-zones)
        ass_content = self._build_style_template(subtitle_style, platform)
        
        # Add progress bar at bottom (5px high, yellow, fills 0-100%)
        progress_end = self.format_timestamp(clip_duration)
        # Progress bar using ASS drawing commands
        # \p1 = drawing mode, \1a = alpha, \c = color
        ass_content += f"Dialogue: 0,0:00:00.00,{progress_end},Default,,0,0,0,,{{\\pos(540,1915)\\p1\\c&H0000FFFF&\\1a&H00&\\t(0,{int(clip_duration*1000)},\\fscx0,\\fscx100)}}m 0 0 l 1080 0 1080 5 0 5{{\\p0}}\n"
        
        # Add hook text at TOP (5% from top) - limited to 3 words max
        if hook_text:
            # Limit to 3 words maximum - short and punchy
            hook_words = hook_text.split()[:3]
            hook_text_short = " ".join(hook_words).upper()  # ALL CAPS for impact
            hook_text_escaped = self.escape_ass_text(hook_text_short)
            hook_end = self.format_timestamp(clip_duration)
            # Hook uses style-defined position (MarginV=96, Alignment=8 for top)
            ass_content += f"Dialogue: 0,0:00:00.00,{hook_end},Hook,,0,0,0,,{hook_text_escaped}\n"
        
        # Add emojis (rotate every 3 seconds)
        if emojis and isinstance(emojis, list):
            emoji_duration = 3.0  # Show each emoji for 3 seconds
            
            for i, emoji in enumerate(emojis[:3]):
                emoji_start = i * emoji_duration
                emoji_end = min((i + 1) * emoji_duration, clip_duration)
                
                if emoji_start >= clip_duration:
                    break
                
                start_ts = self.format_timestamp(emoji_start)
                end_ts = self.format_timestamp(emoji_end)
                
                # Emoji appears above hook text with bounce animation
                ass_content += f"Dialogue: 0,{start_ts},{end_ts},Emoji,,0,0,0,,{{\\move(540,150,540,180,0,200)\\t(200,400,\\fscx120\\fscy120)\\t(400,600,\\fscx100\\fscy100)}}{emoji}\n"
        
        # Process word-level subtitles
        total_subtitle_lines = 0
        total_words = 0
        
        for segment in segments:
            seg_start = segment.get("start", 0)
            seg_end = segment.get("end", seg_start + 1)
            
            # Skip segments outside clip range
            if clip_end_time and seg_start > clip_end_time:
                continue
            if seg_end < clip_start_time:
                continue
            
            words = segment.get("words", [])
            if not words:
                continue
            
            # Filter words that overlap with clip time range (include words at boundaries).
            # Also exclude words marked as fillers by _apply_corrected_segment_text (H3).
            clip_words = [
                w for w in words
                if w.get("end", 0) > clip_start_time
                and (clip_end_time is None or w.get("start", 0) < clip_end_time)
                and not w.get("_filler", False)
            ]
            
            if not clip_words:
                continue
            
            total_words += len(clip_words)
            
            # SEMANTIC CHUNKING: Use GPT-4o to create intelligent phrase groups
            if self.use_semantic_chunking:
                # Get semantic chunks from AI (async call needs to be run in event loop)
                segment_text = segment.get("text", "")
                try:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
                        semantic_chunks = _pool.submit(
                            asyncio.run,
                            get_semantic_subtitle_chunks(
                                segment_text=segment_text,
                                segment_words=clip_words,
                                preserve_timing=True,
                            )
                        ).result(timeout=30)
                    
                    # Create subtitles from semantic chunks
                    for semantic_chunk in semantic_chunks:
                        chunk_words = semantic_chunk.get("words", [])
                        if not chunk_words:
                            continue
                        
                        chunk_start = semantic_chunk.get("start", clip_start_time)
                        chunk_end = semantic_chunk.get("end", chunk_start + 1)
                        
                        subtitle_line = self.create_chunk_subtitle(
                            chunk_words,
                            chunk_start,
                            chunk_end,
                            clip_start_time,
                            platform=platform,
                            is_split_screen=is_split_screen
                        )
                        if subtitle_line:
                            ass_content += subtitle_line
                            total_subtitle_lines += 1
                except Exception as e:
                    print(f"    Semantic chunking failed, falling back to fixed chunking: {e}")
                    # Fallback to fixed word chunking
                    chunks = self.chunk_words(clip_words, max_words=3)
                    for chunk in chunks:
                        chunk_start = chunk[0].get("start", 0) if chunk else clip_start_time
                        chunk_end = chunk[-1].get("end", chunk_start + 1) if chunk else chunk_start + 1
                        subtitle_line = self.create_chunk_subtitle(
                            chunk, chunk_start, chunk_end, clip_start_time,
                            platform=platform, is_split_screen=is_split_screen
                        )
                        if subtitle_line:
                            ass_content += subtitle_line
                            total_subtitle_lines += 1
            else:
                # FIXED CHUNKING: Traditional 1-3 word groups
                chunks = self.chunk_words(clip_words, max_words=3)
                for chunk in chunks:
                    chunk_start = chunk[0].get("start", 0) if chunk else clip_start_time
                    chunk_end = chunk[-1].get("end", chunk_start + 1) if chunk else chunk_start + 1
                    subtitle_line = self.create_chunk_subtitle(
                        chunk, chunk_start, chunk_end, clip_start_time,
                        platform=platform, is_split_screen=is_split_screen
                    )
                    if subtitle_line:
                        ass_content += subtitle_line
                        total_subtitle_lines += 1
        
        print(f"    Generated {total_subtitle_lines} subtitle lines from {total_words} words")
        
        # Write to file with UTF-8 BOM to ensure proper encoding
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8-sig", newline='\n') as f:
            f.write(ass_content)
        
        # Return sentence start times for zoom effect
        return self.get_sentence_start_times(transcription_data, clip_start_time, clip_end_time)


def create_subtitle_generator(use_semantic_chunking: bool = True) -> SubtitleGeneratorV2:
    """
    Create subtitle generator with optional semantic chunking.
    
    Args:
        use_semantic_chunking: If True, uses GPT-4o for intelligent phrase grouping.
                               If False, uses traditional fixed 3-word chunks.
    """
    return SubtitleGeneratorV2(use_semantic_chunking=use_semantic_chunking)
