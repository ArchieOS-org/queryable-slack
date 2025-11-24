"""
Vercel serverless function to migrate ChromaDB data to Supabase vecs.

This runs on Vercel where DATABASE_URL is accessible.
Call this endpoint once to migrate all data.
"""

import os
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mangum import Mangum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class MigrationRequest(BaseModel):
    secret: str
    chromadb_path: str = None  # Not used - data must be uploaded separately


@app.post("/api/migrate")
async def migrate_endpoint(request: MigrationRequest):
    """
    Migrate ChromaDB data to Supabase vecs.
    
    Note: This requires ChromaDB data to be accessible from Vercel.
    For now, this endpoint is a placeholder - actual migration should
    be done via the migration script run locally with MCP tools.
    """
    # Verify secret
    expected_secret = os.environ.get("MIGRATION_SECRET", "migrate-now-2024")
    if request.secret != expected_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "message": "Migration endpoint ready",
        "note": "Use conductor/migrate_direct_mcp.py with MCP tools instead",
        "status": "Use SQL files in /tmp/migration_batch_*.sql with MCP execute_sql"
    }


handler = Mangum(app)


