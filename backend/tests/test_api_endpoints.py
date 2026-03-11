"""
Integration tests for API endpoints related to Human-in-the-Loop architecture.
Tests the /analyze, /clips/{file_id}/candidates, and /extract-clips endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app, clip_candidates_store, UPLOAD_DIR, OUTPUT_DIR


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_file_setup(tmp_path):
    """Setup mock files for testing"""
    file_id = "test_video_123"
    
    # Create mock transcription file
    transcription_data = {
        "text": "This is a test transcription for viral clip detection.",
        "language": "en",
        "segments": [
            {
                "start": 0.0,
                "end": 30.0,
                "text": "This is a test transcription for viral clip detection.",
                "words": [
                    {"word": "This", "start": 0.0, "end": 0.5},
                    {"word": "is", "start": 0.5, "end": 0.8},
                    {"word": "a", "start": 0.8, "end": 1.0},
                    {"word": "test", "start": 1.0, "end": 1.5}
                ]
            }
        ]
    }
    
    transcription_file = OUTPUT_DIR / f"{file_id}_transcription.json"
    transcription_file.parent.mkdir(parents=True, exist_ok=True)
    with transcription_file.open("w", encoding="utf-8") as f:
        json.dump(transcription_data, f)
    
    # Create mock video file (empty, just for existence check)
    video_file = UPLOAD_DIR / f"{file_id}.mp4"
    video_file.parent.mkdir(parents=True, exist_ok=True)
    video_file.touch()
    
    yield file_id
    
    # Cleanup
    if transcription_file.exists():
        transcription_file.unlink()
    if video_file.exists():
        video_file.unlink()
    
    # Clear candidate store
    if file_id in clip_candidates_store:
        del clip_candidates_store[file_id]


class TestAnalyzeEndpoint:
    """Test the /analyze endpoint"""
    
    def test_analyze_stores_candidates_in_memory(self, client, mock_file_setup):
        """Analysis should store candidates in memory"""
        file_id = mock_file_setup
        
        # Clear any existing data
        if file_id in clip_candidates_store:
            del clip_candidates_store[file_id]
        
        response = client.post(f"/analyze/{file_id}?provider=mock")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "viral_clips" in data
        assert "video_duration" in data
        assert "message" in data
        
        # Check candidates stored in memory
        assert file_id in clip_candidates_store
        assert len(clip_candidates_store[file_id]) > 0
        
        # Verify candidates match response
        assert len(clip_candidates_store[file_id]) == len(data["viral_clips"])
    
    def test_analyze_returns_valid_json_structure(self, client, mock_file_setup):
        """Analysis should return properly structured JSON"""
        file_id = mock_file_setup
        
        response = client.post(f"/analyze/{file_id}?provider=mock")
        
        assert response.status_code == 200
        data = response.json()
        
        clips = data["viral_clips"]
        assert isinstance(clips, list)
        assert len(clips) > 0
        
        # Check each clip has required fields
        required_fields = ["start_time", "end_time", "title", "reason", "virality_score", "hook"]
        for clip in clips:
            for field in required_fields:
                assert field in clip, f"Missing field: {field}"
    
    def test_analyze_validates_timecodes(self, client, mock_file_setup):
        """Analysis should validate timecodes against video duration"""
        file_id = mock_file_setup
        
        response = client.post(f"/analyze/{file_id}?provider=mock")
        
        assert response.status_code == 200
        data = response.json()
        
        video_duration = data["video_duration"]
        clips = data["viral_clips"]
        
        for clip in clips:
            assert clip["start_time"] >= 0, "Start time should be non-negative"
            assert clip["end_time"] <= video_duration, f"End time exceeds video duration"
            assert clip["start_time"] < clip["end_time"], "Start should be before end"
    
    def test_analyze_missing_transcription(self, client):
        """Should return 404 if transcription not found"""
        response = client.post("/analyze/nonexistent_file?provider=mock")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetCandidatesEndpoint:
    """Test the GET /clips/{file_id}/candidates endpoint"""
    
    def test_get_candidates_from_memory(self, client, mock_file_setup):
        """Should retrieve candidates from memory after analysis"""
        file_id = mock_file_setup
        
        # First analyze to populate candidates
        client.post(f"/analyze/{file_id}?provider=mock")
        
        # Then get candidates
        response = client.get(f"/clips/{file_id}/candidates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "file_id" in data
        assert "candidates" in data
        assert "count" in data
        assert data["file_id"] == file_id
        assert len(data["candidates"]) > 0
        assert data["count"] == len(data["candidates"])
    
    def test_get_candidates_from_file_fallback(self, client, mock_file_setup):
        """Should load from file if not in memory"""
        file_id = mock_file_setup
        
        # Analyze first to create file
        client.post(f"/analyze/{file_id}?provider=mock")
        
        # Clear memory
        if file_id in clip_candidates_store:
            del clip_candidates_store[file_id]
        
        # Should still work by loading from file
        response = client.get(f"/clips/{file_id}/candidates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["candidates"]) > 0
        assert "loaded from file" in data["message"].lower()
    
    def test_get_candidates_not_found(self, client):
        """Should return 404 if no analysis exists"""
        response = client.get("/clips/nonexistent_file/candidates")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_candidates_structure(self, client, mock_file_setup):
        """Candidates should have correct structure"""
        file_id = mock_file_setup
        
        client.post(f"/analyze/{file_id}?provider=mock")
        response = client.get(f"/clips/{file_id}/candidates")
        
        assert response.status_code == 200
        candidates = response.json()["candidates"]
        
        for candidate in candidates:
            assert "start_time" in candidate
            assert "end_time" in candidate
            assert "title" in candidate
            assert "reason" in candidate
            assert "virality_score" in candidate
            assert isinstance(candidate["virality_score"], int)
            assert 1 <= candidate["virality_score"] <= 10


class TestExtractClipsEndpoint:
    """Test the /extract-clips endpoint with new Human-in-the-Loop features"""
    
    def test_extract_clips_request_structure(self, client, mock_file_setup):
        """Should accept ExtractClipsRequest with clip_indices, platform, etc."""
        file_id = mock_file_setup
        
        # Analyze first
        client.post(f"/analyze/{file_id}?provider=mock")
        
        # Test request structure (will fail on actual rendering, but validates request)
        request_data = {
            "clip_indices": [0],
            "enable_reframe": True,
            "enable_subtitles": True,
            "platform": "tiktok"
        }
        
        # This will fail at rendering stage, but we can check request validation
        response = client.post(
            f"/extract-clips/{file_id}",
            json=request_data
        )
        
        # Should not be 422 (validation error)
        assert response.status_code != 422
    
    def test_platform_parameter_validation(self, client, mock_file_setup):
        """Should accept different platform values"""
        file_id = mock_file_setup
        
        client.post(f"/analyze/{file_id}?provider=mock")
        
        platforms = ["tiktok", "youtube", "instagram"]
        
        for platform in platforms:
            request_data = {
                "clip_indices": [0],
                "platform": platform
            }
            
            response = client.post(
                f"/extract-clips/{file_id}",
                json=request_data
            )
            
            # Should accept the platform parameter (even if rendering fails)
            assert response.status_code != 422


class TestTimecodeValidationIntegration:
    """Integration tests for timecode validation across the pipeline"""
    
    def test_end_to_end_timecode_validation(self, client, mock_file_setup):
        """Test timecode validation from analysis to candidate retrieval"""
        file_id = mock_file_setup
        
        # Step 1: Analyze
        analyze_response = client.post(f"/analyze/{file_id}?provider=mock")
        assert analyze_response.status_code == 200
        
        video_duration = analyze_response.json()["video_duration"]
        
        # Step 2: Get candidates
        candidates_response = client.get(f"/clips/{file_id}/candidates")
        assert candidates_response.status_code == 200
        
        candidates = candidates_response.json()["candidates"]
        
        # Step 3: Validate all timecodes
        for candidate in candidates:
            start = candidate["start_time"]
            end = candidate["end_time"]
            
            assert start >= 0, f"Invalid start time: {start}"
            assert end <= video_duration, f"End time {end} exceeds duration {video_duration}"
            assert start < end, f"Start {start} not before end {end}"
            
            # Check duration constraints
            duration = end - start
            assert duration >= 10, f"Duration {duration}s below minimum"
    
    def test_custom_clips_timecode_validation(self, client, mock_file_setup):
        """Custom clips from frontend should be validated"""
        file_id = mock_file_setup
        
        # Create custom clip with invalid timecodes
        custom_clips = [
            {
                "start_time": -5.0,  # Invalid: negative
                "end_time": 1000.0,  # Invalid: exceeds duration
                "title": "Test Clip",
                "hook": "TEST"
            }
        ]
        
        request_data = {
            "custom_clips": custom_clips,
            "platform": "tiktok"
        }
        
        # Should either reject or auto-correct invalid timecodes
        response = client.post(
            f"/extract-clips/{file_id}",
            json=request_data
        )
        
        # Should not crash (even if rendering fails for other reasons)
        assert response.status_code != 500


class TestCandidateStoragePersistence:
    """Test candidate storage and retrieval"""
    
    def test_multiple_files_independent_storage(self, client):
        """Different files should have independent candidate storage"""
        file_ids = ["file_1", "file_2", "file_3"]
        
        # Store candidates for multiple files
        for file_id in file_ids:
            clip_candidates_store[file_id] = [
                {
                    "start_time": 0.0,
                    "end_time": 30.0,
                    "title": f"Clip for {file_id}",
                    "reason": "Test",
                    "virality_score": 8,
                    "hook": "TEST"
                }
            ]
        
        # Verify independent retrieval
        for file_id in file_ids:
            response = client.get(f"/clips/{file_id}/candidates")
            assert response.status_code == 200
            
            candidates = response.json()["candidates"]
            assert len(candidates) == 1
            assert file_id in candidates[0]["title"]
        
        # Cleanup
        for file_id in file_ids:
            if file_id in clip_candidates_store:
                del clip_candidates_store[file_id]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
