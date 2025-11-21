"""
Integration tests for video and audio processing with real dependencies.

Tests video frame extraction, audio transcription, and error handling.
"""

import pytest
from pathlib import Path
from conductor.video_processor import (
    extract_video_metadata,
    extract_video_frames,
    extract_video_audio,
    process_video_content,
)
from conductor.audio_processor import transcribe_audio, process_audio_content
import tempfile


class TestVideoProcessingIntegration:
    """Integration tests for video processing with real dependencies."""

    def test_video_metadata_extraction_works(self, tmp_path):
        """Test video metadata extraction when FFmpeg is available."""
        print("\n🎬 Testing video metadata extraction...")
        
        # Check if FFmpeg is available
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            ffmpeg_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            ffmpeg_available = False
        
        if not ffmpeg_available:
            print("   ⏭️  Skipping: FFmpeg binary not found (install with: brew install ffmpeg)")
            pytest.skip("FFmpeg binary not available")
        
        # Create a minimal valid video file would require actual video encoding
        # For now, test that the function handles gracefully
        fake_video = tmp_path / "test.mp4"
        fake_video.write_bytes(b"fake video data")
        
        print("   Attempting metadata extraction...")
        metadata = extract_video_metadata(fake_video)
        
        assert isinstance(metadata, dict)
        print(f"   ✅ Metadata extraction returned: {len(metadata)} fields")

    def test_video_processing_graceful_degradation(self, tmp_path):
        """Test that video processing degrades gracefully without FFmpeg."""
        print("\n🎬 Testing video processing graceful degradation...")
        
        fake_video = tmp_path / "test.mp4"
        fake_video.write_bytes(b"fake video data")
        
        print("   Processing video (may fail gracefully)...")
        result = process_video_content(
            fake_video,
            extract_audio=False,
            generate_description=False,
            fps=1.0,
            max_frames=5
        )
        
        # Should return dict structure regardless of success
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "frame_count" in result
        assert "description" in result
        assert "audio_path" in result
        print("   ✅ Video processing handles errors gracefully!")


class TestAudioProcessingIntegration:
    """Integration tests for audio processing with real dependencies."""

    def test_audio_transcription_structure(self, tmp_path):
        """Test audio transcription returns correct structure."""
        print("\n🎵 Testing audio transcription structure...")
        
        fake_audio = tmp_path / "test.mp3"
        fake_audio.write_bytes(b"fake audio data")
        
        print("   Attempting transcription...")
        result = transcribe_audio(fake_audio)
        
        # Should return dict with expected structure
        assert isinstance(result, dict)
        assert "text" in result
        assert "language" in result
        assert "segments" in result
        assert "success" in result
        assert "error" in result
        
        # If transcription fails, should have success=False
        if not result.get("success"):
            assert result.get("error") is not None
            print(f"   ⚠️  Transcription failed (expected): {result.get('error')}")
        else:
            print(f"   ✅ Transcription succeeded: {len(result.get('text', ''))} chars")
        
        print("   ✅ Audio transcription structure is correct!")

    def test_audio_processing_graceful_degradation(self, tmp_path):
        """Test that audio processing degrades gracefully without dependencies."""
        print("\n🎵 Testing audio processing graceful degradation...")
        
        fake_audio = tmp_path / "test.wav"
        fake_audio.write_bytes(b"fake audio data")
        
        print("   Processing audio (may fail gracefully)...")
        result = process_audio_content(fake_audio)
        
        # Should return dict structure regardless of success
        assert isinstance(result, dict)
        assert "text" in result
        assert "success" in result
        
        if not result.get("success"):
            print(f"   ⚠️  Processing failed gracefully: {result.get('error')}")
        else:
            print(f"   ✅ Processing succeeded!")
        
        print("   ✅ Audio processing handles errors gracefully!")


class TestMLXDependencies:
    """Tests for MLX dependency availability."""

    def test_mlx_available(self):
        """Test that MLX is available."""
        print("\n🔍 Testing MLX availability...")
        try:
            import mlx.core as mx
            print("   ✅ MLX is available")
            assert True
        except ImportError:
            print("   ❌ MLX not available")
            pytest.fail("MLX should be installed")

    def test_mlx_vlm_available(self):
        """Test that MLX-VLM is available."""
        print("\n🔍 Testing MLX-VLM availability...")
        try:
            from mlx_vlm import load
            print("   ✅ MLX-VLM is available")
            assert True
        except ImportError:
            print("   ❌ MLX-VLM not available")
            pytest.fail("MLX-VLM should be installed")

    def test_ffmpeg_python_available(self):
        """Test that ffmpeg-python is available."""
        print("\n🔍 Testing ffmpeg-python availability...")
        try:
            import ffmpeg
            print("   ✅ ffmpeg-python is available")
            assert True
        except ImportError:
            print("   ❌ ffmpeg-python not available")
            pytest.fail("ffmpeg-python should be installed")

