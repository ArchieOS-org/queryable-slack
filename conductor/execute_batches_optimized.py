"""
Execute SQL batch files using psycopg with pipeline mode for optimal performance.
Based on Context7 best practices for batch SQL execution.
"""

import os
import sys
from pathlib import Path
import logging
import glob
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def execute_batches_with_pipeline(sql_files: List[Path], db_url: str, batch_size: int = 10) -> tuple[int, int]:
    """
    Execute SQL batches using psycopg pipeline mode for optimal performance.
    
    Args:
        sql_files: List of SQL file paths to execute
        db_url: Database connection URL
        batch_size: Number of batches to execute in each pipeline transaction
        
    Returns:
        Tuple of (successful_count, failed_count)
    """
    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed. Install with: pip install 'psycopg[binary]'")
        return 0, len(sql_files)
    
    successful = 0
    failed = 0
    
    try:
        logger.info(f"Connecting to database...")
        with psycopg.connect(db_url) as conn:
            # Process batches in groups using pipeline mode
            for i in range(0, len(sql_files), batch_size):
                batch_group = sql_files[i:i + batch_size]
                logger.info(f"\n📦 Processing batch group {i//batch_size + 1} ({len(batch_group)} files)...")
                
                try:
                    # Use pipeline mode for batch execution
                    with conn.pipeline():
                        for sql_file in batch_group:
                            try:
                                logger.info(f"  Executing {sql_file.name}...")
                                with open(sql_file, 'r') as f:
                                    sql_content = f.read()
                                
                                conn.execute(sql_content)
                                successful += 1
                                
                            except Exception as e:
                                logger.error(f"  ❌ Error in {sql_file.name}: {e}")
                                failed += 1
                                # Continue with next file in pipeline
                        
                        # Commit the entire pipeline batch
                        conn.commit()
                        logger.info(f"  ✅ Committed batch group {i//batch_size + 1}")
                        
                except Exception as e:
                    logger.error(f"  ❌ Pipeline error for batch group {i//batch_size + 1}: {e}")
                    # Rollback and mark all in group as failed
                    conn.rollback()
                    failed += len(batch_group)
                    successful -= (len(batch_group) - failed)
                    
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}", exc_info=True)
        return successful, failed + (len(sql_files) - successful)
    
    return successful, failed


def main():
    """Execute all SQL batch files."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Execute SQL batch files with optimized pipeline mode"
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
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of batches to execute per pipeline transaction (default: 10)"
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        help="Maximum number of batches to execute (for testing)"
    )
    
    args = parser.parse_args()
    
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable or --db-url is required")
        sys.exit(1)
    
    sql_dir = Path(args.sql_dir)
    sql_files = sorted(glob.glob(str(sql_dir / "batch_*.sql")))
    
    if not sql_files:
        logger.warning(f"No batch files found in {sql_dir}")
        return
    
    if args.max_batches:
        sql_files = sql_files[:args.max_batches]
        logger.info(f"Limiting to first {args.max_batches} batches")
    
    logger.info(f"Found {len(sql_files)} batch files to execute")
    logger.info(f"Using pipeline mode with batch size: {args.batch_size}")
    
    successful, failed = execute_batches_with_pipeline(
        [Path(f) for f in sql_files],
        db_url,
        batch_size=args.batch_size
    )
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ Migration Summary:")
    logger.info(f"   Total batches: {len(sql_files)}")
    logger.info(f"   Successful: {successful}")
    logger.info(f"   Failed: {failed}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()

