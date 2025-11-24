# Migration Status

## Summary

The migration from ChromaDB to Supabase pgvector is **ready to execute**. All infrastructure is in place:

1. ✅ **SQL batch files generated**: 1,009 batches (~10 records each, ~83KB per batch)
2. ✅ **Supabase table created**: `vecs.conductor_sessions` with proper schema
3. ✅ **Migration scripts created**: Multiple approaches available
4. ✅ **Vercel endpoint deployed**: `/api/migrate` (needs psycopg fix)
5. ✅ **MCP tools verified**: Supabase MCP execute_sql works

## Current Status

- **Records in Supabase**: 2 (test records)
- **Records to migrate**: ~10,090 (from ChromaDB)
- **Batch files**: `/tmp/migration_small/batch_*.sql` (1,009 files)

## Execution Options

### Option 1: Execute via Supabase MCP (Recommended)

Since MCP execute_sql works, you can execute batches manually or via a script:

```bash
# Execute batches one at a time via MCP
# Each batch file is ~83KB with 10 records
```

**Note**: Each batch file is ~83KB which may be too large for a single MCP call. Consider splitting batches further (5 records per file) if needed.

### Option 2: Fix Vercel Migration Endpoint

The Vercel endpoint `/api/migrate` is deployed but failing with `FUNCTION_INVOCATION_FAILED`. 

**Issues to fix**:
- psycopg import/runtime error
- Check Vercel function logs for exact error

**Fix steps**:
1. Check if `psycopg[binary]>=3.1.0` is properly installed in `api/requirements.txt`
2. Verify Vercel is using the correct Python version (3.12)
3. Check function logs: `vercel logs queryable-slack.vercel.app`

### Option 3: Local Migration Script

If local connection to Supabase works:

```bash
python3 -m conductor.execute_sql_batches --sql-dir /tmp/migration_small --db-url "$DATABASE_URL"
```

**Note**: Local connection to Supabase has been timing out, so this may not work.

## Next Steps

1. **Execute first batch via MCP** to verify it works
2. **If successful**, create a script to execute all batches
3. **If batches are too large**, split them further (5 records per file = ~2,018 batches)
4. **Monitor progress** by checking record count: `SELECT COUNT(*) FROM vecs.conductor_sessions;`

## Verification

After migration, verify data:

```sql
SELECT COUNT(*) as total_records FROM vecs.conductor_sessions;
SELECT COUNT(DISTINCT id) as unique_ids FROM vecs.conductor_sessions;
SELECT * FROM vecs.conductor_sessions LIMIT 5;
```

## Files Created

- `/tmp/migration_small/batch_*.sql` - SQL batch files (1,009 files)
- `conductor/migrate_small_batches.py` - Script to generate batches
- `conductor/migrate_via_vercel.py` - Script to execute via Vercel API
- `conductor/execute_sql_batches.py` - Script to execute locally
- `web_api.py` - Migration endpoint (`/api/migrate`)
- `api/requirements.txt` - Updated with psycopg

## Estimated Time

- **Per batch**: ~1-2 seconds (via MCP)
- **Total batches**: 1,009
- **Estimated total time**: ~30-60 minutes (if executed sequentially)

**Recommendation**: Execute batches in parallel if possible, or use Vercel endpoint once fixed.

