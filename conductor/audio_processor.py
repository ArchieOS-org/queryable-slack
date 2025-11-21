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
    quant: Optional[str] = "4bit"
) -> Optional[LightningWhisperMLX]:
    """Load Lightning Whisper MLX model (cached globally)."""
    global _whisper_model
    
    if _whisper_model is None and LightningWhisperMLX is not None:
        try:
            logger.info(f"Loading Lightning Whisper MLX model: {model_name} (batch_size={batch_size}, quant={quant})")
            _whisper_model = LightningWhisperMLX(
                model=model_name,
                batch_size=batch_size,
                quant=quant
            )
            logger.info("✅ Lightning Whisper MLX model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load Whisper model: {e}")
            return None
    
    return _whisper_model


def transcribe_audio(
    audio_path: Path,
    model_name: str = "distil-medium.en",
    batch_size: int = 12,
    quant: Optional[str] = "4bit",
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transcribe audio file using Lightning Whisper MLX.
    
    Args:
        audio_path: Path to audio file
        model_name: Whisper model to use (default: "distil-medium.en" for English)
        batch_size: Batch size for processing (default: 12)
        quant: Quantization level ("4bit", "8bit", or None)
        language: Language code (e.g., "en", "es") - if None, auto-detect
        
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
        
        # Transcribe audio
        result = whisper.transcribe(
            audio_path=str(audio_path),
            language=language
        )
        
        return {
            "text": result.get('text', ''),
            "language": result.get('language', 'unknown'),
            "segments": result.get('segments', []),
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
    quant: Optional[str] = "4bit"
) -> Dict[str, Any]:
    """
    Complete audio processing pipeline: transcribe audio file.
    
    Args:
        audio_path: Path to audio file
        model_name: Whisper model to use
        batch_size: Batch size for processing
        quant: Quantization level
        
    Returns:
        Dictionary containing transcription results
    """
    return transcribe_audio(
        audio_path=audio_path,
        model_name=model_name,
        batch_size=batch_size,
        quant=quant
    )

