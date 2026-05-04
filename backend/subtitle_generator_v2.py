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
    "minimal": (
        "Arial", 44, "&H00FFFFFF", "&H00FFFFFF", "&H00000000", 2, 2, 120, 0
    ),
    "podcast": (
        "Montserrat", 52, "&H00FFFFFF", "&H00FFFFFF", "&H00000000", 3, 0, 450, -1
    ),
}


class SubtitleGeneratorV2:
    """Subtitle generator with multiple style presets and optional Claude semantic chunking."""
    
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
        text = text.strip().lstrip('\u2014').lstrip('\u2013').lstrip('-').strip()
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
    
    def create_static_subtitle(
        self,
        chunk: List[Dict],
        chunk_start: float,
        chunk_end: float,
        clip_start_time: float,
    ) -> str:
        """Create a static subtitle line (no animation) for podcast style."""
        if not chunk:
            return ""

        chunk_end = chunk[-1].get("end", chunk_start + 1)
        adjusted_start = max(0, chunk_start - clip_start_time)
        adjusted_end = chunk_end - clip_start_time

        if adjusted_end <= 0:
            return ""

        words = " ".join(
            self.escape_ass_text(w.get("word", "").strip())
            for w in chunk
            if w.get("word", "").strip()
        )

        start_time = self.format_timestamp(adjusted_start)
        end_time = self.format_timestamp(adjusted_end)

        return f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{words}\n"

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
    
    def _translate_segments(self, segments: List[Dict], target_language: str) -> List[Dict]:
        """
        Translate segment texts using Claude (Anthropic).
        Reconstructs word-level timings by distributing proportionally across translated words.
        target_language: 'en' (English) or 'ru' (Russian)
        """
        import os
        from services.claude_llm import claude_completion_sync

        if not os.getenv("ANTHROPIC_API_KEY"):
            return segments

        lang_name = "English" if target_language == "en" else "Russian"

        # Collect texts to translate
        texts = [seg.get("text", "").strip() for seg in segments]
        if not any(texts):
            return segments

        prompt = f"Translate each line to {lang_name}. Return ONLY the translated lines in the same order, one per line, no numbering.\n\n" + "\n".join(texts)

        try:
            translated = claude_completion_sync(user=prompt, system=None, max_tokens=2048)
            translated_lines = translated.strip().split("\n")
        except Exception as e:
            print(f"  [WARN] Translation failed: {e}")
            return segments

        translated_segments = []
        for i, seg in enumerate(segments):
            translated_text = translated_lines[i].strip() if i < len(translated_lines) else seg.get("text", "")
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", seg_start + 1)
            seg_duration = max(seg_end - seg_start, 0.1)

            # Build proportional word timings from translated text
            raw_words = translated_text.split()
            if not raw_words:
                translated_segments.append(dict(seg, text=translated_text, words=[]))
                continue

            word_dur = seg_duration / len(raw_words)
            new_words = []
            for wi, w in enumerate(raw_words):
                new_words.append({
                    "word": " " + w,
                    "start": round(seg_start + wi * word_dur, 3),
                    "end": round(seg_start + (wi + 1) * word_dur, 3),
                    "probability": 1.0,
                })

            new_seg = dict(seg)
            new_seg["text"] = translated_text
            new_seg["words"] = new_words
            translated_segments.append(new_seg)

        return translated_segments

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
        subtitle_language: str = "auto",
    ) -> List[float]:
        """Generate ASS subtitle file with word-level highlighting.
        subtitle_style: 'hormozi' | 'minimal'
        Returns list of sentence start times for zoom effect."""
        
        segments = transcription_data.get("segments", [])
        if not segments:
            return []

        # Translation: if subtitle_language is 'en' or 'ru' and differs from auto,
        # translate segments before generating subtitle lines.
        # 'auto' = use transcript as-is; 'ru' = Russian; 'en' = English
        if subtitle_language == "en":
            print(f"  [LANG] Translating subtitles to English...")
            segments = self._translate_segments(segments, "en")
        elif subtitle_language == "ru":
            print(f"  [LANG] Translating subtitles to Russian...")
            segments = self._translate_segments(segments, "ru")

        # Calculate clip duration
        if clip_duration is None:
            clip_duration = clip_end_time - clip_start_time if clip_end_time else 30
        
        # Start with style template (dynamic per subtitle_style + platform safe-zones)
        ass_content = self._build_style_template(subtitle_style, platform)
        
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
                # Synthesize word timings by distributing segment text evenly
                seg_text = (segment.get("text") or "").strip()
                if not seg_text:
                    continue
                raw_words = seg_text.split()
                if not raw_words:
                    continue
                seg_dur = max(seg_end - seg_start, 0.1)
                word_dur = seg_dur / len(raw_words)
                words = []
                for wi, w in enumerate(raw_words):
                    w = w.lstrip('\u2014').lstrip('\u2013').lstrip('-').strip()
                    if not w:
                        continue
                    words.append({
                        "word": " " + w,
                        "start": round(seg_start + wi * word_dur, 3),
                        "end":   round(seg_start + (wi + 1) * word_dur, 3),
                        "probability": 1.0,
                    })
            
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
            
            # PODCAST STYLE: static text, 6 words per phrase, no animation
            if subtitle_style == "podcast":
                chunks = self.chunk_words(clip_words, max_words=6)
                for chunk in chunks:
                    chunk_start = chunk[0].get("start", 0) if chunk else clip_start_time
                    chunk_end = chunk[-1].get("end", chunk_start + 1) if chunk else chunk_start + 1
                    subtitle_line = self.create_static_subtitle(chunk, chunk_start, chunk_end, clip_start_time)
                    if subtitle_line:
                        ass_content += subtitle_line
                        total_subtitle_lines += 1

            # SEMANTIC CHUNKING: Claude groups phrases for readability
            elif self.use_semantic_chunking:
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
        use_semantic_chunking: If True, uses Claude for phrase grouping where configured.
                               If False, uses traditional fixed 3-word chunks.
    """
    return SubtitleGeneratorV2(use_semantic_chunking=use_semantic_chunking)
