"""
Configuration constants for Conductor.

Centralized configuration for database paths and other settings.
"""

from pathlib import Path

# Default database path - local storage for faster access
DEFAULT_DB_PATH = Path("/Users/noahdeskin/slack-vectoriezed-data")

# Ensure directory exists
DEFAULT_DB_PATH.mkdir(parents=True, exist_ok=True)


