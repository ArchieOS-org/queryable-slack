"""
Execute SQL batches via Supabase MCP tools.
This script reads SQL files and provides instructions for executing via MCP.
Since MCP tools can't be called programmatically in a loop, this script
reads batches and outputs them for manual execution or provides a helper.
"""

import os
import sys
from pathlib import Path
import logging
import glob

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def read_sql_batch(sql_file: Path) -> str:
    """Read SQL content from a batch file."""
    with open(sql_file, 'r') as f:
        return f.read()


def get_batch_info(sql_dir: Path) -> dict:
    """Get information about batch files."""
    sql_files = sorted(glob.glob(str(sql_dir / "batch_*.sql")))
    
    total_size = 0
    for sql_file in sql_files:
        total_size += Path(sql_file).stat().st_size
    
    return {
        "count": len(sql_files),
        "total_size_mb": total_size / (1024 * 1024),
        "avg_size_kb": (total_size / len(sql_files)) / 1024 if sql_files else 0,
        "files": [Path(f) for f in sql_files]
    }


def main():
    """Main function to prepare batches for MCP execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Prepare SQL batches for Supabase MCP execution"
    )
    parser.add_argument(
        "--sql-dir",
        type=str,
        default="/tmp/migration_small",
        help="Directory containing SQL batch files"
    )
    parser.add_argument(
        "--execute-first",
        type=int,
        help="Execute first N batches via MCP (for testing)"
    )
    
    args = parser.parse_args()
    
    sql_dir = Path(args.sql_dir)
    info = get_batch_info(sql_dir)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 Batch Information:")
    logger.info(f"   Total batches: {info['count']}")
    logger.info(f"   Total size: {info['total_size_mb']:.2f} MB")
    logger.info(f"   Avg size per batch: {info['avg_size_kb']:.2f} KB")
    logger.info(f"{'='*60}\n")
    
    if args.execute_first:
        logger.info(f"Executing first {args.execute_first} batches...")
        logger.info("Note: This requires manual MCP tool calls for each batch.")
        logger.info("Each batch file can be executed via: mcp_supabase_execute_sql\n")
        
        for i, sql_file in enumerate(info['files'][:args.execute_first], 1):
            logger.info(f"Batch {i}/{args.execute_first}: {sql_file.name}")
            sql_content = read_sql_batch(sql_file)
            logger.info(f"  Size: {len(sql_content)} chars")
            logger.info(f"  Ready to execute via MCP\n")


if __name__ == "__main__":
    main()

