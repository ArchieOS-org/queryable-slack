"""
Migrate ChromaDB data to Supabase using MCP SQL directly.

This bypasses local connection issues by using MCP tools.
"""

import sys
from pathlib import Path
import json
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def read_chromadb_batch(chromadb_path: Path, offset: int, limit: int) -> List[Dict[str, Any]]:
    """Read a batch of records from ChromaDB."""
    import chromadb
    
    client = chromadb.PersistentClient(path=str(chromadb_path))
    collection = client.get_collection(name='conductor_sessions')
    
    batch_data = collection.get(
        limit=limit,
        offset=offset,
        include=['documents', 'metadatas', 'embeddings']
    )
    
    records = []
    ids = batch_data['ids']
    documents = batch_data.get('documents') or []
    metadatas = batch_data.get('metadatas') or []
    
    # Handle embeddings safely
    embeddings_raw = batch_data.get('embeddings')
    embeddings_list = []
    if embeddings_raw is not None:
        try:
            if hasattr(embeddings_raw, 'tolist'):
                embeddings_list = embeddings_raw.tolist()
            elif isinstance(embeddings_raw, (list, tuple)):
                embeddings_list = list(embeddings_raw)
            else:
                embeddings_list = []
        except:
            embeddings_list = []
    
    for i in range(len(ids)):
        record_id = ids[i]
        document = documents[i] if i < len(documents) else ''
        metadata = metadatas[i] if i < len(metadatas) else {}
        embedding = embeddings_list[i] if i < len(embeddings_list) else None
        
        records.append({
            'id': record_id,
            'document': document,
            'metadata': metadata or {},
            'embedding': embedding
        })
    
    return records


def insert_batch_via_mcp(records: List[Dict[str, Any]]) -> None:
    """
    Insert a batch of records using MCP execute_sql.
    Note: This function should be called from a context where MCP tools are available.
    """
    # This will be called via a wrapper that has MCP access
    # For now, we'll generate SQL and save it
    pass


def generate_insert_sql(records: List[Dict[str, Any]]) -> str:
    """Generate SQL INSERT statements for a batch of records."""
    sql_parts = []
    
    for record in records:
        record_id = record['id'].replace("'", "''")  # Escape single quotes
        document = record['document'].replace("'", "''")
        metadata_json = json.dumps(record['metadata']).replace("'", "''")
        
        embedding = record['embedding']
        if embedding and len(embedding) == 384:
            # Format as PostgreSQL vector: '[0.1,0.2,0.3]'
            embedding_str = '[' + ','.join(str(float(x)) for x in embedding) + ']'
            sql = f"""INSERT INTO vecs.conductor_sessions (id, embedding, metadata) 
                     VALUES ('{record_id}', '{embedding_str}'::vector, '{metadata_json}'::jsonb)
                     ON CONFLICT (id) DO UPDATE SET 
                       embedding = EXCLUDED.embedding,
                       metadata = EXCLUDED.metadata;"""
        else:
            # No embedding, insert without it
            sql = f"""INSERT INTO vecs.conductor_sessions (id, metadata) 
                     VALUES ('{record_id}', '{metadata_json}'::jsonb)
                     ON CONFLICT (id) DO UPDATE SET 
                       metadata = EXCLUDED.metadata;"""
        
        sql_parts.append(sql)
    
    return '\n'.join(sql_parts)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate SQL for ChromaDB to Supabase migration")
    parser.add_argument("--chromadb-path", type=str, 
                       default="/Users/noahdeskin/slack-vectoriezed-data",
                       help="Path to ChromaDB directory")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for SQL generation")
    parser.add_argument("--output", type=str,
                       help="Output SQL file (optional)")
    
    args = parser.parse_args()
    
    chromadb_path = Path(args.chromadb_path)
    total_count = 10088  # Known count
    
    logger.info(f"Generating SQL for {total_count} records...")
    
    all_sql = []
    batch_size = args.batch_size
    
    for offset in range(0, total_count, batch_size):
        logger.info(f"Processing batch {offset//batch_size + 1} (offset {offset})...")
        records = read_chromadb_batch(chromadb_path, offset, batch_size)
        batch_sql = generate_insert_sql(records)
        all_sql.append(f"-- Batch {offset//batch_size + 1}\n{batch_sql}")
    
    final_sql = '\n\n'.join(all_sql)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(final_sql)
        logger.info(f"SQL written to {args.output}")
    else:
        print(final_sql)


