"""
Tests for audio processing functionality.

Tests Lightning Whisper MLX transcription.
"""

import pytest
from pathlib import Path
from conductor.audio_processor import (
    transcribe_audio,
    process_audio_content,
)


class TestAudioTranscription:
    """Tests for audio transcription."""

    def test_transcribe_audio_structure(self, tmp_path):
        """Test that transcribe_audio returns correct structure."""
        print("\n🎵 Testing audio transcription...")
        # Create a fake audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        print(f"   Created test audio file: {audio_file}")
        
        print("   Attempting transcription...")
        result = transcribe_audio(audio_file)
        print(f"   Transcription result: success={result.get('success')}, error={result.get('error')}")
        
        # Should return dict with expected keys
        assert isinstance(result, dict)
        assert "text" in result
        assert "language" in result
        assert "segments" in result
        assert "success" in result
        assert "error" in result
        
        assert isinstance(result["success"], bool)
        assert isinstance(result["segments"], list)
        print("   ✅ Audio transcription structure is correct")

    def test_transcribe_nonexistent_audio(self):
        """Test that transcribing nonexistent file handles gracefully."""
        fake_path = Path("/nonexistent/audio.mp3")
        
        result = transcribe_audio(fake_path)
        
        # Should return dict with success=False, not crash
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] is not None

    def test_transcribe_invalid_audio_file(self, tmp_path):
        """Test that transcribing invalid audio file handles gracefully."""
        # Create a text file with .mp3 extension
        fake_audio = tmp_path / "fake.mp3"
        fake_audio.write_text("This is not an audio file")
        
        result = transcribe_audio(fake_audio)
        
        # Should return dict, not crash
        assert isinstance(result, dict)
        # May succeed or fail depending on Whisper's ability to handle the file
        assert "success" in result


class TestAudioProcessingPipeline:
    """Tests for complete audio processing pipeline."""

    def test_process_audio_content(self, tmp_path):
        """Test that process_audio_content returns correct structure."""
        # Create a fake audio file
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        
        result = process_audio_content(audio_file)
        
        # Should return dict with expected keys
        assert isinstance(result, dict)
        assert "text" in result
        assert "language" in result
        assert "segments" in result
        assert "success" in result


class TestAudioProcessingErrorHandling:
    """Tests for error handling in audio processing."""

    def test_process_audio_with_missing_dependencies(self, tmp_path):
        """Test that processing handles missing dependencies gracefully."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        result = process_audio_content(audio_file)
        
        # Should return dict, not crash
        assert isinstance(result, dict)
        # If dependencies missing, success should be False
        if not result.get("success"):
            assert result.get("error") is not None

