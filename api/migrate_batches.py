"""
Vercel serverless function to execute SQL migration batches.
This can be called via HTTP POST to execute batches remotely.
"""

import os
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handler(request):
    """Vercel serverless function handler."""
    import psycopg
    
    try:
        # Get SQL content from request body
        body = request.get_json()
        sql_content = body.get('sql')
        batch_name = body.get('batch_name', 'unknown')
        
        if not sql_content:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'SQL content required'})
            }
        
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'DATABASE_URL not configured'})
            }
        
        logger.info(f"Executing batch: {batch_name}")
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        cur.execute(sql_content)
        conn.commit()
        
        cur.close()
        conn.close()
        
        logger.info(f"✅ Successfully executed {batch_name}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'batch': batch_name})
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


