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
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

# Lazy imports will be used inside factory/startup to prevent top-level import failures
# disrupting the server initialization if a dependency is missing.

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global app instance placeholder
app = None
INIT_ERROR = None

def create_app():
    """Factory to create FastAPI app with robust import handling."""
    global app
    
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
        from dotenv import load_dotenv
        
        load_dotenv()
        
        app = FastAPI(
            title="Vector Database Chatbot API",
            description="API for querying the vector database with thinking mode",
            version="1.0.0"
        )
        
        # CORS middleware for React frontend - MUST be added before routes
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for development (local network access)
            allow_credentials=False,  # Must be False when using allow_origins=["*"]
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
            max_age=3600,
        )
        
        # Global exception handler for better error logging
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            """Global exception handler to log all errors."""
            logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error: {type(exc).__name__}: {str(exc)}",
                    "type": type(exc).__name__
                }
            )
            
        # Define models locally to avoid import issues if Pydantic fails (though if Pydantic fails, FastAPI fails)
        class QueryRequest(BaseModel):
            """Request model for chat queries."""
            query: str
            db_path: Optional[str] = None
            use_thinking: bool = True
            use_hybrid: bool = False
            use_deep_research: bool = True  # Default to True for exhaustive search
            deep_research_n_results: int = 50  # Results per query variation
            max_final_results: int = 40  # Final results after RRF fusion

        class QueryResponse(BaseModel):
            """Response model for chat queries."""
            response: str
            refined_query: Optional[str] = None
            query_num: Optional[int] = None
            retrieval_stats: Optional[Dict] = None

        class MigrateRequest(BaseModel):
            """Request model for migration batches."""
            sql: str
            batch_name: Optional[str] = None

        class MigrateResponse(BaseModel):
            """Response model for migration."""
            success: bool
            batch: Optional[str] = None
            rows_affected: Optional[int] = None
            error: Optional[str] = None

        # Define routes
        @app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "Vector Database Chatbot API",
                "version": "1.0.0",
                "endpoints": {
                    "/query": "POST - Query the vector database",
                    "/health": "GET - Health check",
                    "/migrate": "POST - Execute SQL migration batch (via /api/migrate)"
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
            # Lazy import conductor modules
            if not _import_conductor():
                raise HTTPException(
                    status_code=500,
                    detail=f"Conductor modules not available: {CONDUCTOR_IMPORT_ERROR}"
                )
            
            try:
                # Lazy import conductor config
                from conductor.config import USE_VECS
                
                # Determine database path
                db_path_obj = None
                if not USE_VECS:
                    # ChromaDB mode
                    if os.environ.get('VERCEL'):
                        if os.environ.get('CHROMADB_URL'):
                            db_path_obj = None
                        else:
                            db_path_obj = Path(os.environ.get('CHROMADB_PATH', '/tmp/chromadb'))
                    else:
                        db_path_obj = Path(request.db_path) if request.db_path else DEFAULT_DB_PATH
                    
                    if db_path_obj and not db_path_obj.exists():
                        raise HTTPException(
                            status_code=404, 
                            detail=f"Database not found: {db_path_obj}"
                        )
                
                results = query_chromadb(
                    request.query,
                    db_path=db_path_obj,
                    use_reranking=True,
                    use_cache=not request.use_deep_research,
                    use_hybrid=request.use_hybrid or request.use_deep_research,
                    use_deep_research=request.use_deep_research,
                    deep_research_n_results=request.deep_research_n_results,
                    max_final_results=request.max_final_results
                )
                
                context = format_context(results)
                num_results = len(results.get("documents", [[]])[0]) if results.get("documents") else 0
                retrieval_stats = {
                    "num_results": num_results,
                    "deep_research": request.use_deep_research,
                    "query_variations": request.deep_research_n_results if request.use_deep_research else 1
                }
                
                response = query_claude_with_system_prompt(
                    query=request.query,
                    context=context,
                    use_thinking=request.use_thinking
                )
                
                return QueryResponse(
                    response=response,
                    refined_query=None,
                    retrieval_stats=retrieval_stats
                )
                
            except Exception as e:
                logger.error(f"Query error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/migrate", response_model=MigrateResponse)
        async def migrate_endpoint(request: MigrateRequest):
            try:
                try:
                    import psycopg
                except ImportError as e:
                    error_msg = f"Failed to import psycopg: {e}"
                    logger.error(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                db_url = os.environ.get('DATABASE_URL')
                if not db_url:
                    raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
                
                batch_name = request.batch_name or "unknown"
                logger.info(f"Executing migration batch: {batch_name}")
                
                try:
                    with psycopg.connect(db_url) as conn:
                        with conn.pipeline():
                            with conn.cursor() as cur:
                                cur.execute(request.sql)
                    
                    rows_affected = request.sql.count("VALUES") if "VALUES" in request.sql else 0
                    return MigrateResponse(success=True, batch=batch_name, rows_affected=rows_affected)
                except psycopg.Error as e:
                    raise HTTPException(status_code=500, detail=f"PostgreSQL error: {str(e)}")
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Migration error: {str(e)}")

        return app
        
    except Exception as e:
        logger.error(f"Failed to create FastAPI app: {e}", exc_info=True)
        # Re-raise so api/index.py can catch it and return JSON error
        raise

# Globals for lazy loading conductor
CONDUCTOR_AVAILABLE = False
CONDUCTOR_IMPORT_ERROR = None
query_chromadb = None
format_context = None
DEFAULT_DB_PATH = None
query_claude_with_system_prompt = None
SYSTEM_PROMPT_SEARCH_AGENT = None

def _import_conductor():
    """Lazy import of conductor modules."""
    global CONDUCTOR_AVAILABLE, query_chromadb, format_context, DEFAULT_DB_PATH
    global query_claude_with_system_prompt, SYSTEM_PROMPT_SEARCH_AGENT, CONDUCTOR_IMPORT_ERROR
    
    if CONDUCTOR_AVAILABLE:
        return True
        
    logger.debug("Attempting to import conductor modules")
    try:
        from conductor.ask import (
            query_chromadb,
            format_context,
            DEFAULT_DB_PATH
        )
        from conductor.prompt_refiner import (
            query_claude_with_system_prompt,
            SYSTEM_PROMPT_SEARCH_AGENT
        )
        CONDUCTOR_AVAILABLE = True
        CONDUCTOR_IMPORT_ERROR = None
        return True
    except Exception as e:
        CONDUCTOR_AVAILABLE = False
        CONDUCTOR_IMPORT_ERROR = f"{type(e).__name__}: {e}"
        logger.error(f"Failed to import conductor modules: {CONDUCTOR_IMPORT_ERROR}", exc_info=True)
        return False

# Initialize app at module level if possible, but wrapped
try:
    app = create_app()
except Exception as e:
    # Capture initialization error for api/index.py to report
    import traceback
    INIT_ERROR = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    app = None

if __name__ == "__main__":
    import uvicorn
    if app:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        print("Failed to initialize app")
