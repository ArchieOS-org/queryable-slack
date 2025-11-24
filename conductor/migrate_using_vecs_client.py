"""
Migrate ChromaDB to Supabase using vecs client directly.

This script uses vecs.upsert() which handles batching efficiently.
Best practice: Use vecs client methods rather than raw SQL.
"""

import sys
from pathlib import Path
import logging
import os

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


def migrate_using_vecs(chromadb_path: Path, batch_size: int = 1000):
    """
    Migrate using vecs client upsert() method.
    This is the recommended approach per Context7 docs.
    """
    import chromadb
    import vecs
    
    # Check DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    logger.info("Connecting to Supabase via vecs client...")
    vx = vecs.create_client(db_url)
    
    logger.info("Getting or creating collection 'conductor_sessions' (dimension=384)...")
    collection = vx.get_or_create_collection(
        name="conductor_sessions",
        dimension=384
    )
    
    # Read ChromaDB
    logger.info(f"Reading from ChromaDB: {chromadb_path}")
    chroma_client = chromadb.PersistentClient(path=str(chromadb_path))
    chroma_collection = chroma_client.get_collection(name='conductor_sessions')
    total_count = chroma_collection.count()
    
    logger.info(f"Total records to migrate: {total_count}")
    logger.info(f"Batch size: {batch_size} records")
    
    migrated = 0
    total_batches = (total_count + batch_size - 1) // batch_size
    
    for offset in range(0, total_count, batch_size):
        batch_num = (offset // batch_size) + 1
        
        logger.info(f"Processing batch {batch_num}/{total_batches} (offset {offset})...")
        
        # Read batch from ChromaDB
        records_data = read_chromadb_batch(chromadb_path, offset, batch_size)
        
        # Prepare records for vecs: (id, embedding, metadata)
        vecs_records = []
        for record in records_data:
            record_id = record['id']
            metadata = record['metadata']
            embedding = record['embedding']
            
            # Use embedding if available (384 dimensions)
            if embedding and len(embedding) == 384:
                vecs_records.append((record_id, embedding, metadata))
            else:
                # If no embedding, skip or use document text
                # For now, skip records without embeddings
                logger.warning(f"Skipping record {record_id[:20]}... (no valid embedding)")
                continue
        
        if not vecs_records:
            logger.warning(f"No valid records in batch {batch_num}")
            continue
        
        # Upsert using vecs client (handles batching internally)
        try:
            logger.info(f"Upserting {len(vecs_records)} records via vecs...")
            collection.upsert(records=vecs_records)
            migrated += len(vecs_records)
            logger.info(f"✅ Batch {batch_num} complete: {len(vecs_records)} records migrated")
        except Exception as e:
            logger.error(f"❌ Error in batch {batch_num}: {e}", exc_info=True)
            # Continue with next batch
            continue
    
    logger.info(f"\n✅ Migration complete!")
    logger.info(f"Migrated: {migrated}/{total_count} records")
    
    # Create index after migration (best practice per Context7)
    if migrated > 0:
        logger.info("Creating index for efficient querying...")
        try:
            collection.create_index()
            logger.info("✅ Index created successfully")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    vx.disconnect()
    logger.info("✅ Disconnected from vecs")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate ChromaDB to Supabase using vecs client (recommended method)"
    )
    parser.add_argument(
        "--chromadb-path",
        type=str,
        default="/Users/noahdeskin/slack-vectoriezed-data",
        help="Path to ChromaDB directory"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for migration (vecs handles batching efficiently)"
    )
    
    args = parser.parse_args()
    
    migrate_using_vecs(Path(args.chromadb_path), args.batch_size)


