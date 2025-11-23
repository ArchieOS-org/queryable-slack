"""
Video processing module for extracting frames, audio, and generating descriptions.

Uses FFmpeg for frame extraction and MLX-VLM for video understanding.
Optimized for Apple Silicon (M2 Max).
"""

import logging
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

try:
    import ffmpeg
    
    # Check if ffmpeg binary is available (try common paths)
    FFMPEG_PATH = None
    for path in ['/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', 'ffmpeg']:
        try:
            result = subprocess.run([path, '-version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                FFMPEG_PATH = path
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if FFMPEG_PATH is None:
        ffmpeg = None
    else:
        # Set ffmpeg binary path for ffmpeg-python
        os.environ['FFMPEG_BINARY'] = FFMPEG_PATH
        ffprobe_path = FFMPEG_PATH.replace('ffmpeg', 'ffprobe')
        if os.path.exists(ffprobe_path):
            os.environ['FFPROBE_BINARY'] = ffprobe_path
except ImportError:
    ffmpeg = None
    FFMPEG_PATH = None

try:
    from mlx_vlm import load as mlx_vlm_load, generate as mlx_vlm_generate
    from mlx_vlm.video_generate import extract_frames
    from mlx_vlm.prompt_utils import apply_chat_template
except ImportError:
    mlx_vlm_load = None
    mlx_vlm_generate = None
    extract_frames = None
    apply_chat_template = None

logger = logging.getLogger(__name__)

# Log FFmpeg status if available (only once, at debug level to reduce noise)
if FFMPEG_PATH:
    logger.debug(f"FFmpeg available at: {FFMPEG_PATH}")
else:
    logger.debug("FFmpeg not available - video processing will be limited")

# Global model cache to avoid reloading
_vlm_model = None
_vlm_processor = None
_vlm_config = None


def _parse_frame_rate(frame_rate_str: str) -> float:
    """Safely parse frame rate string like '30/1' or '29.97' to float."""
    try:
        if '/' in frame_rate_str:
            num, den = frame_rate_str.split('/')
            return float(num) / float(den) if float(den) != 0 else 0.0
        else:
            return float(frame_rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _load_vlm_model(model_name: str = "mlx-community/Qwen2-VL-2B-Instruct-4bit"):
    """Load MLX-VLM model (cached globally). Reuses image processor's model if available."""
    global _vlm_model, _vlm_processor, _vlm_config
    
    # Try to reuse the image processor's model first (already loaded)
    try:
        from conductor.image_processor import _load_mlx_vlm_model
        img_model, img_processor, img_config = _load_mlx_vlm_model()
        if img_model is not None and img_processor is not None and img_config is not None:
            logger.debug("Reusing MLX-VLM model from image processor for video")
            return img_model, img_processor, img_config
    except Exception as e:
        logger.debug(f"Could not reuse image processor model: {e}")
    
    # Otherwise, load our own instance
    if _vlm_model is None and mlx_vlm_load is not None:
        try:
            logger.info(f"Loading MLX-VLM model for video: {model_name}")
            _vlm_model, _vlm_processor = mlx_vlm_load(model_name)
            if load_config is not None:
                _vlm_config = load_config(model_name)
            else:
                # Fallback: try to get config from model
                try:
                    _vlm_config = _vlm_model.config if hasattr(_vlm_model, 'config') else None
                except:
                    _vlm_config = None
            logger.info("✅ MLX-VLM model loaded successfully for video")
        except Exception as e:
            logger.warning(f"Failed to load MLX-VLM model for video: {e}")
            return None, None, None
    
    return _vlm_model, _vlm_processor, _vlm_config


def extract_video_metadata(video_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from video file using FFprobe.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dictionary containing video metadata (duration, resolution, codec, etc.)
    """
    if ffmpeg is None or FFMPEG_PATH is None:
        logger.debug("FFmpeg not available, cannot extract video metadata")
        return {}
    
    try:
        probe = ffmpeg.probe(str(video_path))
        video_info = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_info = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        
        # Get duration from format (more reliable than stream duration)
        format_info = probe.get('format', {})
        duration = float(format_info.get('duration', 0))
        
        metadata = {
            "has_video": video_info is not None,
            "has_audio": audio_info is not None,
            "duration": duration,
        }
        
        if video_info:
            metadata.update({
                "width": int(video_info.get('width', 0)),
                "height": int(video_info.get('height', 0)),
                "codec": video_info.get('codec_name', 'unknown'),
                "fps": _parse_frame_rate(video_info.get('r_frame_rate', '0/1')) if video_info.get('r_frame_rate') else 0,
                "bitrate": int(video_info.get('bit_rate', 0)),
            })
        
        if audio_info:
            metadata.update({
                "audio_codec": audio_info.get('codec_name', 'unknown'),
                "audio_sample_rate": int(audio_info.get('sample_rate', 0)),
                "audio_channels": int(audio_info.get('channels', 0)),
            })
        
        return metadata
    except Exception as e:
        logger.warning(f"Failed to extract video metadata from {video_path.name}: {e}")
        return {}


def extract_video_frames(
    video_path: Path,
    fps: float = 1.0,
    max_frames: int = 30,
    max_duration_seconds: float = 600.0,  # Limit to 10 minutes for processing window
    max_file_size_mb: float = 2000.0  # Allow up to 2GB, but process adaptively
) -> List[Path]:
    """
    Extract frames from video using FFmpeg with adaptive limits based on file size/duration.
    Large videos are processed with lower FPS and fewer frames, but not skipped.
    
    Args:
        video_path: Path to video file
        fps: Base frames per second to extract (will be reduced for large files)
        max_frames: Maximum number of frames to extract (will be reduced for large files)
        max_duration_seconds: Maximum duration window to process (default: 10 minutes)
        max_file_size_mb: Maximum file size warning threshold (default: 2GB)
        
    Returns:
        List of paths to extracted frame images
    """
    if ffmpeg is None or FFMPEG_PATH is None:
        logger.debug("FFmpeg not available, cannot extract video frames")
        return []
    
    try:
        # Get file size and adjust processing parameters adaptively
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        
        # Get video duration from metadata
        metadata = extract_video_metadata(video_path)
        duration = metadata.get('duration', 0)
        has_video = metadata.get('has_video', True)
        
        # Check if this is an audio-only file (no video stream)
        if not has_video:
            logger.info(f"File {video_path.name} is audio-only (no video stream), skipping frame extraction")
            return []
        has_video = metadata.get('has_video', True)
        
        # Check if this is an audio-only file (no video stream)
        if not has_video:
            logger.info(f"File {video_path.name} is audio-only (no video stream), skipping frame extraction")
            return []
        
        # Adaptive processing: adjust FPS and max_frames based on file size and duration
        adaptive_fps = fps
        adaptive_max_frames = max_frames
        process_duration = duration
        
        if file_size_mb > 1000:  # > 1GB
            # Very large files: reduce FPS significantly
            adaptive_fps = 0.5  # Extract every 2 seconds
            adaptive_max_frames = 20  # Fewer frames
            logger.info(f"Large video ({file_size_mb:.1f}MB): using adaptive FPS={adaptive_fps}, max_frames={adaptive_max_frames}")
        elif file_size_mb > 500:  # > 500MB
            # Large files: reduce FPS moderately
            adaptive_fps = 0.75  # Extract every ~1.3 seconds
            adaptive_max_frames = 25
            logger.info(f"Large video ({file_size_mb:.1f}MB): using adaptive FPS={adaptive_fps}, max_frames={adaptive_max_frames}")
        
        # For very long videos, sample evenly across duration or focus on first portion
        if duration > max_duration_seconds:
            # Long video: sample evenly across first max_duration_seconds
            process_duration = max_duration_seconds
            # Adjust FPS to get good coverage
            adaptive_fps = max(adaptive_fps, adaptive_max_frames / max_duration_seconds)
            logger.info(f"Long video ({duration:.1f}s): processing first {max_duration_seconds}s with FPS={adaptive_fps:.2f}")
        
        output_dir = tempfile.mkdtemp(prefix="video_frames_")
        output_pattern = os.path.join(output_dir, "frame_%04d.jpg")
        
        # Extract frames using FFmpeg with max_pixels limit (224x224 as per MLX-VLM recommendations)
        # Scale frames down to prevent memory issues - this is the key optimization
        try:
            result = (
                ffmpeg
                .input(str(video_path), t=process_duration if duration > max_duration_seconds else None)
                .filter('fps', fps=adaptive_fps)
                .filter('scale', 224, -1)  # Scale to max 224px width, maintain aspect ratio (per MLX-VLM recommendations)
                .output(output_pattern, vframes=adaptive_max_frames)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
        except ffmpeg.Error as e:
            # Log the actual FFmpeg error - extract meaningful error message
            stderr_output = e.stderr.decode('utf-8') if e.stderr else str(e)
            
            # Extract the actual error message (skip version info and config lines)
            error_lines = stderr_output.split('\n')
            actual_error = []
            in_version_block = False
            for line in error_lines:
                line_lower = line.lower()
                # Skip version/configuration header block
                if 'ffmpeg version' in line_lower or 'built with' in line_lower:
                    in_version_block = True
                    continue
                if in_version_block and ('configuration:' in line_lower or line.strip().startswith('--')):
                    continue
                if in_version_block and line.strip() and not line.strip().startswith('--'):
                    in_version_block = False
                
                # Collect actual error messages
                if not in_version_block and line.strip():
                    # Skip common non-error lines
                    if not any(skip in line_lower for skip in ['lib', 'configuration', 'built with', 'ffmpeg version']):
                        actual_error.append(line.strip())
            
            error_msg = '\n'.join(actual_error[:5])  # First 5 meaningful lines
            if not error_msg:
                error_msg = stderr_output[:300]  # Fallback to first 300 chars
            
            logger.warning(f"FFmpeg error extracting frames from {video_path.name}: {error_msg}")
            
            # Check if video has no video stream (audio-only file)
            if any(phrase in stderr_output.lower() for phrase in ["no video streams", "does not contain any stream", "video:0"]):
                logger.info(f"Video {video_path.name} has no video stream (audio-only), skipping frame extraction")
                return []
            
            # Return empty list instead of raising - allows audio extraction to continue
            return []
        
        # Collect extracted frame paths
        frame_paths = sorted([Path(output_dir) / f for f in os.listdir(output_dir) if f.endswith('.jpg')])
        logger.debug(f"Extracted {len(frame_paths)} frames from {video_path.name} (FPS={adaptive_fps:.2f}, duration={process_duration:.1f}s)")
        return frame_paths[:adaptive_max_frames]
        
    except Exception as e:
        logger.warning(f"Failed to extract frames from {video_path.name}: {e}")
        return []


def extract_video_audio(video_path: Path, output_audio_path: Optional[Path] = None, max_duration_seconds: Optional[float] = None) -> Optional[Path]:
    """
    Extract audio track from video file, optionally limiting duration.
    
    Args:
        video_path: Path to video file
        output_audio_path: Optional path for output audio file
        max_duration_seconds: Optional maximum duration to extract (for long videos)
        
    Returns:
        Path to extracted audio file, or None if extraction failed
    """
    if ffmpeg is None or FFMPEG_PATH is None:
        logger.debug("FFmpeg not available, cannot extract audio")
        return None
    
    try:
        if output_audio_path is None:
            output_audio_path = Path(tempfile.mkdtemp()) / f"{video_path.stem}_audio.wav"
        
        # Build FFmpeg command with optional duration limit
        input_stream = ffmpeg.input(str(video_path))
        if max_duration_seconds:
            input_stream = ffmpeg.input(str(video_path), t=max_duration_seconds)
        
        try:
            (
                input_stream
                .output(str(output_audio_path), acodec='pcm_s16le', ac=1, ar='16k')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            logger.debug(f"Extracted audio from {video_path.name} to {output_audio_path}")
            return output_audio_path
        except ffmpeg.Error as e:
            # Extract meaningful error message (skip version info)
            stderr_output = e.stderr.decode('utf-8') if e.stderr else str(e)
            error_lines = stderr_output.split('\n')
            actual_error = []
            in_version_block = False
            for line in error_lines:
                line_lower = line.lower()
                if 'ffmpeg version' in line_lower or 'built with' in line_lower:
                    in_version_block = True
                    continue
                if in_version_block and ('configuration:' in line_lower or line.strip().startswith('--')):
                    continue
                if in_version_block and line.strip() and not line.strip().startswith('--'):
                    in_version_block = False
                if not in_version_block and line.strip():
                    if not any(skip in line_lower for skip in ['lib', 'configuration', 'built with', 'ffmpeg version']):
                        actual_error.append(line.strip())
            
            error_msg = '\n'.join(actual_error[:5])
            if not error_msg:
                error_msg = stderr_output[:300]
            
            logger.warning(f"FFmpeg error extracting audio from {video_path.name}: {error_msg}")
            return None
        
    except Exception as e:
        logger.warning(f"Failed to extract audio from {video_path.name}: {e}")
        return None


def generate_video_description(
    video_path: Path,
    prompt: str = "Describe what happens in this video in detail.",
    fps: float = 1.0,
    max_pixels: tuple = (224, 224)
) -> Optional[str]:
    """
    Generate description of video using MLX-VLM on extracted frames.
    
    Args:
        video_path: Path to video file
        prompt: Prompt for description generation
        fps: Frames per second to extract
        max_pixels: Maximum frame resolution
        
    Returns:
        Video description text, or None if generation failed
    """
    model, processor, config = _load_vlm_model()
    if model is None or processor is None or config is None:
        logger.warning("MLX-VLM model not available for video description")
        return None
    
    try:
        frames = extract_video_frames(video_path, fps=fps, max_frames=30)
        if not frames:
            logger.warning(f"No frames extracted from {video_path.name}")
            return None
        
        # Use MLX-VLM video understanding (if available)
        # For now, describe frames individually
        descriptions = []
        for frame_path in frames[:10]:  # Limit to 10 frames for performance
            try:
                formatted_prompt = apply_chat_template(
                    processor, config, prompt, num_images=1
                )
                output = mlx_vlm_generate(
                    model, processor, formatted_prompt, [str(frame_path)],
                    verbose=False, max_tokens=100
                )
                descriptions.append(output.text if hasattr(output, 'text') else str(output))
            except Exception as e:
                logger.debug(f"Failed to describe frame {frame_path.name}: {e}")
                continue
        
        if descriptions:
            return " | ".join(descriptions)
        return None
        
    except Exception as e:
        logger.warning(f"Failed to generate video description for {video_path.name}: {e}")
        return None


def process_video_content(
    video_path: Path,
    extract_audio: bool = True,
    generate_description: bool = True,
    fps: float = 1.0,
    max_frames: int = 30,
    max_duration_seconds: float = 600.0,  # Process up to 10 minutes
    max_file_size_mb: float = 2000.0  # Allow up to 2GB with adaptive processing
) -> Dict[str, Any]:
    """
    Process a video file to extract frames, audio, and generate descriptions.
    All videos are processed, but large/long videos use adaptive limits.
    
    Args:
        video_path: Path to video file
        extract_audio: Whether to extract audio track
        generate_description: Whether to generate video description
        fps: Base frames per second for frame extraction (will be reduced for large files)
        max_frames: Maximum number of frames to extract (will be reduced for large files)
        max_duration_seconds: Maximum duration window to process (default: 10 minutes)
        max_file_size_mb: Warning threshold for file size (default: 2GB)
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Processing video: {video_path.name}")
    
    # Get file size for adaptive processing
    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    
    # Extract metadata
    metadata = extract_video_metadata(video_path)
    duration = metadata.get('duration', 0)
    
    # Log adaptive processing for large/long videos
    if file_size_mb > 500:
        logger.info(f"Large video ({file_size_mb:.1f}MB): using adaptive processing with reduced FPS/frames")
    if duration > max_duration_seconds:
        logger.info(f"Long video ({duration:.1f}s): processing first {max_duration_seconds}s window")
    
    # Extract frames with adaptive limits (never skipped, just processed differently)
    frames = extract_video_frames(video_path, fps=fps, max_frames=max_frames, 
                                  max_duration_seconds=max_duration_seconds, 
                                  max_file_size_mb=max_file_size_mb)
    
    # Extract audio if requested (limit to processing window for long videos)
    audio_path = None
    if extract_audio:
        # For long videos, extract audio from first portion only
        if duration > max_duration_seconds:
            logger.info(f"Extracting audio from first {max_duration_seconds}s of long video")
            # Create temporary video segment for audio extraction
            try:
                temp_video = Path(tempfile.mkdtemp()) / f"{video_path.stem}_segment.mp4"
                (
                    ffmpeg
                    .input(str(video_path), t=max_duration_seconds)
                    .output(str(temp_video), vcodec='copy', acodec='copy')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                audio_path = extract_video_audio(temp_video)
                temp_video.unlink()  # Clean up temp file
            except Exception as e:
                logger.warning(f"Could not extract audio segment from long video: {e}")
                # Fall back to full video audio extraction (may be slow)
                audio_path = extract_video_audio(video_path)
        else:
            audio_path = extract_video_audio(video_path)
    
    # Generate description if requested (uses adaptive frame extraction)
    description = None
    if generate_description:
        description = generate_video_description(video_path, fps=fps)
    
    return {
        "metadata": metadata,
        "frames": [str(f) for f in frames],
        "frame_count": len(frames),
        "audio_path": str(audio_path) if audio_path else None,
        "description": description,
        "summary": description[:200] + "..." if description and len(description) > 200 else description
    }
