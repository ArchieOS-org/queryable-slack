"""
Migrate ChromaDB to Supabase using MCP tools with small batches.

This script reads from ChromaDB and generates small SQL batches (10 records each)
that can be executed via MCP execute_sql.
"""

import sys
from pathlib import Path
import json
import logging

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def read_chromadb_batch(chromadb_path: Path, offset: int, limit: int):
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


def generate_small_batch_sql(records):
    """Generate SQL for a small batch (10 records max)."""
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
    return sql.strip()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate small SQL batches for MCP migration")
    parser.add_argument("--chromadb-path", type=str, 
                       default="/Users/noahdeskin/slack-vectoriezed-data",
                       help="Path to ChromaDB directory")
    parser.add_argument("--batch-size", type=int, default=10,
                       help="Records per SQL batch (smaller = easier to execute)")
    parser.add_argument("--output-dir", type=str, default="/tmp/migration_small",
                       help="Output directory for SQL files")
    
    args = parser.parse_args()
    
    chromadb_path = Path(args.chromadb_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    import chromadb
    client = chromadb.PersistentClient(path=str(chromadb_path))
    collection = client.get_collection(name='conductor_sessions')
    total_count = collection.count()
    
    logger.info(f"Generating small SQL batches for {total_count} records...")
    logger.info(f"Batch size: {args.batch_size} records per file")
    
    batch_num = 0
    for offset in range(0, total_count, args.batch_size):
        batch_num += 1
        logger.info(f"Processing batch {batch_num} (offset {offset})...")
        
        records = read_chromadb_batch(chromadb_path, offset, args.batch_size)
        sql = generate_small_batch_sql(records)
        
        output_file = output_dir / f"batch_{batch_num:04d}.sql"
        output_file.write_text(sql)
        
        logger.info(f"  ✅ Saved {len(records)} records to {output_file} ({len(sql)} chars)")
    
    logger.info(f"\n✅ Generated {batch_num} SQL batch files in {output_dir}")
    logger.info(f"Each file contains {args.batch_size} records and can be executed via MCP")


