# Vercel Database Configuration

## Current Issue

The API is configured to use a local file path (`/Users/noahdeskin/slack-vectoriezed-data`) which doesn't exist on Vercel serverless functions.

## Solution Options

### Option 1: ChromaDB HTTP Client (Recommended)

Host a ChromaDB server and connect via HTTP:

1. **Set up ChromaDB Server** (on Railway, Render, or similar):
   ```bash
   # Install ChromaDB server
   pip install chromadb[server]
   
   # Run server
   chroma run --host 0.0.0.0 --port 8001
   ```

2. **Set Environment Variable in Vercel**:
   ```bash
   vercel env add CHROMADB_URL production
   # Enter: http://your-chromadb-server.com:8001
   ```

3. **The code will automatically use HTTP client when `CHROMADB_URL` is set**

### Option 2: Supabase Storage + Download at Runtime

Store ChromaDB files in Supabase Storage and download to `/tmp`:

1. **Upload ChromaDB data to Supabase Storage**:
   - Create bucket: `chromadb`
   - Upload your `/Users/noahdeskin/slack-vectoriezed-data` directory

2. **Update code to download on cold start** (needs implementation)

### Option 3: Migrate to Supabase pgvector

Use Supabase's native vector search instead of ChromaDB (requires data migration).

## Current Configuration

The code now:
- ✅ Detects Vercel environment (`VERCEL` env var)
- ✅ Uses `/tmp/chromadb` on Vercel (if no `CHROMADB_URL`)
- ✅ Supports HTTP client mode (if `CHROMADB_URL` is set)
- ✅ Falls back to local path for development

## Next Steps

1. **Set `CHROMADB_URL` in Vercel** if you have a ChromaDB server
2. **OR** upload ChromaDB data to Supabase Storage and implement download logic
3. **OR** migrate to Supabase pgvector (more work but better long-term)

## Testing

After setting `CHROMADB_URL`:
```bash
# Test locally with HTTP client
export CHROMADB_URL=http://your-server:8001
python -m conductor.ask "test query"

# Deploy to Vercel
vercel --prod
```

