# Supabase Connection Issue

## Problem
Connection to Supabase PostgreSQL is timing out. This is likely because:

1. **IP Restrictions**: Supabase may require whitelisting your IP address
2. **Connection Method**: Direct connections (port 5432) may be disabled
3. **Connection Pooler**: May need to use pooler (port 6543) with correct format

## Solutions

### Option 1: Enable Direct Connections in Supabase

1. Go to Supabase Dashboard → Settings → Database
2. Check "Allow connections from anywhere" or add your IP to whitelist
3. Verify connection string format

### Option 2: Use Connection Pooler

The connection pooler format should be:
```
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

For your project:
```
postgresql://postgres.gxpcrohsbtndndypagie:34Huntley!34Huntley@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### Option 3: Migrate via Vercel (Recommended)

Since Vercel already has `DATABASE_URL` set and can connect, we can:
1. Deploy a migration script as a Vercel serverless function
2. Run it once to migrate the data
3. Delete it after migration

### Option 4: Use Supabase CLI

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Link to project
supabase link --project-ref gxpcrohsbtndndypagie

# Run migration via Supabase CLI
```

## Next Steps

Try Option 3 (Vercel migration) as it's the most reliable since Vercel can already connect to Supabase.


