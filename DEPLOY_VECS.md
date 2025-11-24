# Deploying with Supabase Vecs

## ✅ Migration Complete

The system has been migrated to use Supabase pgvector (vecs) when `DATABASE_URL` is set.

## Current Status

- ✅ Code updated to use vecs when `DATABASE_URL` is set
- ✅ Vecs client implementation complete
- ✅ Automatic fallback to ChromaDB for local development
- ⚠️ Needs testing on Vercel

## Next Steps

### 1. Deploy to Vercel

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
vercel --prod
```

### 2. Verify Environment Variables

Ensure these are set in Vercel:
- `DATABASE_URL` - Supabase Postgres connection string ✅
- `ANTHROPIC_API_KEY` - Claude API key ✅
- `SUPABASE_URL` - Supabase project URL ✅
- `SUPABASE_ANON_KEY` - Supabase anonymous key ✅
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key ✅

### 3. Test the API

After deployment, test the API:

```bash
curl https://queryable-slack.vercel.app/api/query \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "use_deep_research": false}'
```

### 4. Ingest Data (if needed)

If you need to ingest data into Supabase:

```bash
# Set DATABASE_URL locally
export DATABASE_URL="postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres"

# Run ingestion
python -m conductor.ingest /path/to/slack/export
```

## Troubleshooting

### Issue: "vecs is not installed"
**Solution**: The `vecs` package should be installed automatically via `requirements.txt`. If not:
```bash
pip install vecs psycopg[binary]
```

### Issue: "DATABASE_URL not set"
**Solution**: Ensure `DATABASE_URL` is set in Vercel environment variables.

### Issue: "Table not found"
**Solution**: Vecs creates tables automatically on first upsert. Make sure you've ingested at least one record.

### Issue: Query returns empty results
**Solution**: 
1. Verify data was ingested: Check Supabase dashboard → Table Editor → `vecs.conductor_sessions`
2. Check logs: `vercel logs --follow`
3. Verify collection name matches: `conductor_sessions`

## How It Works

1. **Detection**: System checks for `DATABASE_URL` environment variable
2. **Vecs Mode**: If set, uses Supabase vecs (pgvector)
3. **ChromaDB Mode**: If not set, uses ChromaDB (local or HTTP client)
4. **Query**: Vecs queries PostgreSQL directly to retrieve full records with metadata
5. **Storage**: Documents are stored in `metadata['document']` for retrieval

## Architecture

```
┌─────────────┐
│   Vercel    │
│  Serverless │
│   Function  │
└──────┬──────┘
       │
       │ DATABASE_URL
       ▼
┌─────────────┐
│  Supabase   │
│  Postgres   │
│  (pgvector) │
└─────────────┘
```

## Notes

- Vecs uses the same embedding model as ChromaDB (all-MiniLM-L6-v2, 384 dimensions)
- Metadata filtering works identically in both systems
- The system maintains backward compatibility with ChromaDB


