"""
FastAPI backend API for the React web app.

Provides REST API endpoints for querying the vector database.
Uses Context7 best practices for FastAPI.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import chatbot functionality
from conductor.ask import (
    query_chromadb,
    format_context,
    DEFAULT_DB_PATH
)
from conductor.prompt_refiner import (
    query_claude_with_system_prompt,
    SYSTEM_PROMPT_SEARCH_AGENT
)

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Vector Database Chatbot API",
    description="API for querying the vector database with thinking mode",
    version="1.0.0"
)

# CORS middleware for React frontend - MUST be added before routes
# Context7 best practice: Configure CORS properly for development and local network access
# For development, allow all origins to support mobile device access on local network
# In production, restrict to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development (local network access)
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


class QueryRequest(BaseModel):
    """Request model for chat queries."""
    query: str
    db_path: Optional[str] = None
    use_thinking: bool = True
    use_hybrid: bool = False
    # use_refinement deprecated - query understanding now handled by system prompt


class QueryResponse(BaseModel):
    """Response model for chat queries."""
    response: str
    refined_query: Optional[str] = None
    query_num: Optional[int] = None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Vector Database Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/query": "POST - Query the vector database",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS requests for CORS preflight."""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Query the vector database.
    
    This endpoint:
    1. Queries ChromaDB for similar sessions
    2. Formats context
    3. Queries Claude with system prompt and user message
    4. Returns the response
    """
    try:
        # Determine database path
        db_path_obj = Path(request.db_path) if request.db_path else DEFAULT_DB_PATH
        
        if not db_path_obj.exists():
            raise HTTPException(status_code=404, detail=f"Database not found: {db_path_obj}")
        
        # Step 1: Query ChromaDB (system prompt handles query understanding)
        results = query_chromadb(
            request.query,
            db_path=db_path_obj,
            use_reranking=True,
            use_cache=True,
            use_hybrid=request.use_hybrid
        )
        
        # Step 2: Format context
        context = format_context(results)
        
        # Step 3: Query Claude with system prompt
        response = query_claude_with_system_prompt(
            query=request.query,
            context=context,
            use_thinking=request.use_thinking
        )
        
        return QueryResponse(
            response=response,
            refined_query=None  # No longer using separate refinement step
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

