# Vercel + Supabase Configuration Verification

## ✅ Migration Status

- **Total Records Migrated**: 10,088 sessions
- **Migration Batches**: 1,009/1,009 successful
- **Database**: Supabase pgvector (vecs)
- **Collection**: `conductor_sessions` (384 dimensions)

## ✅ Code Configuration

### 1. Connection Pooler (Context7 Best Practice)

**Updated Files:**
- `conductor/vecs_client.py` - Automatically converts to pooler URL for Vercel
- `api/migrate.py` - Uses pooler connection for migrations

**Pooler Format:**
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-1-[REGION].pooler.supabase.com:6543/postgres
```

**Key Features:**
- ✅ Automatically detects Vercel environment (`VERCEL` or `VERCEL_ENV`)
- ✅ Converts direct connection to transaction pooler (port 6543)
- ✅ Uses `aws-1-{region}` format (not `aws-0`)
- ✅ Falls back to direct connection if pooler conversion fails

### 2. Environment Detection

**Files Updated:**
- `conductor/config.py` - Detects `DATABASE_URL` to enable vecs
- `conductor/vecs_client.py` - Detects `VERCEL` environment for pooler

**Logic:**
```python
USE_VECS = bool(os.environ.get('DATABASE_URL'))
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    db_connection = _convert_to_pooler_url(db_connection)
```

### 3. Vercel Configuration

**`vercel.json`:**
- ✅ Frontend build: `@vercel/static-build`
- ✅ API function: `@vercel/python` (Python 3.12)
- ✅ Migration endpoint: `@vercel/python`
- ✅ Routes configured correctly

**`api/requirements.txt`:**
- ✅ Minimal dependencies (no macOS-specific packages)
- ✅ `vecs>=0.4.0` for Supabase pgvector
- ✅ `psycopg[binary]>=3.1.0` for PostgreSQL
- ✅ `mangum>=0.17.0` for FastAPI adapter

## 📋 Required Environment Variables

### Vercel Environment Variables (Production)

**Required:**
- ✅ `DATABASE_URL` - Supabase pooler connection string
  - Format: `postgresql://postgres.gxpcrohsbtndndypagie:[PASSWORD]@aws-1-us-east-1.pooler.supabase.com:6543/postgres`
- ✅ `ANTHROPIC_API_KEY` - Claude API key
- ✅ `SUPABASE_URL` - Project URL (optional, for future features)
- ✅ `SUPABASE_ANON_KEY` - Anonymous key (optional, for future features)

**Optional:**
- `SUPABASE_REGION` - Override default region (default: `us-east-1`)
- `VERCEL` - Automatically set by Vercel

### Local Development

**`.env` file:**
```bash
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.gxpcrohsbtndndypagie.supabase.co:5432/postgres
ANTHROPIC_API_KEY=sk-ant-...
```

## 🔍 Verification Checklist

### 1. Database Connection

```bash
# Test connection via Supabase MCP
# Should return: 10,088 records
SELECT COUNT(*) FROM vecs.conductor_sessions;
```

### 2. Vercel Deployment

```bash
# Deploy to production
vercel --prod

# Check logs
vercel logs --follow
```

### 3. API Endpoint Test

```bash
# Test query endpoint
curl https://queryable-slack.vercel.app/api/query \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "use_deep_research": false}'
```

### 4. Health Check

```bash
# Test health endpoint
curl https://queryable-slack.vercel.app/api/health
```

## 🚀 Deployment Steps

1. **Verify Environment Variables:**
   ```bash
   vercel env ls
   ```

2. **Deploy:**
   ```bash
   vercel --prod
   ```

3. **Test:**
   ```bash
   curl https://queryable-slack.vercel.app/api/health
   ```

## 🔧 Troubleshooting

### Issue: Connection Timeout

**Symptom:** `OperationalError: connection to server at ... failed`

**Solution:**
- Ensure `DATABASE_URL` uses pooler format (`aws-1-{region}.pooler.supabase.com:6543`)
- Check IP whitelisting in Supabase dashboard (if enabled)
- Verify region matches your Supabase project region

### Issue: "vecs is not installed"

**Solution:**
- Check `api/requirements.txt` includes `vecs>=0.4.0`
- Verify deployment logs for installation errors

### Issue: Empty Query Results

**Solution:**
- Verify data exists: `SELECT COUNT(*) FROM vecs.conductor_sessions;`
- Check collection name matches: `conductor_sessions`
- Verify embedding dimension: 384

## 📚 Context7 Best Practices Applied

1. ✅ **Connection Pooler**: Using transaction mode (port 6543) for serverless
2. ✅ **Environment Detection**: Automatic pooler conversion for Vercel
3. ✅ **Error Handling**: Graceful fallback to direct connection
4. ✅ **Minimal Dependencies**: Removed macOS-specific packages
5. ✅ **Lazy Imports**: FastAPI app starts even if conductor modules unavailable

## ✅ Status: Ready for Production

All configuration is complete and verified. The application is ready to deploy to Vercel with Supabase pgvector.

