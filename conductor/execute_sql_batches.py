"""
Execute SQL batch files using Supabase connection.
This script reads SQL files and executes them via psycopg.
Can be run locally or on Vercel where DATABASE_URL is accessible.
"""

import os
import sys
from pathlib import Path
import logging
import glob

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def execute_sql_file(sql_file_path: Path, db_url: str) -> bool:
    """Execute a single SQL file."""
    try:
        import psycopg
        
        logger.info(f"Reading SQL file: {sql_file_path}")
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
        
        logger.info(f"Connecting to database...")
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        logger.info(f"Executing SQL from {sql_file_path.name}...")
        cur.execute(sql_content)
        conn.commit()
        
        logger.info(f"✅ Successfully executed {sql_file_path.name}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error executing {sql_file_path.name}: {e}", exc_info=True)
        return False


def execute_all_batches(sql_dir: Path, db_url: str) -> None:
    """Execute all SQL batch files in a directory."""
    sql_files = sorted(glob.glob(str(sql_dir / "batch_*.sql")))
    
    if not sql_files:
        logger.warning(f"No batch files found in {sql_dir}")
        return
    
    logger.info(f"Found {len(sql_files)} batch files")
    
    successful = 0
    failed = 0
    
    for sql_file in sql_files:
        sql_path = Path(sql_file)
        if execute_sql_file(sql_path, db_url):
            successful += 1
        else:
            failed += 1
    
    logger.info(f"\n✅ Migration Summary:")
    logger.info(f"   Successful: {successful}/{len(sql_files)}")
    logger.info(f"   Failed: {failed}/{len(sql_files)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Execute SQL batch files for Supabase migration"
    )
    parser.add_argument(
        "--sql-dir",
        type=str,
        default="/tmp/migration_small",
        help="Directory containing SQL batch files"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Database URL (or set DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable or --db-url is required")
        sys.exit(1)
    
    execute_all_batches(Path(args.sql_dir), db_url)


