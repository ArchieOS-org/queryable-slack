"""
Vercel serverless function entry point.

Uses Mangum to wrap FastAPI app for Vercel serverless functions.
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
import os
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Import the FastAPI app
from web_api import app

# Import Mangum adapter for Vercel
from mangum import Mangum

# Create handler for Vercel
handler = Mangum(app, lifespan="off")

