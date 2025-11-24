# Migration Execution Plan - Final Steps

## Current Status

✅ **Completed:**
- SQL batch files generated: 1,009 batches (~10 records each, ~84KB per batch)
- Supabase table created: `vecs.conductor_sessions` with proper schema
- Migration scripts created with Context7 best practices (pipeline mode)
- Vercel endpoint deployed: `/api/migrate` (updated with pipeline mode)
- MCP tools verified: Supabase MCP execute_sql works for smaller queries

⚠️ **Challenge:**
- Batch files are ~84KB each, too large for single MCP execute_sql calls
- Local connection to Supabase times out
- Vercel endpoint needs testing/debugging

## Solution: Execute via Vercel Serverless Function

The best approach is to use the Vercel serverless function where `DATABASE_URL` is accessible. The function uses Context7 best practices (psycopg pipeline mode) for optimal performance.

### Step 1: Deploy Updated Code

The migration endpoint has been updated with:
- ✅ Pipeline mode for batch execution (Context7 best practice)
- ✅ Better error handling
- ✅ Proper psycopg import handling

### Step 2: Execute Batches via HTTP

Use the `migrate_via_vercel.py` script to execute batches:

```bash
# Test with first 10 batches
python3 -m conductor.migrate_via_vercel \
  --sql-dir /tmp/migration_small \
  --vercel-url https://queryable-slack.vercel.app \
  --max-batches 10

# Execute all batches (1,009 total)
python3 -m conductor.migrate_via_vercel \
  --sql-dir /tmp/migration_small \
  --vercel-url https://queryable-slack.vercel.app
```

### Step 3: Monitor Progress

Check migration progress:

```bash
# Via Supabase MCP
# Query: SELECT COUNT(*) FROM vecs.conductor_sessions;

# Or via curl
curl https://queryable-slack.vercel.app/api/migrate \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) as count FROM vecs.conductor_sessions;", "batch_name": "count_check"}'
```

## Alternative: Execute Smaller Batches via MCP

If Vercel endpoint still fails, split batches into smaller chunks (5 records instead of 10):

```bash
# Split batches (creates ~2,018 files with 5 records each)
python3 -m conductor.split_batches_for_mcp --records-per-chunk 5

# Then execute via MCP (manual process)
# Each batch will be ~40KB, more manageable for MCP
```

## Files Created

1. **`conductor/execute_batches_optimized.py`** - Uses psycopg pipeline mode (Context7 best practice)
2. **`conductor/migrate_via_vercel.py`** - Executes batches via Vercel HTTP endpoint
3. **`conductor/execute_batches_via_mcp.py`** - Helper for MCP execution
4. **`web_api.py`** - Updated migration endpoint with pipeline mode
5. **`api/migrate_bulk.py`** - Bulk batch execution endpoint (alternative)

## Next Steps

1. **Deploy to Vercel**: `vercel deploy --prod`
2. **Test endpoint**: Execute first batch via HTTP
3. **Execute all batches**: Run migration script
4. **Verify**: Check record count in Supabase

## Expected Results

- **Total records**: ~10,090 sessions
- **Total batches**: 1,009 files
- **Estimated time**: ~30-60 minutes (depending on network/Vercel performance)

