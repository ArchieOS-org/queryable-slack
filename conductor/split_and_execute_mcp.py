"""
Split large SQL batches into smaller chunks and prepare for MCP execution.
Based on Context7 best practices for batch SQL execution.
"""

import os
import re
from pathlib import Path
import logging
import glob

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def split_batch_into_chunks(sql_content: str, records_per_chunk: int = 5) -> list[str]:
    """
    Split a SQL INSERT statement into smaller chunks.
    
    Args:
        sql_content: Full SQL INSERT statement
        records_per_chunk: Number of records per chunk
        
    Returns:
        List of SQL statements, each with records_per_chunk records
    """
    # Extract the INSERT statement header and footer
    header_match = re.match(r'(INSERT INTO vecs\.conductor_sessions.*?VALUES\s*\()', sql_content, re.DOTALL)
    footer_match = re.search(r'(ON CONFLICT.*)', sql_content, re.DOTALL)
    
    if not header_match or not footer_match:
        logger.warning("Could not parse SQL structure, returning original")
        return [sql_content]
    
    header = header_match.group(1)
    footer = footer_match.group(1)
    
    # Extract all VALUES tuples
    values_section = sql_content[len(header):-len(footer)]
    
    # Split by ),( pattern (end of one record, start of next)
    # But we need to be careful with nested parentheses in JSONB
    # Use a simpler approach: split by '),(' pattern
    records = []
    current_record = ""
    paren_depth = 0
    in_string = False
    escape_next = False
    
    for char in values_section:
        if escape_next:
            current_record += char
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            current_record += char
            continue
            
        if char == "'" and not escape_next:
            in_string = not in_string
            current_record += char
            continue
            
        if not in_string:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    # End of a record
                    current_record += char
                    records.append(current_record.strip())
                    current_record = ""
                    continue
        
        current_record += char
    
    # Group records into chunks
    chunks = []
    for i in range(0, len(records), records_per_chunk):
        chunk_records = records[i:i + records_per_chunk]
        chunk_sql = header + ','.join(chunk_records) + footer
        chunks.append(chunk_sql)
    
    return chunks


def process_batch_files(input_dir: Path, output_dir: Path, records_per_chunk: int = 5):
    """Process all batch files and split them into smaller chunks."""
    sql_files = sorted(glob.glob(str(input_dir / "batch_*.sql")))
    
    if not sql_files:
        logger.warning(f"No batch files found in {input_dir}")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_chunks = 0
    for sql_file in sql_files:
        sql_path = Path(sql_file)
        logger.info(f"Processing {sql_path.name}...")
        
        with open(sql_path, 'r') as f:
            sql_content = f.read()
        
        chunks = split_batch_into_chunks(sql_content, records_per_chunk)
        
        for i, chunk in enumerate(chunks):
            chunk_file = output_dir / f"{sql_path.stem}_chunk_{i:04d}.sql"
            with open(chunk_file, 'w') as f:
                f.write(chunk)
            total_chunks += 1
    
    logger.info(f"\n✅ Created {total_chunks} chunk files from {len(sql_files)} batch files")
    logger.info(f"   Output directory: {output_dir}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Split SQL batches into smaller chunks for MCP execution"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="/tmp/migration_small",
        help="Directory containing input batch files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/tmp/migration_mcp_chunks",
        help="Directory for output chunk files"
    )
    parser.add_argument(
        "--records-per-chunk",
        type=int,
        default=5,
        help="Number of records per chunk (default: 5)"
    )
    
    args = parser.parse_args()
    
    process_batch_files(
        Path(args.input_dir),
        Path(args.output_dir),
        records_per_chunk=args.records_per_chunk
    )


if __name__ == "__main__":
    main()

