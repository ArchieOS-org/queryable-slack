"""
Configuration constants for Conductor.

Centralized configuration for database paths and other settings.
Context7 best practice: No side effects at module level.
"""

# #region agent log
import json
import os
import time
_debug_log_path = os.environ.get('DEBUG_LOG_PATH') or ('/tmp/debug.log' if os.environ.get('VERCEL') else '/Volumes/LaCie/Coding-Projects/queryable-slack/.cursor/debug.log')
try:
    with open(_debug_log_path, 'a') as f:
        f.write(json.dumps({"location":"conductor/config.py:15","message":"config.py module loading started","data":{"file":"config.py","debug_path":_debug_log_path},"timestamp":time.time(),"sessionId":"debug-session","runId":"vercel-debug","hypothesisId":"A"})+"\n")
except: pass
# #endregion

from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

def _get_use_vecs():
    """Determine if we should use Supabase vecs (pgvector) or ChromaDB."""
    # #region agent log
    try:
        with open(_debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"conductor/config.py:_get_use_vecs","message":"_get_use_vecs called","data":{},"timestamp":time.time(),"sessionId":"debug-session","runId":"vercel-debug","hypothesisId":"B"})+"\n")
    except: pass
    # #endregion
    try:
        # Use vecs if DATABASE_URL is set (Supabase deployment)
        database_url = os.environ.get('DATABASE_URL')
        result = bool(database_url)
        # #region agent log
        try:
            with open(_debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"conductor/config.py:_get_use_vecs","message":"USE_VECS determined","data":{"DATABASE_URL_set":bool(database_url),"result":result},"timestamp":time.time(),"sessionId":"debug-session","runId":"vercel-debug","hypothesisId":"B"})+"\n")
        except: pass
        # #endregion
        return result
    except Exception as e:
        # #region agent log
        try:
            with open(_debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"conductor/config.py:_get_use_vecs","message":"Error in _get_use_vecs","data":{"error":str(e)},"timestamp":time.time(),"sessionId":"debug-session","runId":"vercel-debug","hypothesisId":"B"})+"\n")
        except: pass
        # #endregion
        logger.warning(f"Error determining USE_VECS: {e}, defaulting to False")
        return False

# Determine if we should use Supabase vecs (pgvector) or ChromaDB
USE_VECS = _get_use_vecs()

# #region agent log
try:
    with open(_debug_log_path, 'a') as f:
        f.write(json.dumps({"location":"conductor/config.py:24","message":"USE_VECS assigned","data":{"USE_VECS":USE_VECS},"timestamp":time.time(),"sessionId":"debug-session","runId":"vercel-debug","hypothesisId":"C"})+"\n")
except: pass
# #endregion

def _get_default_db_path():
    """Determine database path based on environment."""
    # Context7: Check both VERCEL and VERCEL_ENV for Vercel detection
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        # Vercel serverless environment
        # Use CHROMADB_PATH if set, otherwise use /tmp/chromadb
        # Note: /tmp is cleared between invocations, so data needs to be downloaded from Supabase Storage
        return Path(os.environ.get('CHROMADB_PATH', '/tmp/chromadb'))
    else:
        # Local development
        return Path("/Users/noahdeskin/slack-vectoriezed-data")

DEFAULT_DB_PATH = _get_default_db_path()

def ensure_db_path():
    """
    Ensure directory exists (non-blocking, with error handling).
    Only needed for ChromaDB mode.
    Safe to call at runtime, not at module level.
    """
    try:
        if not USE_VECS:
            try:
                DEFAULT_DB_PATH.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                # Log but don't fail - ChromaDB will create it if needed or fail later
                # On Vercel read-only FS (outside /tmp), this would fail but shouldn't crash app init
                logger.warning(f"Could not create directory {DEFAULT_DB_PATH}: {e}")
    except Exception as e:
        logger.warning(f"Error in config initialization: {e}")

# DO NOT call ensure_db_path() at module level on Vercel
# It should be called only when ChromaDB is actually initialized
if not (os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV')):
    # Safe to call in local dev environment
    ensure_db_path()

# ChromaDB HTTP client URL (for remote ChromaDB server)
# If set, use HTTP client instead of PersistentClient
# Only used if USE_VECS is False
CHROMADB_URL = os.environ.get('CHROMADB_URL', None)

# Supabase DATABASE_URL (for vecs/pgvector)
# Used when USE_VECS is True
DATABASE_URL = os.environ.get('DATABASE_URL', None)
