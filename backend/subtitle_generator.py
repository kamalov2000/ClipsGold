from pathlib import Path
from typing import List, Dict, Optional
import re


class SubtitleGenerator:
    def __init__(self):
        self.style_template = """[Script Info]
Title: ClipsGold Word-Level Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,70,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,150,1
Style: Hook,Arial Black,90,&H00FFFFFF,&H000000FF,&H00FF00FF,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,8,50,50,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        self.color_white = "&H00FFFFFF"
        self.color_yellow = "&H0000FFFF"
        self.color_green = "&H0000FF00"
    
    def format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    def clean_text(self, text: str) -> str:
        text = text.replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def escape_ass_text(self, text: str) -> str:
        text = text.replace('\\', '\\\\')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        return text
    
    def create_word_level_line(
        self,
        words: List[Dict],
        line_start: float,
        line_end: float,
        clip_start_time: float
    ) -> str:
        if not words:
            return ""
        
        adjusted_start = max(0, line_start - clip_start_time)
        adjusted_end = line_end - clip_start_time
        
        if adjusted_end <= 0:
            return ""
        
        text_parts = []
        
        for i, word_data in enumerate(words):
            word = self.escape_ass_text(word_data.get("word", "").strip())
            if not word:
                continue
            
            word_start = word_data.get("start", line_start)
            word_end = word_data.get("end", line_end)
            
            word_start_adj = max(0, word_start - clip_start_time)
            word_end_adj = word_end - clip_start_time
            
            start_ms = int(word_start_adj * 1000)
            end_ms = int(word_end_adj * 1000)
            
            text_parts.append(
                f"{{\\t({start_ms},{start_ms},\\fscx120\\fscy120\\c{self.color_yellow})}}" 
                f"{{\\t({end_ms},{end_ms},\\fscx100\\fscy100\\c{self.color_white})}}" 
                f"{word}"
            )
            
            if i < len(words) - 1:
                text_parts.append(" ")
        
        formatted_text = "".join(text_parts)
        
        return f"Dialogue: 0,{self.format_timestamp(adjusted_start)},{self.format_timestamp(adjusted_end)},Default,,0,0,0,,{formatted_text}"
    
    def group_words_into_lines(self, words: List[Dict], max_words: int = 8) -> List[List[Dict]]:
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            if len(current_line) >= max_words:
                lines.append(current_line)
                current_line = []
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def generate_ass_from_segments(
        self,
        segments: List[Dict],
        output_path: Path,
        hook_text: str = "",
        clip_start_time: float = 0
    ) -> Path:
        lines = [self.style_template]
        
        if hook_text:
            hook_end = segments[-1]["end"] if segments else 30.0
            hook_text_clean = self.escape_ass_text(hook_text).upper()
            lines.append(
                f"Dialogue: 0,{self.format_timestamp(0)},{self.format_timestamp(hook_end)},"
                f"Hook,,0,0,0,,{hook_text_clean}"
            )
        
        for segment in segments:
            seg_start = segment["start"]
            seg_end = segment["end"]
            
            if seg_end - clip_start_time <= 0:
                continue
            
            words = segment.get("words", [])
            
            if not words:
                text = self.escape_ass_text(self.clean_text(segment["text"]))
                start_time = max(0, seg_start - clip_start_time)
                end_time = seg_end - clip_start_time
                lines.append(
                    f"Dialogue: 0,{self.format_timestamp(start_time)},{self.format_timestamp(end_time)},"
                    f"Default,,0,0,0,,{text}"
                )
            else:
                word_lines = self.group_words_into_lines(words, max_words=8)
                
                for word_line in word_lines:
                    if word_line:
                        line_start = word_line[0].get("start", seg_start)
                        line_end = word_line[-1].get("end", seg_end)
                        
                        word_level_dialogue = self.create_word_level_line(
                            word_line,
                            line_start,
                            line_end,
                            clip_start_time
                        )
                        
                        if word_level_dialogue:
                            lines.append(word_level_dialogue)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def generate_ass_from_transcription(
        self,
        transcription_data: Dict,
        output_path: Path,
        hook_text: str = "",
        clip_start_time: float = 0,
        clip_end_time: float = 30.0
    ) -> Path:
        segments = transcription_data.get("segments", [])
        
        filtered_segments = []
        for segment in segments:
            seg_start = segment["start"]
            seg_end = segment["end"]
            
            if seg_end > clip_start_time and seg_start < clip_end_time:
                filtered_segments.append(segment)
        
        return self.generate_ass_from_segments(
            filtered_segments,
            output_path,
            hook_text,
            clip_start_time
        )


def create_subtitle_generator() -> SubtitleGenerator:
    return SubtitleGenerator()
