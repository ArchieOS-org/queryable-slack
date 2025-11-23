"""
Configuration constants for Conductor.

Centralized configuration for database paths and other settings.
"""

from pathlib import Path
import os

# Determine database path based on environment
# On Vercel, use /tmp (writable but ephemeral) or CHROMADB_PATH env var
# For local development, use the user's local path
if os.environ.get('VERCEL'):
    # Vercel serverless environment
    # Use CHROMADB_PATH if set, otherwise use /tmp/chromadb
    # Note: /tmp is cleared between invocations, so data needs to be downloaded from Supabase Storage
    DEFAULT_DB_PATH = Path(os.environ.get('CHROMADB_PATH', '/tmp/chromadb'))
else:
    # Local development
    DEFAULT_DB_PATH = Path("/Users/noahdeskin/slack-vectoriezed-data")

# Ensure directory exists (non-blocking, with error handling)
try:
    DEFAULT_DB_PATH.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError) as e:
    # Log but don't fail - ChromaDB will create it if needed
    import logging
    logging.getLogger(__name__).warning(f"Could not create directory {DEFAULT_DB_PATH}: {e}")

# ChromaDB HTTP client URL (for remote ChromaDB server)
# If set, use HTTP client instead of PersistentClient
CHROMADB_URL = os.environ.get('CHROMADB_URL', None)


