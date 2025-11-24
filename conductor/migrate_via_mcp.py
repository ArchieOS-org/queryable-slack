"""
Migrate ChromaDB data to Supabase vecs using MCP tools.

This script reads from local ChromaDB and uses Supabase MCP tools
to insert data directly, bypassing local connection issues.
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

def read_chromadb_data(chromadb_path: Path, batch_size: int = 1000) -> List[Dict[str, Any]]:
    """Read all data from ChromaDB."""
    import chromadb
    
    logger.info(f"Reading from ChromaDB: {chromadb_path}")
    client = chromadb.PersistentClient(path=str(chromadb_path))
    collection = client.get_collection(name='conductor_sessions')
    
    total_count = collection.count()
    logger.info(f"Total records: {total_count}")
    
    all_records = []
    
    # Read in batches to avoid memory issues
    for offset in range(0, total_count, batch_size):
        batch_data = collection.get(
            limit=batch_size,
            offset=offset,
            include=['documents', 'metadatas', 'embeddings']
        )
        
        batch_count = len(batch_data['ids'])
        
        # Safely get embeddings (handle numpy arrays)
        embeddings_raw = batch_data.get('embeddings')
        if embeddings_raw is None:
            embeddings_list = []
        elif isinstance(embeddings_raw, (list, tuple)):
            embeddings_list = list(embeddings_raw)
        else:
            # Numpy array or similar - convert to list
            try:
                embeddings_list = embeddings_raw.tolist() if hasattr(embeddings_raw, 'tolist') else list(embeddings_raw)
            except:
                embeddings_list = []
        
        documents_list = batch_data.get('documents') or []
        metadatas_list = batch_data.get('metadatas') or []
        
        for i in range(batch_count):
            record_id = batch_data['ids'][i]
            document = documents_list[i] if i < len(documents_list) else ''
            metadata = metadatas_list[i] if i < len(metadatas_list) else {}
            
            # Get embedding
            embedding = None
            if len(embeddings_list) > 0 and i < len(embeddings_list):
                emb = embeddings_list[i]
                if emb is not None:
                    # Convert to list if numpy array
                    if hasattr(emb, 'tolist'):
                        embedding = emb.tolist()
                    elif isinstance(emb, (list, tuple)):
                        embedding = list(emb)
            
            all_records.append({
                'id': record_id,
                'document': document,
                'metadata': metadata or {},
                'embedding': embedding
            })
        
        logger.info(f"Processed {min(offset + batch_size, total_count)}/{total_count} records...")
    
    logger.info(f"✅ Prepared {len(all_records)} records")
    if all_records and all_records[0]['embedding']:
        logger.info(f"Embedding dimension: {len(all_records[0]['embedding'])}")
    
    return all_records


def migrate_via_vecs_client(records: List[Dict[str, Any]]) -> None:
    """
    Migrate records using vecs client.
    This will work when run on Vercel where DATABASE_URL is accessible.
    """
    from conductor.vecs_client import upsert_vecs, disconnect
    import os
    
    # Set DATABASE_URL if not set
    if not os.environ.get('DATABASE_URL'):
        logger.error("DATABASE_URL not set. Cannot migrate.")
        return
    
    # Prepare records for vecs: (id, embedding_or_text, metadata)
    vecs_records = []
    for record in records:
        record_id = record['id']
        document = record['document']
        metadata = record['metadata']
        embedding = record['embedding']
        
        # Use embedding if available, otherwise use document text
        if embedding and len(embedding) > 0:
            vecs_records.append((record_id, embedding, metadata))
        else:
            vecs_records.append((record_id, document, metadata))
    
    # Migrate in batches
    batch_size = 1000
    migrated = 0
    total_batches = (len(vecs_records) + batch_size - 1) // batch_size
    
    for i in range(0, len(vecs_records), batch_size):
        batch = vecs_records[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        logger.info(f"Migrating batch {batch_num}/{total_batches} ({len(batch)} records)...")
        try:
            upsert_vecs(batch)
            migrated += len(batch)
            logger.info(f"✅ Batch {batch_num} complete")
        except Exception as e:
            logger.error(f"❌ Error in batch {batch_num}: {e}", exc_info=True)
            # Continue with next batch
            continue
    
    logger.info(f"✅ Migration complete: {migrated}/{len(vecs_records)} records migrated")
    disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate ChromaDB data to Supabase vecs")
    parser.add_argument("--chromadb-path", type=str, 
                       default="/Users/noahdeskin/slack-vectoriezed-data",
                       help="Path to ChromaDB directory")
    parser.add_argument("--method", choices=["vecs", "mcp"], default="vecs",
                       help="Migration method: vecs (uses vecs client) or mcp (uses MCP tools)")
    
    args = parser.parse_args()
    
    # Read ChromaDB data
    records = read_chromadb_data(Path(args.chromadb_path))
    
    if args.method == "vecs":
        logger.info("Using vecs client method (requires DATABASE_URL)")
        migrate_via_vecs_client(records)
    else:
        logger.info("MCP method not yet implemented. Use --method vecs")
        logger.info("Note: vecs method requires DATABASE_URL to be set and accessible")

