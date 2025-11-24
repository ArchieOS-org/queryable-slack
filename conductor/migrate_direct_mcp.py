"""
Migrate ChromaDB to Supabase using MCP tools directly.

This script reads from ChromaDB and inserts data via MCP execute_sql in batches.
Run this from an environment with MCP access (like Cursor).
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


def generate_batch_insert_sql(records: List[Dict[str, Any]]) -> str:
    """Generate a single SQL statement for batch insert."""
    if not records:
        return ""
    
    values = []
    for record in records:
        record_id = record['id'].replace("'", "''")
        metadata_json = json.dumps(record['metadata']).replace("'", "''")
        
        embedding = record['embedding']
        if embedding and len(embedding) == 384:
            embedding_str = '[' + ','.join(str(float(x)) for x in embedding) + ']'
            values.append(f"('{record_id}', '{embedding_str}'::vector, '{metadata_json}'::jsonb)")
        else:
            values.append(f"('{record_id}', NULL::vector, '{metadata_json}'::jsonb)")
    
    sql = f"""
INSERT INTO vecs.conductor_sessions (id, embedding, metadata) 
VALUES {','.join(values)}
ON CONFLICT (id) DO UPDATE SET 
  embedding = COALESCE(EXCLUDED.embedding, vecs.conductor_sessions.embedding),
  metadata = EXCLUDED.metadata;
"""
    return sql


def migrate_via_mcp(chromadb_path: Path, batch_size: int = 100) -> None:
    """
    Migrate data using MCP tools.
    Note: This requires MCP access - call from Cursor or similar.
    """
    import chromadb
    
    client = chromadb.PersistentClient(path=str(chromadb_path))
    collection = client.get_collection(name='conductor_sessions')
    total_count = collection.count()
    
    logger.info(f"Starting migration of {total_count} records...")
    
    migrated = 0
    total_batches = (total_count + batch_size - 1) // batch_size
    
    for offset in range(0, total_count, batch_size):
        batch_num = (offset // batch_size) + 1
        logger.info(f"Processing batch {batch_num}/{total_batches} (offset {offset})...")
        
        # Read batch
        records = read_chromadb_batch(chromadb_path, offset, batch_size)
        
        if not records:
            continue
        
        # Generate SQL
        sql = generate_batch_insert_sql(records)
        
        # Execute via MCP (this would need to be called from MCP context)
        logger.info(f"Batch {batch_num}: Prepared {len(records)} records for insert")
        logger.info(f"SQL length: {len(sql)} characters")
        
        # For now, save SQL to file for manual execution or MCP execution
        sql_file = Path(f"/tmp/migration_batch_{batch_num}.sql")
        sql_file.write_text(sql)
        logger.info(f"SQL saved to {sql_file}")
        
        migrated += len(records)
    
    logger.info(f"✅ Prepared {migrated} records in {total_batches} batches")
    logger.info(f"SQL files saved to /tmp/migration_batch_*.sql")
    logger.info("Execute these SQL files via MCP execute_sql tool")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate ChromaDB to Supabase via MCP")
    parser.add_argument("--chromadb-path", type=str, 
                       default="/Users/noahdeskin/slack-vectoriezed-data",
                       help="Path to ChromaDB directory")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for inserts")
    
    args = parser.parse_args()
    
    migrate_via_mcp(Path(args.chromadb_path), args.batch_size)


