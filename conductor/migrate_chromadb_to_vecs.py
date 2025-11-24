"""
Migrate data from ChromaDB to Supabase vecs.

This script reads all data from ChromaDB and migrates it to Supabase vecs.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def migrate_chromadb_to_vecs(chromadb_path: Path, batch_size: int = 1000):
    """
    Migrate all data from ChromaDB to Supabase vecs.
    
    Args:
        chromadb_path: Path to ChromaDB directory
        batch_size: Number of records to migrate per batch
    """
    # Check DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set. Set it to your Supabase connection string.")
        print("\nExample:")
        print("export DATABASE_URL='postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres'")
        return False
    
    # Check ChromaDB exists
    if not chromadb_path.exists():
        print(f"❌ ChromaDB path does not exist: {chromadb_path}")
        return False
    
    try:
        import chromadb
        from conductor.vecs_client import upsert_vecs
        
        print("=" * 60)
        print("ChromaDB to Supabase Vecs Migration")
        print("=" * 60)
        print()
        
        # Connect to ChromaDB
        print(f"📂 Reading from ChromaDB: {chromadb_path}")
        chroma_client = chromadb.PersistentClient(path=str(chromadb_path))
        
        try:
            collection = chroma_client.get_collection("conductor_sessions")
        except Exception as e:
            print(f"❌ Could not access ChromaDB collection: {e}")
            return False
        
        # Get total count
        total_count = collection.count()
        print(f"📊 Found {total_count} records in ChromaDB")
        
        if total_count == 0:
            print("⚠️  No data to migrate")
            return False
        
        # Get all records in batches
        print(f"\n🔄 Migrating {total_count} records to Supabase vecs...")
        print(f"   Batch size: {batch_size}")
        print()
        
        migrated = 0
        batch_num = 0
        
        # ChromaDB get() has a limit, so we'll use query with a dummy query to get all
        # Or we can use get() with limit and offset
        offset = 0
        limit = min(batch_size, 10000)  # ChromaDB get() max is around 10k
        
        while offset < total_count:
            batch_num += 1
            current_batch_size = min(limit, total_count - offset)
            
            print(f"   Batch {batch_num}: Records {offset+1} to {offset+current_batch_size}...", end=" ", flush=True)
            
            try:
                # Get batch from ChromaDB
                batch_data = collection.get(
                    limit=current_batch_size,
                    offset=offset,
                    include=["documents", "metadatas"]
                )
                
                if not batch_data or not batch_data.get("ids"):
                    print("No more records")
                    break
                
                # Convert to vecs format
                records = []
                for i, doc_id in enumerate(batch_data["ids"]):
                    document = batch_data["documents"][i] if batch_data.get("documents") else ""
                    metadata = batch_data["metadatas"][i] if batch_data.get("metadatas") else {}
                    
                    # Ensure document is stored in metadata for vecs retrieval
                    metadata_with_doc = {**metadata, "document": document}
                    
                    records.append((doc_id, document, metadata_with_doc))
                
                # Upsert to vecs
                upsert_vecs(records)
                
                migrated += len(records)
                print(f"✅ Migrated {len(records)} records")
                
                offset += current_batch_size
                
            except Exception as e:
                print(f"❌ Error in batch {batch_num}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print()
        print("=" * 60)
        print("Migration Complete")
        print("=" * 60)
        print(f"✅ Migrated {migrated} out of {total_count} records")
        
        if migrated == total_count:
            print("✅ All records migrated successfully!")
            return True
        else:
            print(f"⚠️  Only {migrated}/{total_count} records migrated")
            return False
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install chromadb vecs")
        return False
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate ChromaDB data to Supabase vecs")
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
        help="Number of records per batch"
    )
    
    args = parser.parse_args()
    
    chromadb_path = Path(args.chromadb_path)
    success = migrate_chromadb_to_vecs(chromadb_path, args.batch_size)
    
    sys.exit(0 if success else 1)


