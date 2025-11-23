"""
Configuration constants for Conductor.

Centralized configuration for database paths and other settings.
"""

from pathlib import Path
import os

# Default database path - use /Users/noahdeskin/slack-vectoriezed-data
# This is the main database location for the web app and CLI tools
DEFAULT_DB_PATH = Path("/Users/noahdeskin/slack-vectoriezed-data")

# Ensure directory exists (non-blocking, with error handling)
try:
    DEFAULT_DB_PATH.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError) as e:
    # Log but don't fail - ChromaDB will create it if needed
    import logging
    logging.getLogger(__name__).warning(f"Could not create directory {DEFAULT_DB_PATH}: {e}")


