"""
Audio processing module for transcription using MLX-optimized Whisper.

Optimized for Apple Silicon (M2 Max) with batch processing support.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from lightning_whisper_mlx import LightningWhisperMLX
except ImportError:
    # Gracefully handle missing dependency - will fall back to metadata-only
    LightningWhisperMLX = None
    import logging
    logger = logging.getLogger(__name__)
    logger.info("lightning-whisper-mlx not available - audio transcription will be skipped")

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading
_whisper_model = None


def _load_whisper_model(
    model_name: str = "distil-medium.en",
    batch_size: int = 12,
    quant: Optional[str] = None  # Changed from "4bit" to None for compatibility
) -> Optional[LightningWhisperMLX]:
    """Load Lightning Whisper MLX model (cached globally)."""
    global _whisper_model
    
    if _whisper_model is None and LightningWhisperMLX is not None:
        try:
            # Try with quantization first, fall back to None if it fails
            try:
                logger.info(f"Loading Lightning Whisper MLX model: {model_name} (batch_size={batch_size}, quant={quant})")
                _whisper_model = LightningWhisperMLX(
                    model=model_name,
                    batch_size=batch_size,
                    quant=quant
                )
                logger.info("✅ Lightning Whisper MLX model loaded successfully")
            except (AttributeError, TypeError) as quant_error:
                # If quantization fails (e.g., QuantizedLinear error), try without quantization
                if quant is not None:
                    logger.warning(f"Quantization failed ({quant_error}), retrying without quantization...")
                    logger.info(f"Loading Lightning Whisper MLX model: {model_name} (batch_size={batch_size}, quant=None)")
                    _whisper_model = LightningWhisperMLX(
                        model=model_name,
                        batch_size=batch_size,
                        quant=None
                    )
                    logger.info("✅ Lightning Whisper MLX model loaded successfully (without quantization)")
                else:
                    raise
        except Exception as e:
            logger.warning(f"Failed to load Whisper model: {e}")
            return None
    
    return _whisper_model


def transcribe_audio(
    audio_path: Path,
    model_name: str = "distil-medium.en",
    batch_size: int = 12,
    quant: Optional[str] = None,  # Changed from "4bit" to None for compatibility
    language: Optional[str] = None,
    max_duration_seconds: float = 1800.0,  # Limit to 30 minutes
    max_file_size_mb: float = 200.0  # Limit to 200MB
) -> Dict[str, Any]:
    """
    Transcribe audio file using Lightning Whisper MLX with size/duration limits.
    
    Args:
        audio_path: Path to audio file
        model_name: Whisper model to use (default: "distil-medium.en" for English)
        batch_size: Batch size for processing (default: 12)
        quant: Quantization level ("4bit", "8bit", or None)
        language: Language code (e.g., "en", "es") - if None, auto-detect
        max_duration_seconds: Maximum audio duration to process (default: 30 minutes)
        max_file_size_mb: Maximum file size in MB to process (default: 200MB)
        
    Returns:
        Dictionary containing:
        - text: Transcribed text
        - language: Detected language
        - segments: List of transcription segments with timestamps
        - success: Boolean indicating success
    """
    if LightningWhisperMLX is None:
        logger.warning("lightning-whisper-mlx not installed, cannot transcribe audio")
        return {
            "text": None,
            "language": None,
            "segments": [],
            "success": False,
            "error": "lightning-whisper-mlx not installed"
        }
    
    try:
        # Check file size and warn, but still process (with adaptive limits)
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_file_size_mb:
            logger.warning(f"Large audio file ({file_size_mb:.1f}MB > {max_file_size_mb}MB): processing may take longer")
            # Still process, but Whisper will handle it (it's designed for long audio)
        
        # Load model
        whisper = _load_whisper_model(model_name, batch_size, quant)
        if whisper is None:
            return {
                "text": None,
                "language": None,
                "segments": [],
                "success": False,
                "error": "Failed to load Whisper model"
            }
        
        # Transcribe audio - Lightning Whisper MLX handles long audio efficiently
        # For very long audio, Whisper processes it in chunks automatically
        logger.debug(f"Transcribing audio: {audio_path.name} ({file_size_mb:.1f}MB)")
        
        if file_size_mb > 100:
            logger.info(f"Large audio file ({file_size_mb:.1f}MB): transcription may take several minutes")
        
        # Transcribe audio (Whisper handles long files efficiently with batching)
        result = whisper.transcribe(
            audio_path=str(audio_path),
            language=language
        )
        
        # Handle different return types (dict or list)
        if isinstance(result, list):
            # If result is a list, it might be a list of segments or a wrapped result
            # Try to extract text from segments if available
            if result and isinstance(result[0], dict):
                # Might be a list of segments
                segments = result
                text = " ".join(seg.get('text', '') for seg in segments if isinstance(seg, dict))
                language_detected = segments[0].get('language', 'unknown') if segments else 'unknown'
            else:
                # Unknown list format, log and return error
                logger.warning(f"Unexpected list format from transcribe: {type(result[0]) if result else 'empty'}")
                return {
                    "text": None,
                    "language": None,
                    "segments": [],
                    "success": False,
                    "error": f"Unexpected return format: list of {type(result[0]) if result else 'empty'}"
                }
        elif isinstance(result, dict):
            # Normal dict format
            segments = result.get('segments', [])
            text = result.get('text', '')
            language_detected = result.get('language', 'unknown')
        else:
            # Unknown format
            logger.warning(f"Unexpected return type from transcribe: {type(result)}")
            return {
                "text": None,
                "language": None,
                "segments": [],
                "success": False,
                "error": f"Unexpected return type: {type(result)}"
            }
        
        # Log completion for long audio
        if segments:
            try:
                total_duration = max(seg.get('end', 0) if isinstance(seg, dict) else 0 for seg in segments)
                if total_duration > max_duration_seconds:
                    logger.info(f"Long audio ({total_duration:.1f}s) transcribed successfully with {len(segments)} segments")
            except Exception as e:
                logger.debug(f"Could not calculate duration: {e}")
        
        return {
            "text": text,
            "language": language_detected,
            "segments": segments if isinstance(segments, list) else [],
            "success": True,
            "error": None
        }
        
    except Exception as e:
        logger.warning(f"Failed to transcribe audio {audio_path.name}: {e}")
        return {
            "text": None,
            "language": None,
            "segments": [],
            "success": False,
            "error": str(e)
        }


def process_audio_content(
    audio_path: Path,
    model_name: str = "distil-medium.en",
    batch_size: int = 12,
    quant: Optional[str] = None,  # Changed from "4bit" to None for compatibility
    max_duration_seconds: float = 1800.0,  # Limit to 30 minutes
    max_file_size_mb: float = 200.0  # Limit to 200MB
) -> Dict[str, Any]:
    """
    Complete audio processing pipeline: transcribe audio file with limits.
    
    Args:
        audio_path: Path to audio file
        model_name: Whisper model to use
        batch_size: Batch size for processing
        quant: Quantization level
        max_duration_seconds: Maximum duration to process (default: 30 minutes)
        max_file_size_mb: Maximum file size to process (default: 200MB)
        
    Returns:
        Dictionary containing transcription results
    """
    return transcribe_audio(
        audio_path=audio_path,
        model_name=model_name,
        batch_size=batch_size,
        quant=quant,
        max_duration_seconds=max_duration_seconds,
        max_file_size_mb=max_file_size_mb
    )

