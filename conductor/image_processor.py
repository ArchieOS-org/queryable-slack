"""
Image processing module for generating descriptions using MLX-VLM.

Optimized for Apple Silicon (M2 Max) with batch processing support.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from PIL import Image
import os

# Lazy load MLX-VLM to avoid dependency issues if not installed
MLX_VLM_AVAILABLE = False
MLX_VLM_LOAD_ERROR = None

try:
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    MLX_VLM_AVAILABLE = True
except ImportError as e:
    MLX_VLM_LOAD_ERROR = str(e)
    logging.warning(f"mlx-vlm not installed: {e}. Image descriptions will be skipped.")
except Exception as e:
    # Catch any other import errors (e.g., missing dependencies like torchvision)
    MLX_VLM_LOAD_ERROR = str(e)
    logging.warning(f"mlx-vlm import failed: {e}. Image descriptions will be skipped.")

logger = logging.getLogger(__name__)

# Cache MLX-VLM model globally
_mlx_vlm_model = None
_mlx_vlm_processor = None
_mlx_vlm_config = None
_mlx_vlm_load_failed = False  # Track if loading failed permanently


def _load_mlx_vlm_model():
    """Load MLX-VLM model (cached globally)."""
    global _mlx_vlm_model, _mlx_vlm_processor, _mlx_vlm_config, _mlx_vlm_load_failed
    
    # If we've already failed to load, don't try again
    if _mlx_vlm_load_failed:
        logger.debug("MLX-VLM model load previously failed, skipping")
        return None, None, None
    
    # If model already loaded, return it
    if _mlx_vlm_model is not None:
        return _mlx_vlm_model, _mlx_vlm_processor, _mlx_vlm_config
    
    # Try to load if available
    if not MLX_VLM_AVAILABLE:
        logger.debug("MLX-VLM not available, marking as failed")
        _mlx_vlm_load_failed = True
        return None, None, None
    
    try:
        model_path = "mlx-community/Qwen2-VL-2B-Instruct-4bit"
        logger.info(f"Loading MLX-VLM model ({model_path})... This may take a moment.")
        _mlx_vlm_model, _mlx_vlm_processor = load(model_path)
        _mlx_vlm_config = load_config(model_path)
        logger.info("✅ MLX-VLM model loaded successfully")
        return _mlx_vlm_model, _mlx_vlm_processor, _mlx_vlm_config
    except Exception as e:
        # Mark as failed so we don't keep trying
        _mlx_vlm_load_failed = True
        error_msg = str(e)
        logger.warning(f"Failed to load MLX-VLM model: {error_msg[:200]}")
        # Check for specific dependency errors
        if "torchvision" in error_msg.lower() or "AutoVideoProcessor" in error_msg:
            logger.warning("MLX-VLM requires torchvision which is not installed. All image descriptions will be skipped.")
        return None, None, None


def _check_and_resize_image(image_path: Path, max_dimension: int = 2048, max_file_size_mb: int = 50) -> Optional[Path]:
    """
    Check image size and resize if too large to prevent memory issues.
    
    Args:
        image_path: Path to the image file
        max_dimension: Maximum width or height in pixels
        max_file_size_mb: Maximum file size in MB before checking dimensions
        
    Returns:
        Path to (possibly resized) image, or None if image is too large/problematic
    """
    try:
        # Check file size first
        file_size_mb = image_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_file_size_mb:
            logger.debug(f"Image {image_path.name} is large ({file_size_mb:.1f}MB), checking dimensions...")
        
        # Open and check dimensions
        with Image.open(image_path) as img:
            width, height = img.size
            total_pixels = width * height
            
            # Check if image is too large (prevent memory allocation issues)
            # MLX Metal buffer limit is ~20GB, so we limit to reasonable size
            max_pixels = max_dimension * max_dimension
            
            if total_pixels > max_pixels or width > max_dimension or height > max_dimension:
                logger.info(f"Resizing large image {image_path.name} from {width}x{height} to max {max_dimension}px")
                
                # Calculate new dimensions maintaining aspect ratio
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert RGBA to RGB if saving as JPEG (JPEG doesn't support transparency)
                if resized_img.mode == 'RGBA' and image_path.suffix.lower() in ['.jpg', '.jpeg']:
                    # Create RGB background (white)
                    rgb_img = Image.new('RGB', resized_img.size, (255, 255, 255))
                    rgb_img.paste(resized_img, mask=resized_img.split()[3])  # Use alpha channel as mask
                    resized_img = rgb_img
                
                # Save to temporary file
                temp_path = image_path.parent / f".temp_resized_{image_path.name}"
                # Determine format from original extension or use PNG for RGBA
                save_format = 'PNG' if resized_img.mode == 'RGBA' else None
                resized_img.save(temp_path, format=save_format, quality=85, optimize=True)
                logger.debug(f"Saved resized image to {temp_path.name}")
                return temp_path
            else:
                # Image is fine, return original path
                return image_path
                
    except Exception as e:
        logger.warning(f"Failed to check/resize image {image_path.name}: {e}")
        return None


def generate_image_description(image_path: Path, prompt: str = "Describe this image in detail.") -> Dict[str, Any]:
    """
    Generate a detailed description of an image using MLX-VLM.
    
    Args:
        image_path: Path to the image file
        prompt: Prompt for description generation
        
    Returns:
        Dictionary with description, success status, and metadata
    """
    # Quick check - if MLX-VLM is not available, skip immediately
    if not MLX_VLM_AVAILABLE:
        return {
            "description": "[SKIPPED: MLX-VLM not available]",
            "success": False,
            "error": MLX_VLM_LOAD_ERROR or "mlx-vlm not installed"
        }
    
    # Check if we've already failed to load (avoid repeated attempts)
    if _mlx_vlm_load_failed:
        return {
            "description": "[SKIPPED: MLX-VLM model failed to load]",
            "success": False,
            "error": "Model loading failed (likely missing torchvision dependency)"
        }
    
    # Try to load model (will use cache if already loaded, or mark as failed if it fails)
    model, processor, config = _load_mlx_vlm_model()
    if model is None or processor is None or config is None:
        # _load_mlx_vlm_model already set _mlx_vlm_load_failed = True
        return {
            "description": "[SKIPPED: Failed to load MLX-VLM model]",
            "success": False,
            "error": "Model loading failed"
        }
    
    # Check and resize image if needed to prevent memory issues
    processed_image_path = _check_and_resize_image(image_path, max_dimension=2048)
    if processed_image_path is None:
        return {
            "description": "[SKIPPED: Image too large or invalid]",
            "success": False,
            "error": "Image size check failed"
        }
    
    temp_file_created = processed_image_path != image_path
    
    try:
        logger.debug(f"Generating description for image: {image_path.name}")
        
        # Prepare image input (use processed/resized image)
        image_input = [str(processed_image_path)]
        
        # Apply chat template
        formatted_prompt = apply_chat_template(
            processor, config, prompt, num_images=1
        )
        
        # Generate description with memory-safe settings
        output = generate(
            model, processor, formatted_prompt, image_input,
            verbose=False, 
            max_tokens=200  # Limit description length
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
        error_msg = str(e)
        # Check for memory-related errors
        if "malloc" in error_msg or "buffer size" in error_msg or "memory" in error_msg.lower():
            logger.warning(f"Memory error processing {image_path.name}: {error_msg[:200]}")
            return {
                "description": "[SKIPPED: Image too large for available memory]",
                "success": False,
                "error": f"Memory allocation error: {error_msg[:100]}"
            }
        else:
            logger.warning(f"Failed to generate description for {image_path.name}: {error_msg[:200]}")
            return {
                "description": f"[ERROR: Could not describe image {image_path.name} - {error_msg[:100]}]",
                "success": False,
                "error": error_msg[:200]
            }
    finally:
        # Clean up temporary resized image if created
        if temp_file_created and processed_image_path.exists():
            try:
                processed_image_path.unlink()
                logger.debug(f"Cleaned up temporary resized image: {processed_image_path.name}")
            except Exception as e:
                logger.debug(f"Failed to clean up temp file {processed_image_path.name}: {e}")


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

