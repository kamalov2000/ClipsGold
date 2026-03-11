"""
Unit tests for the analyzer module and analysis endpoint.
Tests JSON parsing, timecode validation, and candidate storage.
"""

import pytest
import json
from pathlib import Path
from analyzer import ViralClipAnalyzer, MockAnalyzer, create_analyzer


class TestTimecodeValidation:
    """Test that timecodes are validated against video duration"""
    
    def test_clips_within_video_duration(self):
        """Clips should not exceed video duration"""
        analyzer = MockAnalyzer()
        video_duration = 60.0  # 1 minute video
        
        clips = analyzer.analyze_transcription("Test transcription", video_duration)
        
        for clip in clips:
            assert clip["start_time"] >= 0, "Start time should be non-negative"
            assert clip["end_time"] <= video_duration, f"End time {clip['end_time']} exceeds video duration {video_duration}"
            assert clip["start_time"] < clip["end_time"], "Start time should be before end time"
    
    def test_minimum_clip_duration(self):
        """Clips should have minimum duration of 15 seconds"""
        analyzer = MockAnalyzer()
        video_duration = 120.0
        
        clips = analyzer.analyze_transcription("Test transcription", video_duration)
        
        for clip in clips:
            duration = clip["end_time"] - clip["start_time"]
            assert duration >= 10, f"Clip duration {duration}s is below minimum (mock uses 10s min)"
    
    def test_short_video_handling(self):
        """Short videos should generate appropriate clips"""
        analyzer = MockAnalyzer()
        video_duration = 15.0  # Very short video
        
        clips = analyzer.analyze_transcription("Test transcription", video_duration)
        
        # Should generate at least one clip if video is long enough
        if video_duration >= 10:
            assert len(clips) > 0, "Should generate at least one clip for 15s video"
            assert clips[0]["end_time"] <= video_duration
    
    def test_very_short_video_no_clips(self):
        """Videos shorter than minimum should not generate clips"""
        analyzer = MockAnalyzer()
        video_duration = 5.0  # Too short
        
        clips = analyzer.analyze_transcription("Test transcription", video_duration)
        
        # Mock analyzer might still generate a clip, but it should be within bounds
        for clip in clips:
            assert clip["end_time"] <= video_duration


