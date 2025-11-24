"""
Check if data exists in Supabase vecs collection.

Run this script to verify if data has been ingested into Supabase.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_vecs_data():
    """Check if data exists in vecs collection."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set. Set it to your Supabase connection string.")
        print("\nExample:")
        print("export DATABASE_URL='postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres'")
        return False
    
    try:
        import vecs
        from conductor.vecs_client import COLLECTION_NAME
        
        print(f"🔍 Checking vecs collection '{COLLECTION_NAME}'...")
        print(f"📡 Connecting to Supabase...")
        
        vx = vecs.create_client(db_url)
        collection = vx.get_or_create_collection(name=COLLECTION_NAME, dimension=384)
        
        # Get collection info
        try:
            # Try to get collection length
            collection_size = len(collection)
            print(f"✅ Collection '{COLLECTION_NAME}' exists")
            print(f"📊 Collection size: {collection_size} records")
            
            if collection_size > 0:
                print("\n✅ Data is present in Supabase!")
                print(f"   Found {collection_size} records")
                
                # Try to query a sample
                try:
                    sample_results = collection.query(
                        data="test",
                        limit=1
                    )
                    if sample_results:
                        print(f"   Sample query successful: {len(sample_results)} result(s)")
                except Exception as e:
                    print(f"   ⚠️  Sample query failed: {e}")
                
                return True
            else:
                print("\n⚠️  Collection exists but is empty")
                print("   You need to ingest data into Supabase")
                return False
                
        except Exception as e:
            print(f"⚠️  Could not get collection size: {e}")
            print("   Collection may not exist yet or may be empty")
            return False
        
    except ImportError:
        print("❌ vecs is not installed. Install with:")
        print("   pip install vecs")
        return False
    except Exception as e:
        print(f"❌ Error checking vecs data: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            vx.disconnect()
        except:
            pass


def check_chromadb_data():
    """Check if data exists in local ChromaDB."""
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    from conductor.config import DEFAULT_DB_PATH
    
    db_path = DEFAULT_DB_PATH
    if not db_path.exists():
        print(f"❌ ChromaDB path does not exist: {db_path}")
        return False
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_path))
        collection = client.get_collection(name="conductor_sessions")
        
        count = collection.count()
        print(f"✅ ChromaDB collection exists")
        print(f"📊 ChromaDB size: {count} records")
        
        if count > 0:
            print("\n✅ Data exists in local ChromaDB!")
            print(f"   Found {count} records")
            print("\n💡 To migrate to Supabase, run:")
            print("   python -m conductor.migrate_chromadb_to_vecs")
            return True
        else:
            print("\n⚠️  ChromaDB collection is empty")
            return False
            
    except Exception as e:
        print(f"❌ Error checking ChromaDB: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Data Status Check")
    print("=" * 60)
    print()
    
    # Check Supabase
    print("1. Checking Supabase vecs...")
    vecs_has_data = check_vecs_data()
    print()
    
    # Check ChromaDB
    print("2. Checking local ChromaDB...")
    chromadb_has_data = check_chromadb_data()
    print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    if vecs_has_data:
        print("✅ Supabase has data - Ready for Vercel deployment!")
    elif chromadb_has_data:
        print("⚠️  Data is in ChromaDB but not in Supabase")
        print("   You need to migrate data to Supabase")
    else:
        print("❌ No data found in either location")
        print("   You need to ingest data first")

