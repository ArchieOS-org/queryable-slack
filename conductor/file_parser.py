"""
File parsing wrapper for LangChain/Unstructured loaders.

Handles PDF, DOCX, TXT file extraction with error handling.
"""

import logging
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_unstructured import UnstructuredLoader

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: Path, file_type: Optional[str] = None) -> str:
    """
    Extract text content from a file using appropriate loader.

    Supports PDF, DOCX, and TXT files. Images and unsupported types are skipped.

    Args:
        file_path: Path to the file to extract text from
        file_type: File type hint (e.g., "pdf", "docx", "txt"). If None, inferred from extension.

    Returns:
        Extracted text content, or error message if extraction fails

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    # Infer file type from extension if not provided
    if file_type is None:
        file_type = file_path.suffix.lower().lstrip(".")

    file_type = file_type.lower()

    # Handle PDF files
    if file_type == "pdf":
        try:
            loader = PyPDFLoader(str(file_path))
            docs = loader.load()
            text_content = "\n\n".join([doc.page_content for doc in docs])
            logger.debug(f"Extracted {len(docs)} pages from PDF: {file_path.name}")
            return text_content
        except Exception as e:
            logger.warning(f"Failed to parse PDF {file_path.name}: {e}")
            return f"[ERROR: Could not parse file {file_path.name}]"

    # Handle DOCX files
    if file_type == "docx":
        try:
            loader = UnstructuredLoader(str(file_path))
            docs = loader.load()
            text_content = "\n\n".join([doc.page_content for doc in docs])
            logger.debug(f"Extracted content from DOCX: {file_path.name}")
            return text_content
        except Exception as e:
            logger.warning(f"Failed to parse DOCX {file_path.name}: {e}")
            return f"[ERROR: Could not parse file {file_path.name}]"

    # Handle TXT files
    if file_type == "txt":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
            logger.debug(f"Read text file: {file_path.name}")
            return text_content
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    text_content = f.read()
                logger.debug(f"Read text file with latin-1 encoding: {file_path.name}")
                return text_content
            except Exception as e:
                logger.warning(f"Failed to read text file {file_path.name}: {e}")
                return f"[ERROR: Could not parse file {file_path.name}]"
        except Exception as e:
            logger.warning(f"Failed to read text file {file_path.name}: {e}")
            return f"[ERROR: Could not parse file {file_path.name}]"

    # Skip images and unsupported types
    image_types = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"}
    if file_type in image_types:
        logger.debug(f"Skipped image: {file_path.name}")
        return f"[SKIPPED: Image file {file_path.name}]"

    # For other unsupported types, log and return placeholder
    logger.debug(f"Unsupported file type '{file_type}': {file_path.name}")
    return f"[SKIPPED: Unsupported file type {file_type}]"