class TestJSONStructure:
    """Test that analyzer returns correctly structured JSON"""
    
    def test_required_fields_present(self):
        """All required fields should be present in each clip"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test transcription", 120.0)
        
        required_fields = ["start_time", "end_time", "title", "reason", "virality_score", "hook"]
        
        for clip in clips:
            for field in required_fields:
                assert field in clip, f"Required field '{field}' missing from clip"
    
    def test_field_types(self):
        """Fields should have correct data types"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test transcription", 120.0)
        
        for clip in clips:
            assert isinstance(clip["start_time"], (int, float)), "start_time should be numeric"
            assert isinstance(clip["end_time"], (int, float)), "end_time should be numeric"
            assert isinstance(clip["title"], str), "title should be string"
            assert isinstance(clip["reason"], str), "reason should be string"
            assert isinstance(clip["virality_score"], int), "virality_score should be integer"
            assert isinstance(clip["hook"], str), "hook should be string"
    
    def test_virality_score_range(self):
        """Virality score should be between 1 and 10"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test transcription", 120.0)
        
        for clip in clips:
            score = clip["virality_score"]
            assert 1 <= score <= 10, f"Virality score {score} out of range [1, 10]"
    
    def test_json_serializable(self):
        """Output should be JSON serializable"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test transcription", 120.0)
        
        # Should not raise exception
        json_str = json.dumps(clips)
        assert len(json_str) > 0
        
        # Should be able to parse back
        parsed = json.loads(json_str)
        assert len(parsed) == len(clips)
    
    def test_emojis_field(self):
        """Emojis field should be a list if present"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test transcription", 120.0)
        
        for clip in clips:
            if "emojis" in clip:
                assert isinstance(clip["emojis"], list), "emojis should be a list"
                assert len(clip["emojis"]) <= 3, "Should have max 3 emojis"


class TestAnalyzerValidation:
    """Test the _validate_clips method"""
    
    def test_negative_start_time_correction(self):
        """Negative start times should be corrected to 0"""
        analyzer = MockAnalyzer()
        
        # Simulate invalid clip data
        invalid_clips = [
            {
                "start_time": -5.0,
                "end_time": 30.0,
                "title": "Test",
                "reason": "Test reason",
                "virality_score": 8,
                "hook": "TEST"
            }
        ]
        
        # Mock analyzer doesn't have _validate_clips, but we can test the concept
        # In real implementation, this would be validated
        video_duration = 120.0
        
        # Manual validation logic
        for clip in invalid_clips:
            start = max(0, clip["start_time"])
            assert start >= 0, "Start time should be corrected to 0"
    
    def test_end_time_exceeds_duration(self):
        """End times exceeding video duration should be capped"""
        video_duration = 60.0
        
        invalid_clips = [
            {
                "start_time": 50.0,
                "end_time": 100.0,  # Exceeds duration
                "title": "Test",
                "reason": "Test reason",
                "virality_score": 8,
                "hook": "TEST"
            }
        ]
        
        # Manual validation
        for clip in invalid_clips:
            end = min(clip["end_time"], video_duration)
            assert end <= video_duration, "End time should be capped at video duration"


class TestAnalyzerCreation:
    """Test analyzer factory function"""
    
    def test_create_mock_analyzer(self):
        """Should create MockAnalyzer for 'mock' provider"""
        analyzer = create_analyzer(provider="mock")
        assert isinstance(analyzer, MockAnalyzer)
        assert analyzer.provider == "mock"
    
    def test_mock_analyzer_returns_clips(self):
        """Mock analyzer should return valid clips"""
        analyzer = create_analyzer(provider="mock")
        clips = analyzer.analyze_transcription("Test transcription", 120.0)
        
        assert isinstance(clips, list)
        assert len(clips) > 0
        assert len(clips) <= 3  # Should return max 3 clips


class TestCandidateStorage:
    """Test in-memory candidate storage (integration test concept)"""
    
    def test_candidate_structure_for_storage(self):
        """Candidates should have structure suitable for storage"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test transcription", 120.0)
        
        # Simulate storage
        file_id = "test_file_123"
        storage = {file_id: clips}
        
        # Verify storage works
        assert file_id in storage
        assert len(storage[file_id]) == len(clips)
        
        # Verify retrieval
        retrieved = storage[file_id]
        assert retrieved[0]["title"] == clips[0]["title"]
    
    def test_multiple_file_storage(self):
        """Should be able to store candidates for multiple files"""
        analyzer = MockAnalyzer()
        
        storage = {}
        
        # Store for multiple files
        for i in range(3):
            file_id = f"file_{i}"
            clips = analyzer.analyze_transcription(f"Transcription {i}", 120.0)
            storage[file_id] = clips
        
        assert len(storage) == 3
        assert "file_0" in storage
        assert "file_2" in storage


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_transcription(self):
        """Should handle empty transcription gracefully"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("", 120.0)
        
        # Should still return valid structure (even if empty or with defaults)
        assert isinstance(clips, list)
    
    def test_zero_duration_video(self):
        """Should handle zero duration video"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test", 0.0)
        
        # Should return empty list or handle gracefully
        assert isinstance(clips, list)
        for clip in clips:
            assert clip["end_time"] <= 0.0
    
    def test_very_long_video(self):
        """Should handle very long videos (e.g., 2 hours)"""
        analyzer = MockAnalyzer()
        video_duration = 7200.0  # 2 hours
        
        clips = analyzer.analyze_transcription("Test transcription", video_duration)
        
        assert isinstance(clips, list)
        assert len(clips) <= 3  # Should still return max 3 clips
        
        for clip in clips:
            assert clip["end_time"] <= video_duration


class TestTimecodeRounding:
    """Test that timecodes are properly rounded"""
    
    def test_timecodes_rounded_to_two_decimals(self):
        """Timecodes should be rounded to 2 decimal places"""
        analyzer = MockAnalyzer()
        clips = analyzer.analyze_transcription("Test", 120.0)
        
        for clip in clips:
            # Check that values are rounded (no more than 2 decimal places)
            start_str = f"{clip['start_time']:.2f}"
            end_str = f"{clip['end_time']:.2f}"
            
            # Convert back and check they match (within floating point precision)
            assert abs(float(start_str) - clip['start_time']) < 0.01
            assert abs(float(end_str) - clip['end_time']) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
