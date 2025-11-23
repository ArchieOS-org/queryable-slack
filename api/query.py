"""
Vercel serverless function for querying the vector database.

This is a wrapper around web_api.py that works with Vercel's serverless functions.
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
import os
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

import json
from pathlib import Path
from typing import Optional, Dict
from fastapi import HTTPException
from fastapi.responses import JSONResponse

# Import chatbot functionality
from conductor.ask import (
    query_chromadb,
    format_context,
    DEFAULT_DB_PATH
)
from conductor.prompt_refiner import (
    query_claude_with_system_prompt,
)

# For Vercel, we'll use Supabase for database storage
# The database path will come from environment variables
def get_db_path() -> Path:
    """Get database path from environment or use default."""
    db_path_env = os.environ.get('CHROMADB_PATH')
    if db_path_env:
        return Path(db_path_env)
    # For Supabase, we might need to use a different approach
    # For now, use the default
    return DEFAULT_DB_PATH


def handler(request):
    """
    Vercel serverless function handler.
    
    Handles POST requests to query the vector database.
    """
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
        }
    
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': 'Method not allowed'}),
        }
    
    try:
        # Parse request body
        body = json.loads(request.body) if hasattr(request, 'body') else {}
        
        query = body.get('query', '')
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Query is required'}),
            }
        
        # Get database path
        db_path = get_db_path()
        
        if not db_path.exists():
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': f'Database not found: {db_path}'}),
            }
        
        # Query parameters
        use_deep_research = body.get('use_deep_research', True)
        deep_research_n_results = body.get('deep_research_n_results', 50)
        max_final_results = body.get('max_final_results', 40)
        use_thinking = body.get('use_thinking', False)
        
        # Step 1: Query ChromaDB
        results = query_chromadb(
            query,
            db_path=db_path,
            use_reranking=True,
            use_cache=not use_deep_research,
            use_hybrid=use_deep_research,
            use_deep_research=use_deep_research,
            deep_research_n_results=deep_research_n_results,
            max_final_results=max_final_results
        )
        
        # Step 2: Format context
        context = format_context(results)
        
        # Step 3: Query Claude
        response = query_claude_with_system_prompt(
            query=query,
            context=context,
            use_thinking=use_thinking
        )
        
        # Calculate retrieval stats
        num_results = len(results.get("documents", [[]])[0]) if results.get("documents") else 0
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'response': response,
                'retrieval_stats': {
                    'num_results': num_results,
                    'deep_research': use_deep_research,
                    'query_variations': deep_research_n_results if use_deep_research else 1
                }
            }),
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'error': str(e),
                'details': error_details if os.environ.get('DEBUG') else None
            }),
        }

