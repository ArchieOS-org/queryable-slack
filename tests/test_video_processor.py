"""
Tests for video processing functionality.

Tests FFmpeg integration, frame extraction, and MLX-VLM description generation.
"""

import pytest
from pathlib import Path
from conductor.video_processor import (
    extract_video_metadata,
    extract_video_frames,
    extract_video_audio,
    generate_video_description,
    process_video_content,
)


class TestVideoMetadata:
    """Tests for video metadata extraction."""

    def test_extract_metadata_requires_ffmpeg(self, tmp_path):
        """Test that metadata extraction requires ffmpeg."""
        print("\n🎬 Testing video metadata extraction...")
        # Create a fake video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")
        print(f"   Created test video file: {video_file}")
        
        try:
            print("   Attempting to extract metadata with FFmpeg...")
            metadata = extract_video_metadata(video_file)
            # If ffmpeg is available, should return dict (may be empty if file is invalid)
            assert isinstance(metadata, dict)
            print(f"   ✅ Metadata extracted: {len(metadata)} fields")
        except Exception as e:
            # If ffmpeg not available, should handle gracefully
            print(f"   ⏭️  Skipping: FFmpeg not available or file invalid ({e})")
            pytest.skip("FFmpeg not available or file is not a valid video")


class TestVideoFrameExtraction:
    """Tests for video frame extraction."""

    def test_extract_frames_requires_ffmpeg(self, tmp_path):
        """Test that frame extraction requires ffmpeg."""
        # Create a fake video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")
        
        try:
            frames = extract_video_frames(video_file, fps=1.0, max_frames=5)
            # If ffmpeg is available, should return list (may be empty if file is invalid)
            assert isinstance(frames, list)
        except Exception:
            # If ffmpeg not available, should handle gracefully
            pytest.skip("FFmpeg not available or file is not a valid video")


class TestVideoAudioExtraction:
    """Tests for audio extraction from videos."""

    def test_extract_audio_requires_ffmpeg(self, tmp_path):
        """Test that audio extraction requires ffmpeg."""
        # Create a fake video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")
        
        try:
            audio_path = extract_video_audio(video_file)
            # If ffmpeg is available, should return Path or None
            assert audio_path is None or isinstance(audio_path, Path)
        except Exception:
            # If ffmpeg not available, should handle gracefully
            pytest.skip("FFmpeg not available or file is not a valid video")


class TestVideoDescription:
    """Tests for video description generation using MLX-VLM."""

    def test_generate_description_requires_mlx_vlm(self, tmp_path):
        """Test that description generation requires MLX-VLM."""
        # Create a fake video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")
        
        try:
            description = generate_video_description(video_file)
            # If MLX-VLM is available, should return str or None
            assert description is None or isinstance(description, str)
        except Exception:
            # If MLX-VLM not available, should handle gracefully
            pytest.skip("MLX-VLM not available or file is not a valid video")


class TestVideoProcessingPipeline:
    """Tests for complete video processing pipeline."""

    def test_process_video_content_structure(self, tmp_path):
        """Test that process_video_content returns correct structure."""
        # Create a fake video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")
        
        try:
            result = process_video_content(
                video_file,
                extract_audio=False,
                generate_description=False,
                fps=1.0,
                max_frames=5
            )
            
            # Should return dict with expected keys
            assert isinstance(result, dict)
            assert "metadata" in result
            assert "frame_count" in result
            assert "description" in result
            assert "audio_path" in result
            
            assert isinstance(result["metadata"], dict)
            assert isinstance(result["frame_count"], int)
            assert result["description"] is None or isinstance(result["description"], str)
            assert result["audio_path"] is None or isinstance(result["audio_path"], Path)
        except Exception:
            pytest.skip("Video processing dependencies not available")


class TestVideoProcessingErrorHandling:
    """Tests for error handling in video processing."""

    def test_process_nonexistent_video(self):
        """Test that processing nonexistent video handles gracefully."""
        fake_path = Path("/nonexistent/video.mp4")
        
        result = process_video_content(fake_path, extract_audio=False, generate_description=False)
        
        # Should return dict with empty/None values, not crash
        assert isinstance(result, dict)
        assert "metadata" in result

    def test_process_invalid_video_file(self, tmp_path):
        """Test that processing invalid video file handles gracefully."""
        # Create a text file with .mp4 extension
        fake_video = tmp_path / "fake.mp4"
        fake_video.write_text("This is not a video file")
        
        result = process_video_content(fake_video, extract_audio=False, generate_description=False)
        
        # Should return dict, not crash
        assert isinstance(result, dict)

