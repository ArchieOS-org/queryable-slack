"""
Standalone migration endpoint for Vercel.
Does not depend on conductor modules to avoid import issues.
"""

import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress tokenizers parallelism warning
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')


def handler(request):
    """
    Vercel serverless function handler for migration.
    Standalone version that doesn't import conductor modules.
    """
    try:
        import psycopg
    except ImportError as e:
        logger.error(f"Failed to import psycopg: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': f'psycopg not available: {str(e)}'
            })
        }
    
    try:
        # Parse request
        if hasattr(request, 'get_json'):
            body = request.get_json()
        else:
            import json as json_lib
            body = json_lib.loads(request.body) if hasattr(request, 'body') else {}
        
        sql_content = body.get('sql', '')
        batch_name = body.get('batch_name', 'unknown')
        
        if not sql_content:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'success': False,
                    'error': 'SQL content required'
                })
            }
        
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'success': False,
                    'error': 'DATABASE_URL not configured'
                })
            }
        
        logger.info(f"Executing migration batch: {batch_name} ({len(sql_content)} chars)")
        
        # Execute SQL using psycopg pipeline mode (Context7 best practice)
        with psycopg.connect(db_url) as conn:
            with conn.pipeline():
                conn.execute(sql_content)
                # Pipeline automatically commits on success
        
        # Estimate rows affected
        rows_affected = sql_content.count("VALUES") if "VALUES" in sql_content else 0
        
        logger.info(f"✅ Successfully executed {batch_name} (estimated {rows_affected} rows)")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'batch': batch_name,
                'rows_affected': rows_affected
            })
        }
        
    except psycopg.Error as e:
        error_msg = f"PostgreSQL error: {type(e).__name__}: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': error_msg
            })
        }
    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': error_msg
            })
        }

