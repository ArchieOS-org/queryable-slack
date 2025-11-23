"""
FastAPI backend API for the React web app.

Provides REST API endpoints for querying the vector database.
Uses Context7 best practices for FastAPI.
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
# This prevents warnings when tokenizers are used after forking
import os
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

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
    use_deep_research: bool = True  # Default to True for exhaustive search
    deep_research_n_results: int = 50  # Results per query variation
    max_final_results: int = 40  # Final results after RRF fusion
    # use_refinement deprecated - query understanding now handled by system prompt


class QueryResponse(BaseModel):
    """Response model for chat queries."""
    response: str
    refined_query: Optional[str] = None
    query_num: Optional[int] = None
    retrieval_stats: Optional[Dict] = None  # Stats about retrieval process


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
        # Check if using vecs (Supabase pgvector) or ChromaDB
        from conductor.config import USE_VECS
        
        # Determine database path (only needed for ChromaDB mode)
        db_path_obj = None
        if not USE_VECS:
            # ChromaDB mode - determine path
            if os.environ.get('VERCEL'):
                # On Vercel, prefer HTTP client mode if CHROMADB_URL is set
                if os.environ.get('CHROMADB_URL'):
                    db_path_obj = None  # Will use HTTP client
                else:
                    # Use /tmp/chromadb (ephemeral, needs data download)
                    db_path_obj = Path(os.environ.get('CHROMADB_PATH', '/tmp/chromadb'))
            else:
                # Local development
                db_path_obj = Path(request.db_path) if request.db_path else DEFAULT_DB_PATH
            
            # Only check path existence if not using HTTP client
            if db_path_obj and not db_path_obj.exists():
                raise HTTPException(
                    status_code=404, 
                    detail=f"Database not found: {db_path_obj}. On Vercel, ensure DATABASE_URL is set for Supabase vecs or CHROMADB_URL is set for ChromaDB HTTP client."
                )
        
        # Step 1: Query vector database (vecs or ChromaDB - automatically selected)
        # System prompt handles query understanding
        results = query_chromadb(
            request.query,
            db_path=db_path_obj,
            use_reranking=True,
            use_cache=not request.use_deep_research,  # Disable cache for deep research
            use_hybrid=request.use_hybrid or request.use_deep_research,  # Use hybrid in deep research
            use_deep_research=request.use_deep_research,
            deep_research_n_results=request.deep_research_n_results,
            max_final_results=request.max_final_results
        )
        
        # Step 2: Format context
        context = format_context(results)
        
        # Calculate retrieval stats
        num_results = len(results.get("documents", [[]])[0]) if results.get("documents") else 0
        retrieval_stats = {
            "num_results": num_results,
            "deep_research": request.use_deep_research,
            "query_variations": request.deep_research_n_results if request.use_deep_research else 1
        }
        
        # Step 3: Query Claude with system prompt
        response = query_claude_with_system_prompt(
            query=request.query,
            context=context,
            use_thinking=request.use_thinking
        )
        
        return QueryResponse(
            response=response,
            refined_query=None,  # No longer using separate refinement step
            retrieval_stats=retrieval_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

