"""
Conductor API - Simplified for Vercel deployment
Direct Supabase queries without external imports
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from supabase import create_client, Client
from anthropic import Anthropic

app = FastAPI(
    title="Conductor API",
    description="Slack semantic search API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SessionResponse(BaseModel):
    id: str
    metadata: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    supabase_connected: bool
    version: str

# Helper function
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ValueError("Supabase credentials not set")
    return create_client(url, key)

@app.get("/")
def root():
    return {
        "name": "Conductor API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "health": "/api/health",
            "sessions": "/api/sessions",
            "docs": "/api/docs"
        }
    }

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    try:
        client = get_supabase()
        result = client.schema('vecs').from_('conductor_sessions').select('id').limit(1).execute()
        connected = True
    except Exception:
        connected = False
    
    return HealthResponse(
        status="healthy" if connected else "degraded",
        supabase_connected=connected,
        version="1.0.0"
    )

@app.get("/api/sessions", response_model=List[SessionResponse])
def get_sessions(limit: int = 10, channel: Optional[str] = None):
    try:
        client = get_supabase()
        limit = min(limit, 50)
        
        query = client.schema('vecs').from_('conductor_sessions').select('*')
        
        if channel:
            query = query.filter('metadata->>channel_name', 'eq', channel)
        
        result = query.limit(limit).execute()
        
        return [
            SessionResponse(id=s['id'], metadata=s.get('metadata', {}))
            for s in result.data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    try:
        client = get_supabase()
        result = client.schema('vecs').from_('conductor_sessions').select('*').eq('id', session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = result.data[0]
        return SessionResponse(id=session['id'], metadata=session.get('metadata', {}))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Vercel handler
from mangum import Mangum
handler = Mangum(app, lifespan="off")
