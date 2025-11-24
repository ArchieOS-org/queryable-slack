# 🎯 EXPOSED SCHEMAS FIX - Add "vecs" to Exposed Schemas

## The Issue (From Your Screenshot)

Looking at your Supabase Data API Settings, I can see:

✅ **Extra search path**: `public`, `extensions`, `vecs` (CORRECT)
❌ **Exposed schemas**: `public`, `graphql_public` (MISSING `vecs`)

## What's the Difference?

Based on Context7 research of PostgREST documentation:

### **Exposed Schemas** (db-schemas) - THE GATEKEEPER
- **Purpose**: Defines which schemas are **exposed via REST API**
- **Required**: YES - schemas MUST be here to be accessible via HTTP
- **Your current value**: `public`, `graphql_public`
- **Error when missing**: PGRST106 - "The schema must be one of the following: public, graphql_public"
- **What you need**: Add `vecs` to this list

### **Extra Search Path** (db-extra-search-path) - SQL RESOLUTION
- **Purpose**: Helps PostgreSQL find functions/types in these schemas
- **Required for API**: NO - this is for internal SQL resolution only
- **Your current value**: `public`, `extensions`, `vecs` (already correct ✅)
- **What it does**: Allows your RPC functions to find the vector type and other objects

## The Fix (Based on Your Screenshot)

### Step 1: Click in the "Exposed schemas" Field

In your Supabase Dashboard (the screenshot you showed):
1. Look at the **"Exposed schemas"** section (first field)
2. You'll see: `public` ❌ `graphql_public` ❌

### Step 2: Add "vecs" to Exposed Schemas

Click in the input field and type: `vecs`

The field should now show:
```
public ❌  graphql_public ❌  vecs ❌
```

### Step 3: Save the Configuration

1. Click the **"Save"** button at the bottom right
2. Wait 1-2 minutes for PostgREST to restart

### Step 4: Test It

```bash
./run_test.sh
```

**Expected output:**
```
✅ match_conductor_sessions RPC function exists → Function returned X results
✅ match_conductor_sessions_filtered RPC function exists → Function returned X results
✅ list_recent_sessions passed → Retrieved X sessions
✅ get_session_by_id passed
✅ get_sessions_by_channel passed

✅ ALL TESTS PASSED!
```

## Why This Fixes the PGRST106 Error

### Before (Current State):
- **Exposed schemas**: `public`, `graphql_public`
- **Result**: PostgREST only allows REST API access to `public` and `graphql_public` schemas
- **Your table**: Lives in `vecs` schema
- **Error**: PGRST106 - "The schema must be one of the following: public, graphql_public"

### After (With vecs Added):
- **Exposed schemas**: `public`, `graphql_public`, `vecs`
- **Result**: PostgREST now exposes `vecs` schema via REST API
- **Your table**: Accessible via REST API
- **Error**: Fixed! ✅

## Why RPC Functions Work But Direct Queries Don't

From Context7 research:

- **RPC Functions**: Created in `public` schema (already in exposed schemas) ✅
- **Direct Table Queries**: Try to access `vecs.conductor_sessions` (NOT in exposed schemas) ❌

```python
# This works because function is in 'public' (exposed)
client.rpc('match_conductor_sessions', {...}).execute()  # ✅

# This fails because table is in 'vecs' (not exposed)
client.schema('vecs').from_('conductor_sessions').select('*').execute()  # ❌
```

## Configuration Summary

### Current (From Screenshot):
```
Exposed schemas:      public, graphql_public
Extra search path:    public, extensions, vecs  ✅
```

### Needed:
```
Exposed schemas:      public, graphql_public, vecs  ← ADD THIS
Extra search path:    public, extensions, vecs  ✅ (already correct)
```

## PostgREST Configuration Explained (From Context7)

According to PostgREST documentation:

```ini
# Exposed schemas (db-schemas) - Controls REST API access
db-schemas = "public, graphql_public, vecs"

# Extra search path (db-extra-search-path) - For SQL resolution
db-extra-search-path = "public, extensions, vecs"
```

**Key Points from PostgREST Docs:**
1. `db-schemas` is the **gatekeeper** for REST API access
2. Only schemas listed in `db-schemas` can be accessed via HTTP endpoints
3. `db-extra-search-path` is for SQL function resolution (not for API access)
4. You typically need **both** configured

## Verification After Fix

### Check 1: Run Tests
```bash
./run_test.sh
```

Should show all tests passing ✅

### Check 2: Verify Configuration
In Supabase Dashboard, you should see:
```
Exposed schemas:      public ❌  graphql_public ❌  vecs ❌
Extra search path:    public ❌  extensions ❌  vecs ❌
```

### Check 3: Manual Query Test
```python
from supabase import create_client
import os

client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_ANON_KEY')
)

# This should now work
result = client.schema('vecs').from_('conductor_sessions').select('*').limit(1).execute()
print(f"✅ Retrieved {len(result.data)} records")
```

## Summary

**What you did wrong**: Only added `vecs` to "Extra search path"
**What you need to do**: Also add `vecs` to "Exposed schemas"

**Simple fix**:
1. In the screenshot you showed, click in "Exposed schemas" field
2. Type: `vecs`
3. Click "Save"
4. Wait 1-2 minutes
5. Run: `./run_test.sh`
6. Should see: ✅ ALL TESTS PASSED!

## Why Both Settings Are Needed

Based on Context7 PostgREST documentation:

### Extra Search Path (Already Configured ✅)
- Helps your RPC functions find the `vector` type from `public` or `extensions` schema
- Allows SQL functions to resolve unqualified object names
- Your RPC functions work because of this setting

### Exposed Schemas (MISSING `vecs` ❌)
- Controls which schemas are accessible via REST API
- **REQUIRED** for direct table access via Supabase client
- Your direct table queries fail because `vecs` is not here

**Both are needed for full functionality!**

---

## TL;DR

Go back to that screen in your screenshot and:
1. Click in "Exposed schemas" field
2. Add: `vecs`
3. Save
4. Wait 1-2 minutes
5. Run: `./run_test.sh`
6. ✅ Done!

The field should show: `public ❌ graphql_public ❌ vecs ❌`
