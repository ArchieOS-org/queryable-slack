# Migration to Supabase pgvector (vecs)

## ✅ Completed

1. ✅ Created `conductor/vecs_client.py` - Supabase vecs client wrapper
2. ✅ Updated `conductor/config.py` - Detects `DATABASE_URL` and uses vecs automatically
3. ✅ Updated `conductor/ask.py` - Uses vecs when `DATABASE_URL` is set
4. ✅ Updated `conductor/ingest.py` - Stores sessions in vecs when `DATABASE_URL` is set
5. ✅ Updated `web_api.py` - Handles vecs configuration
6. ✅ Updated `requirements.txt` - Added `vecs>=0.4.0`

## How It Works

The system automatically detects if `DATABASE_URL` is set:
- **If `DATABASE_URL` is set**: Uses Supabase vecs (pgvector)
- **If not set**: Uses ChromaDB (local or HTTP client)

This allows seamless switching between local development (ChromaDB) and production (Supabase).

## Configuration

### Vercel Environment Variables

The following environment variables are already set in Vercel:
- `DATABASE_URL` - Supabase Postgres connection string ✅
- `SUPABASE_URL` - Supabase project URL ✅
- `SUPABASE_ANON_KEY` - Supabase anonymous key ✅
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key ✅

### Local Development

For local development with ChromaDB:
```bash
# Don't set DATABASE_URL, use ChromaDB locally
unset DATABASE_URL
python -m conductor.ingest /path/to/slack/export
```

For local development with Supabase:
```bash
# Set DATABASE_URL to your Supabase connection string
export DATABASE_URL="postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres"
python -m conductor.ingest /path/to/slack/export
```

## Next Steps

### 1. Test vecs Query Format

The `vecs_client.py` query function needs to be tested and potentially updated based on the actual vecs API return format. The current implementation may need adjustment.

### 2. Migrate Existing Data (Optional)

If you have existing ChromaDB data, create a migration script:

```python
# conductor/migrate_to_vecs.py
from conductor.vecs_client import upsert_vecs
import chromadb

# Read from ChromaDB
chroma_client = chromadb.PersistentClient(path="/path/to/chromadb")
collection = chroma_client.get_collection("conductor_sessions")

# Get all records
all_data = collection.get()

# Convert to vecs format
records = []
for i, doc_id in enumerate(all_data["ids"]):
    records.append((
        doc_id,
        all_data["documents"][i],
        all_data["metadatas"][i]
    ))

# Upsert to vecs
upsert_vecs(records)
```

### 3. Deploy and Test

1. Deploy to Vercel:
   ```bash
   vercel --prod
   ```

2. Test the API:
   ```bash
   curl https://queryable-slack.vercel.app/api/query \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"query": "test query"}'
   ```

## Notes

- Vecs uses the same embedding model (all-MiniLM-L6-v2, 384 dimensions) as ChromaDB
- Metadata filtering works the same way in both systems
- The system maintains ChromaDB compatibility for local development

