"""
Execute migration batches via Vercel API endpoint.
This script reads SQL batch files and sends them to the Vercel migration endpoint.
"""

import os
import sys
import json
import glob
import requests
from pathlib import Path
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def migrate_batch_via_vercel(sql_file_path: Path, vercel_url: str, api_key: Optional[str] = None) -> bool:
    """Execute a single SQL batch file via Vercel API."""
    try:
        logger.info(f"Reading SQL file: {sql_file_path.name}")
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
        
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        payload = {
            'sql': sql_content,
            'batch_name': sql_file_path.name
        }
        
        logger.info(f"Sending batch {sql_file_path.name} to Vercel...")
        response = requests.post(
            f"{vercel_url}/api/migrate",  # Vercel routes /api/* to FastAPI, FastAPI sees /migrate
            json=payload,
            headers=headers,
            timeout=300  # 5 minute timeout for large batches
        )
        
        if response.status_code == 200:
            result = response.json()
            rows_affected = result.get('rows_affected', 0)
            logger.info(f"✅ Successfully executed {sql_file_path.name} ({rows_affected} rows affected)")
            return True
        else:
            error_msg = response.text
            logger.error(f"❌ Error executing {sql_file_path.name}: {response.status_code} - {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error processing {sql_file_path.name}: {e}", exc_info=True)
        return False


def migrate_all_batches_via_vercel(
    sql_dir: Path,
    vercel_url: str,
    api_key: Optional[str] = None,
    start_from: int = 0,
    max_batches: Optional[int] = None
) -> None:
    """Execute all SQL batch files via Vercel API."""
    sql_files = sorted(glob.glob(str(sql_dir / "batch_*.sql")))
    
    if not sql_files:
        logger.warning(f"No batch files found in {sql_dir}")
        return
    
    total_files = len(sql_files)
    logger.info(f"Found {total_files} batch files")
    
    # Apply start_from and max_batches filters
    if start_from > 0:
        sql_files = sql_files[start_from:]
        logger.info(f"Starting from batch {start_from}")
    
    if max_batches:
        sql_files = sql_files[:max_batches]
        logger.info(f"Processing up to {max_batches} batches")
    
    successful = 0
    failed = 0
    
    for i, sql_file in enumerate(sql_files, start=start_from + 1):
        sql_path = Path(sql_file)
        logger.info(f"\n[{i}/{total_files}] Processing {sql_path.name}...")
        
        if migrate_batch_via_vercel(sql_path, vercel_url, api_key):
            successful += 1
        else:
            failed += 1
            # Continue with next batch even if one fails
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Migration Summary:")
    logger.info(f"  Total batches: {len(sql_files)}")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Execute SQL batch files via Vercel migration endpoint"
    )
    parser.add_argument(
        "--sql-dir",
        type=str,
        default="/tmp/migration_small",
        help="Directory containing SQL batch files"
    )
    parser.add_argument(
        "--vercel-url",
        type=str,
        help="Vercel deployment URL (e.g., https://queryable-slack.vercel.app)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Optional API key for authentication"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start from batch number (0-indexed)"
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        help="Maximum number of batches to process"
    )
    
    args = parser.parse_args()
    
    vercel_url = args.vercel_url or os.environ.get('VERCEL_URL') or 'https://queryable-slack.vercel.app'
    
    logger.info(f"Using Vercel URL: {vercel_url}")
    logger.info(f"SQL directory: {args.sql_dir}")
    
    migrate_all_batches_via_vercel(
        Path(args.sql_dir),
        vercel_url,
        args.api_key,
        args.start_from,
        args.max_batches
    )

