# Update Vercel DATABASE_URL for Connection Pooler

## Issue
The current `DATABASE_URL` in Vercel uses a direct connection which resolves to IPv6. Vercel doesn't support IPv6, so we need to use Supabase's connection pooler (IPv4 compatible).

## Solution

### Step 1: Get Pooler Connection String from Supabase Dashboard

1. Go to your Supabase project dashboard
2. Click **Settings** → **Database**
3. Under **Connection string**, select **Transaction mode** (port 6543)
4. Copy the connection string - it should look like:
   ```
   postgresql://postgres.gxpcrohsbtndndypagie:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```

### Step 2: Update Vercel Environment Variable

Run this command and paste the pooler connection string when prompted:

```bash
vercel env add DATABASE_URL production
```

Or update via Vercel Dashboard:
1. Go to your Vercel project settings
2. Navigate to **Environment Variables**
3. Edit `DATABASE_URL`
4. Paste the transaction pooler connection string
5. Save

### Step 3: Redeploy

After updating the environment variable, redeploy:

```bash
vercel deploy --prod
```

### Step 4: Test Migration Endpoint

```bash
curl -X POST https://queryable-slack.vercel.app/api/migrate \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) as count FROM vecs.conductor_sessions;", "batch_name": "test"}'
```

## Expected Connection String Format

For project `gxpcrohsbtndndypagie`:
```
postgresql://postgres.gxpcrohsbtndndypagie:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

**Important**: Replace `[PASSWORD]` with your actual database password and `[REGION]` with your project's region (e.g., `us-east-1`, `us-west-1`, `eu-west-1`, etc.).

## Why Transaction Pooler?

- **IPv4 compatible**: Works with Vercel (which doesn't support IPv6)
- **Optimized for serverless**: Transaction mode (port 6543) is designed for serverless functions
- **Better connection management**: Handles many transient connections efficiently

