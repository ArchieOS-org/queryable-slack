# 🚨 URGENT: Enable pgvector Extension

## The Problem

You're getting:
```
ERROR: type extensions.vector does not exist
```

This means **pgvector is not enabled** in your Supabase project.

## Two Ways to Fix This

### Option A: Enable via Supabase Dashboard (EASIEST)

1. Go to: https://supabase.com/dashboard/project/gxpcrohsbtndndypagie/database/extensions

2. Search for **"vector"** or **"pgvector"**

3. Click the **toggle/enable button** next to "vector"

4. Wait for it to say "Enabled"

5. Then run `supabase/QUICK_FIX.sql` in SQL Editor

### Option B: Enable via SQL (if Option A doesn't work)

1. Go to SQL Editor: https://supabase.com/dashboard/project/gxpcrohsbtndndypagie/sql

2. Run this **FIRST** (just this one line):
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. If you get an error about permissions, try:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
   ```

4. Once that succeeds, then run `supabase/QUICK_FIX.sql`

## Why This Happens

Supabase projects don't have pgvector enabled by default. You must manually enable it once per project.

## After pgvector is Enabled

Then run the full setup:

**In SQL Editor**, paste and run `supabase/QUICK_FIX.sql`

That file will:
- Configure schema access
- Create RPC functions
- Set up indexes
- Grant permissions

## Test It

```bash
./run_test.sh
```

Should show:
```
✅ ALL TESTS PASSED!
```

## Still Having Issues?

### Check if pgvector is installed:

Run this in SQL Editor:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**If it returns a row**: pgvector is installed ✅
**If it returns nothing**: pgvector is NOT installed ❌

### Try enabling with different schema:

```sql
-- Try each of these until one works:
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
```

### Check your Supabase plan:

Some Supabase plans might not have pgvector available. Check:
- Go to: https://supabase.com/dashboard/project/gxpcrohsbtndndypagie/settings/billing
- Ensure your plan supports custom extensions

## Quick Summary

1. **Enable pgvector** (via dashboard or SQL)
2. **Run QUICK_FIX.sql** (in SQL Editor)
3. **Test**: `./run_test.sh`
4. **Done!**

---

**The simplest path**: Use the dashboard extensions page (Option A) - just toggle it on!
