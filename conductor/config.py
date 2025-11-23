"""
Configuration constants for Conductor.

Centralized configuration for database paths and other settings.
"""

from pathlib import Path
import os

# Determine if we should use Supabase vecs (pgvector) or ChromaDB
# Use vecs if DATABASE_URL is set (Supabase deployment)
USE_VECS = bool(os.environ.get('DATABASE_URL'))

# Determine database path based on environment
# On Vercel, use /tmp (writable but ephemeral) or CHROMADB_PATH env var
# For local development, use the user's local path
# Note: This is only used if USE_VECS is False (ChromaDB mode)
if os.environ.get('VERCEL'):
    # Vercel serverless environment
    # Use CHROMADB_PATH if set, otherwise use /tmp/chromadb
    # Note: /tmp is cleared between invocations, so data needs to be downloaded from Supabase Storage
    DEFAULT_DB_PATH = Path(os.environ.get('CHROMADB_PATH', '/tmp/chromadb'))
else:
    # Local development
    DEFAULT_DB_PATH = Path("/Users/noahdeskin/slack-vectoriezed-data")

# Ensure directory exists (non-blocking, with error handling)
# Only needed for ChromaDB mode
if not USE_VECS:
    try:
        DEFAULT_DB_PATH.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        # Log but don't fail - ChromaDB will create it if needed
        import logging
        logging.getLogger(__name__).warning(f"Could not create directory {DEFAULT_DB_PATH}: {e}")

# ChromaDB HTTP client URL (for remote ChromaDB server)
# If set, use HTTP client instead of PersistentClient
# Only used if USE_VECS is False
CHROMADB_URL = os.environ.get('CHROMADB_URL', None)

# Supabase DATABASE_URL (for vecs/pgvector)
# Used when USE_VECS is True
DATABASE_URL = os.environ.get('DATABASE_URL', None)


