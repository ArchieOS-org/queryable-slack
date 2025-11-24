"""
Vercel serverless function entry point.

Uses Mangum to wrap FastAPI app for Vercel serverless functions.
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
import os
import sys
import logging

os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Import the FastAPI app
    from web_api import app
    
    # Import Mangum adapter for Vercel
    from mangum import Mangum
    
    # Create handler for Vercel
    handler = Mangum(app, lifespan="off")
    
    logger.info("FastAPI app and Mangum handler initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize FastAPI app: {type(e).__name__}: {str(e)}", exc_info=True)
    
    # Create a minimal error handler
    from mangum import Mangum
    from fastapi import FastAPI
    
    error_app = FastAPI()
    
    @error_app.get("/{path:path}")
    @error_app.post("/{path:path}")
    async def error_handler(path: str):
        return {
            "error": "Failed to initialize application",
            "detail": str(e),
            "type": type(e).__name__
        }
    
    handler = Mangum(error_app, lifespan="off")

