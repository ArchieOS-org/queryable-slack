"""
Split SQL batches into smaller chunks (5 records) for MCP execution.
Each batch file is currently ~83KB with 10 records. Split into 5-record chunks (~40KB).
"""

import os
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def split_batch_file(input_file: Path, output_dir: Path, records_per_chunk: int = 5):
    """Split a single batch file into smaller chunks."""
    logger.info(f"Splitting {input_file.name} into chunks of {records_per_chunk} records...")
    
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Extract the INSERT statement and VALUES
    match = re.match(r'(INSERT INTO vecs\.conductor_sessions.*?VALUES\s*\()(.*?)(ON CONFLICT.*)', content, re.DOTALL)
    if not match:
        logger.error(f"Could not parse {input_file.name}")
        return []
    
    header = match.group(1)
    values_section = match.group(2)
    footer = match.group(3)
    
    # Split VALUES by ),( pattern (end of one record, start of next)
    # But we need to be careful with nested parentheses in JSONB
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
        
        if in_string:
            current_record += char
            continue
        
        if char == '(':
            paren_depth += 1
            current_record += char
        elif char == ')':
            paren_depth -= 1
            current_record += char
            if paren_depth == 0:
                # End of a record
                records.append(current_record.strip().rstrip(','))
                current_record = ""
        else:
            current_record += char
    
    # Create chunks
    chunk_files = []
    base_name = input_file.stem
    for i in range(0, len(records), records_per_chunk):
        chunk_num = i // records_per_chunk + 1
        chunk_records = records[i:i + records_per_chunk]
        
        chunk_content = header + ',\n'.join(chunk_records) + '\n' + footer
        
        chunk_file = output_dir / f"{base_name}_chunk_{chunk_num:04d}.sql"
        with open(chunk_file, 'w') as f:
            f.write(chunk_content)
        
        chunk_files.append(chunk_file)
        logger.info(f"Created {chunk_file.name} with {len(chunk_records)} records")
    
    return chunk_files


def main():
    """Split all batch files into smaller chunks."""
    input_dir = Path("/tmp/migration_small")
    output_dir = Path("/tmp/migration_mcp_chunks")
    output_dir.mkdir(exist_ok=True)
    
    batch_files = sorted(input_dir.glob("batch_*.sql"))
    logger.info(f"Found {len(batch_files)} batch files to split")
    
    all_chunk_files = []
    for batch_file in batch_files:
        chunk_files = split_batch_file(batch_file, output_dir, records_per_chunk=5)
        all_chunk_files.extend(chunk_files)
    
    logger.info(f"✅ Created {len(all_chunk_files)} chunk files in {output_dir}")
    logger.info(f"Ready to execute via MCP: {len(all_chunk_files)} chunks")


if __name__ == "__main__":
    main()

