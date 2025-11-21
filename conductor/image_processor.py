"""
Image processing module for generating descriptions using MLX-VLM.

Optimized for Apple Silicon (M2 Max) with batch processing support.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

# Lazy load MLX-VLM to avoid dependency issues if not installed
try:
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    MLX_VLM_AVAILABLE = True
except ImportError:
    MLX_VLM_AVAILABLE = False
    logging.warning("mlx-vlm not installed. Image descriptions will be skipped.")

logger = logging.getLogger(__name__)

# Cache MLX-VLM model globally
_mlx_vlm_model = None
_mlx_vlm_processor = None
_mlx_vlm_config = None


def _load_mlx_vlm_model():
    """Load MLX-VLM model (cached globally)."""
    global _mlx_vlm_model, _mlx_vlm_processor, _mlx_vlm_config
    
    if _mlx_vlm_model is None and MLX_VLM_AVAILABLE:
        model_path = "mlx-community/Qwen2-VL-2B-Instruct-4bit"
        logger.info(f"Loading MLX-VLM model ({model_path})... This may take a moment.")
        _mlx_vlm_model, _mlx_vlm_processor = load(model_path)
        _mlx_vlm_config = load_config(model_path)
        logger.info("✅ MLX-VLM model loaded successfully")
    
    return _mlx_vlm_model, _mlx_vlm_processor, _mlx_vlm_config


def generate_image_description(image_path: Path, prompt: str = "Describe this image in detail.") -> Dict[str, Any]:
    """
    Generate a detailed description of an image using MLX-VLM.
    
    Args:
        image_path: Path to the image file
        prompt: Prompt for description generation
        
    Returns:
        Dictionary with description, success status, and metadata
    """
    if not MLX_VLM_AVAILABLE:
        return {
            "description": "[SKIPPED: mlx-vlm not installed]",
            "success": False,
            "error": "mlx-vlm not available"
        }
    
    model, processor, config = _load_mlx_vlm_model()
    if model is None:
        return {
            "description": "[SKIPPED: Failed to load MLX-VLM model]",
            "success": False,
            "error": "Model loading failed"
        }
    
    try:
        logger.debug(f"Generating description for image: {image_path.name}")
        
        # Prepare image input (can be path string or PIL Image)
        image_input = [str(image_path)]
        
        # Apply chat template
        formatted_prompt = apply_chat_template(
            processor, config, prompt, num_images=1
        )
        
        # Generate description
        output = generate(
            model, processor, formatted_prompt, image_input,
            verbose=False, max_tokens=200  # Limit description length
        )
        
        description = output.text if hasattr(output, 'text') else str(output)
        
        logger.debug(f"Generated description for {image_path.name}: {description[:100]}...")
        
        return {
            "description": description,
            "success": True,
            "prompt": prompt,
            "image_path": str(image_path)
        }
        
    except Exception as e:
        logger.warning(f"Failed to generate description for {image_path.name}: {e}")
        return {
            "description": f"[ERROR: Could not describe image {image_path.name} - {e}]",
            "success": False,
            "error": str(e)
        }


def process_image_content(image_path: Path) -> Dict[str, Any]:
    """
    Process an image file to extract description and metadata.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with description, metadata, and processing status
    """
    # Generate description using MLX-VLM
    description_result = generate_image_description(image_path)
    
    # Extract basic metadata
    metadata = {
        "filename": image_path.name,
        "file_type": image_path.suffix.lower().lstrip("."),
        "size": image_path.stat().st_size if image_path.exists() else 0,
    }
    
    return {
        "description_result": description_result,
        "metadata": metadata,
    }

