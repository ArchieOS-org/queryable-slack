"""
Vercel serverless function for bulk batch migration.
Executes multiple batches using psycopg pipeline mode for optimal performance.
Based on Context7 best practices.
"""

import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress tokenizers parallelism warning
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')


def handler(request):
    """Vercel serverless function handler for bulk batch migration."""
    try:
        import psycopg
        
        if request.method != 'POST':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed. Use POST.'})
            }
        
        body = request.get_json()
        if not body:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Request body required'})
            }
        
        sql_batches = body.get('batches', [])
        if not sql_batches:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'batches array required'})
            }
        
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'DATABASE_URL not configured'})
            }
        
        logger.info(f"Executing {len(sql_batches)} batches via pipeline mode...")
        
        successful = 0
        failed = 0
        errors = []
        
        try:
            with psycopg.connect(db_url) as conn:
                # Use pipeline mode for batch execution (Context7 best practice)
                with conn.pipeline():
                    for i, sql_content in enumerate(sql_batches):
                        try:
                            conn.execute(sql_content)
                            successful += 1
                        except Exception as e:
                            failed += 1
                            errors.append(f"Batch {i+1}: {str(e)}")
                            logger.error(f"Error in batch {i+1}: {e}")
                    
                    # Commit all successful batches
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': f'Pipeline execution failed: {str(e)}',
                    'successful': successful,
                    'failed': failed + (len(sql_batches) - successful)
                })
            }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'total': len(sql_batches),
                'successful': successful,
                'failed': failed,
                'errors': errors[:10]  # Limit error details
            })
        }
        
    except ImportError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'psycopg not available: {str(e)}'})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

