"""
Video processing module for extracting frames, audio, and generating descriptions.

Uses FFmpeg for frame extraction and MLX-VLM for video understanding.
Optimized for Apple Silicon (M2 Max).
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

try:
    import ffmpeg
except ImportError:
    ffmpeg = None

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

# Global model cache to avoid reloading
_vlm_model = None
_vlm_processor = None
_vlm_config = None


def _load_vlm_model(model_name: str = "mlx-community/Qwen2-VL-2B-Instruct-4bit"):
    """Load MLX-VLM model (cached globally)."""
    global _vlm_model, _vlm_processor, _vlm_config
    
    if _vlm_model is None and mlx_vlm_load is not None:
        try:
            logger.info(f"Loading MLX-VLM model: {model_name}")
            _vlm_model, _vlm_processor = mlx_vlm_load(model_name)
            _vlm_config = _vlm_model.config
            logger.info("✅ MLX-VLM model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load MLX-VLM model: {e}")
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
    if ffmpeg is None:
        logger.warning("ffmpeg-python not installed, cannot extract video metadata")
        return {}
    
    try:
        probe = ffmpeg.probe(str(video_path))
        video_info = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_info = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        
        metadata = {
            "has_video": video_info is not None,
            "has_audio": audio_info is not None,
        }
        
        if video_info:
            metadata.update({
                "width": int(video_info.get('width', 0)),
                "height": int(video_info.get('height', 0)),
                "codec": video_info.get('codec_name', 'unknown'),
                "fps": eval(video_info.get('r_frame_rate', '0/1')),
                "duration": float(video_info.get('duration', 0)),
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
    max_frames: Optional[int] = None
) -> List[Path]:
    """
    Extract keyframes from video using FFmpeg.
    
    Args:
        video_path: Path to video file
        fps: Frames per second to extract (default: 1.0 = 1 frame per second)
        max_frames: Maximum number of frames to extract (None = no limit)
        
    Returns:
        List of paths to extracted frame images (temporary files)
    """
    if ffmpeg is None:
        logger.warning("ffmpeg-python not installed, cannot extract video frames")
        return []
    
    try:
        # Create temporary directory for frames
        temp_dir = tempfile.mkdtemp(prefix="video_frames_")
        temp_dir_path = Path(temp_dir)
        
        # Extract frames using FFmpeg
        # Extract at specified fps, save as JPEG
        output_pattern = str(temp_dir_path / "frame_%04d.jpg")
        
        (
            ffmpeg
            .input(str(video_path))
            .filter('fps', fps=fps)
            .output(output_pattern, vframes=max_frames if max_frames else None)
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
        
        # Collect extracted frame paths
        frames = sorted(temp_dir_path.glob("frame_*.jpg"))
        logger.debug(f"Extracted {len(frames)} frames from {video_path.name}")
        return frames
        
    except Exception as e:
        logger.warning(f"Failed to extract frames from {video_path.name}: {e}")
        return []


def extract_video_audio(video_path: Path, output_audio_path: Optional[Path] = None) -> Optional[Path]:
    """
    Extract audio track from video file.
    
    Args:
        video_path: Path to video file
        output_audio_path: Optional path to save audio (if None, creates temp file)
        
    Returns:
        Path to extracted audio file, or None if extraction failed
    """
    if ffmpeg is None:
        logger.warning("ffmpeg-python not installed, cannot extract audio")
        return None
    
    try:
        if output_audio_path is None:
            # Create temporary audio file
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            output_audio_path = Path(temp_audio.name)
            temp_audio.close()
        
        (
            ffmpeg
            .input(str(video_path))
            .output(str(output_audio_path), acodec='libmp3lame', audio_bitrate='192k')
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
        
        logger.debug(f"Extracted audio from {video_path.name} to {output_audio_path}")
        return output_audio_path
        
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
    Generate text description of video using MLX-VLM.
    
    Args:
        video_path: Path to video file
        prompt: Text prompt for video analysis
        fps: Frames per second to process (default: 1.0)
        max_pixels: Maximum resolution for frames (width, height)
        
    Returns:
        Generated description text, or None if generation failed
    """
    if extract_frames is None or mlx_vlm_generate is None:
        logger.warning("MLX-VLM not installed, cannot generate video description")
        return None
    
    try:
        # Load model if not already loaded
        model, processor, config = _load_vlm_model()
        if model is None:
            return None
        
        # Extract frames from video
        frames = extract_frames(str(video_path), fps=fps, max_pixels=max_pixels)
        if not frames:
            logger.warning(f"No frames extracted from {video_path.name}")
            return None
        
        # Format prompt for video
        formatted_prompt = apply_chat_template(
            processor, config, prompt, num_images=len(frames)
        )
        
        # Generate description
        result = mlx_vlm_generate(
            model, processor, formatted_prompt, frames,
            verbose=False, max_tokens=300
        )
        
        description = result.text if hasattr(result, 'text') else str(result)
        logger.debug(f"Generated video description for {video_path.name}: {len(description)} chars")
        return description
        
    except Exception as e:
        logger.warning(f"Failed to generate video description for {video_path.name}: {e}")
        return None


def process_video_content(
    video_path: Path,
    extract_audio: bool = True,
    generate_description: bool = True,
    fps: float = 1.0,
    max_frames: Optional[int] = None
) -> Dict[str, Any]:
    """
    Complete video processing pipeline: extract metadata, frames, audio, and generate description.
    
    Args:
        video_path: Path to video file
        extract_audio: Whether to extract audio track for transcription
        generate_description: Whether to generate video description using MLX-VLM
        fps: Frames per second to extract (default: 1.0)
        max_frames: Maximum number of frames to extract
        
    Returns:
        Dictionary containing:
        - metadata: Video metadata
        - frame_count: Number of frames extracted
        - description: Generated video description (if enabled)
        - audio_path: Path to extracted audio (if enabled)
    """
    result = {
        "metadata": {},
        "frame_count": 0,
        "description": None,
        "audio_path": None,
    }
    
    # Extract metadata
    result["metadata"] = extract_video_metadata(video_path)
    
    # Extract frames (for description generation)
    if generate_description:
        frames = extract_video_frames(video_path, fps=fps, max_frames=max_frames)
        result["frame_count"] = len(frames)
        
        # Generate description using MLX-VLM
        if frames:
            result["description"] = generate_video_description(
                video_path, fps=fps, max_pixels=(224, 224)
            )
    
    # Extract audio track (for transcription)
    if extract_audio:
        result["audio_path"] = extract_video_audio(video_path)
    
    return result

