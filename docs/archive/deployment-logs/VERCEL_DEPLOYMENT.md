# Vercel Deployment Guide - Conductor API

## Overview

This guide covers deploying the Conductor Slack semantic search API to Vercel as a serverless function.

## Prerequisites

1. **Vercel Account**: Sign up at https://vercel.com
2. **Vercel CLI** (optional, but recommended):
   ```bash
   npm install -g vercel
   ```
3. **Environment Variables**: Supabase and Anthropic API keys

## Project Structure

```
queryable-slack-2/
├── api/
│   └── index.py          # FastAPI application (serverless entry point)
├── conductor/            # Python package with core logic
│   ├── supabase_query.py
│   ├── models.py
│   └── ...
├── requirements-vercel.txt  # Dependencies for Vercel
├── vercel.json           # Vercel configuration
└── .env                  # Local env vars (not deployed)
```

## Step 1: Prepare Environment Variables

### Required Environment Variables:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anon/public key
- `ANTHROPIC_API_KEY`: Your Anthropic/Claude API key
- `AI_GATEWAY_API_KEY`: (Optional) Vercel AI Gateway key

### Set via Vercel Dashboard:

1. Go to your project in Vercel Dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add each variable:
   - Name: `SUPABASE_URL`
   - Value: `https://your-project.supabase.co`
   - Environment: Production, Preview, Development (select all)
4. Repeat for all required variables

### Or via Vercel CLI:

```bash
vercel env add SUPABASE_URL
# Enter value when prompted
# Select environments: Production, Preview, Development

vercel env add SUPABASE_ANON_KEY
vercel env add ANTHROPIC_API_KEY
vercel env add AI_GATEWAY_API_KEY
```

## Step 2: Deploy to Vercel

### Option A: Deploy via Git (Recommended)

1. **Push to GitHub/GitLab/Bitbucket**:
   ```bash
   git add .
   git commit -m "Add Vercel deployment configuration"
   git push origin main
   ```

2. **Import Project in Vercel**:
   - Go to https://vercel.com/new
   - Click "Import Git Repository"
   - Select your repository
   - Vercel will auto-detect configuration from `vercel.json`
   - Click "Deploy"

3. **Configure Build Settings** (if prompted):
   - Framework Preset: Other
   - Build Command: (leave empty)
   - Output Directory: (leave empty)
   - Install Command: `pip install -r requirements-vercel.txt`

### Option B: Deploy via CLI

1. **Login to Vercel**:
   ```bash
   vercel login
   ```

2. **Deploy** (from project root):
   ```bash
   cd /path/to/queryable-slack-2
   vercel
   ```

3. **Follow prompts**:
   - Set up and deploy? Yes
   - Which scope? (select your account/team)
   - Link to existing project? No (first time) or Yes (updates)
   - Project name? (e.g., `conductor-api`)
   - Directory? `./` (project root)

4. **Deploy to production**:
   ```bash
   vercel --prod
   ```

## Step 3: Verify Deployment

### Test Health Endpoint:

```bash
curl https://your-deployment-url.vercel.app/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "supabase_connected": true,
  "version": "1.0.0"
}
```

### Test Sessions Endpoint:

```bash
curl https://your-deployment-url.vercel.app/api/sessions?limit=5
```

### Test Query Endpoint:

```bash
curl -X POST https://your-deployment-url.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What deals did we close last month?",
    "match_count": 5
  }'
```

### Interactive API Documentation:

Visit: `https://your-deployment-url.vercel.app/api/docs`

## Step 4: Configure Custom Domain (Optional)

1. Go to **Project Settings** → **Domains**
2. Add your custom domain (e.g., `api.yourdomain.com`)
3. Follow DNS configuration instructions
4. Wait for SSL certificate provisioning (automatic)

## API Endpoints

### GET /
Root endpoint with API information

### GET /api/health
Health check endpoint
- Returns: Supabase connection status

### GET /api/sessions
List recent sessions
- Query params:
  - `limit` (int, default: 10, max: 50)
  - `channel` (string, optional): Filter by channel name

### GET /api/sessions/{session_id}
Get specific session by ID
- Path param: `session_id` (string)

### POST /api/query
Semantic search with Claude answer generation
- Body:
  ```json
  {
    "query": "string",
    "match_count": 5,
    "match_threshold": 0.0,
    "channel_filter": "optional-channel-name"
  }
  ```

## Troubleshooting

### Deployment Fails: "Bundle size exceeds 250MB"

**Solution**: Optimize dependencies in `requirements-vercel.txt`
- Remove unused packages
- Use specific versions
- Check `excludeFiles` in `vercel.json`

### Error: "Module not found: conductor"

**Solution**: Ensure `conductor/` directory is included in deployment
- Check `.gitignore` doesn't exclude `conductor/`
- Verify `conductor/__init__.py` exists

### Error: "Environment variable not set"

**Solution**: Add missing environment variables in Vercel Dashboard
- Settings → Environment Variables
- Redeploy after adding variables

### Cold Start Timeout

**Symptoms**: First request takes 10+ seconds
**Solution**: 
- Increase `maxDuration` in `vercel.json` (if on Pro plan)
- Implement warming strategy (periodic health checks)
- Use Vercel's RuntimeCache for expensive operations

### Supabase Connection Fails

**Check**:
1. Environment variables are set correctly
2. Supabase URL is correct (https://xxx.supabase.co)
3. Supabase anon key is valid
4. "Exposed schemas" includes `vecs` (see EXPOSED_SCHEMAS_FIX.md)

## Performance Optimization

### 1. Bundle Size Optimization

Current `excludeFiles` pattern excludes:
- Test files (`tests/`, `**/*.test.py`)
- Documentation (`*.md`)
- Conductor working directories (`.conductor/`)
- Local databases (`conductor_db/`)
- Git history (`.git/`)
- Virtual environments (`.venv/`)

### 2. Cold Start Optimization

```python
# In api/index.py, cache expensive imports at module level
from conductor.supabase_query import get_supabase_client

# Reuse client across invocations
_supabase_client = None

def get_cached_client():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = get_supabase_client()
    return _supabase_client
```

### 3. Response Caching

Use Vercel's RuntimeCache for frequently accessed data:

```python
from vercel.functions import AsyncRuntimeCache

cache = AsyncRuntimeCache()

@app.get("/api/cached-sessions")
async def cached_sessions():
    key = "recent_sessions"
    cached = await cache.get(key)
    if cached:
        return cached
    
    sessions = list_recent_sessions(limit=10)
    await cache.set(key, sessions, {"ttl": 300})  # 5 min TTL
    return sessions
```

## Monitoring

### View Logs:

**Via Dashboard:**
- Go to project → Deployments → Click deployment → View logs

**Via CLI:**
```bash
vercel logs
vercel logs --follow  # Real-time logs
```

### Metrics:

Vercel Dashboard provides:
- Request count
- Error rate
- Duration (p50, p95, p99)
- Cold start frequency

## Scaling

Vercel automatically scales your serverless functions:
- **Concurrent executions**: Unlimited (subject to plan limits)
- **Auto-scaling**: Handles traffic spikes automatically
- **Regional deployment**: Configure in `vercel.json`:
  ```json
  {
    "regions": ["sfo1", "iad1", "cdg1"]
  }
  ```

## Cost Considerations

### Hobby Plan (Free):
- 100 GB-hours execution time
- 10-second max duration
- 1024 MB memory

### Pro Plan ($20/mo):
- 1000 GB-hours included
- 60-second max duration
- 3008 MB memory
- Custom domains
- Team collaboration

### Estimated Usage:
- Typical query: ~2 seconds execution
- Memory: 512-1024 MB
- With 1000 queries/day: ~0.5-1 GB-hours/day

## Security Best Practices

1. **Never commit `.env` files**
2. **Use Vercel environment variables** for all secrets
3. **Configure CORS** properly in `api/index.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Specify allowed origins
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["*"],
   )
   ```
4. **Rate limiting**: Implement if needed (use Vercel Pro features or external service)
5. **API authentication**: Add if exposing publicly

## Next Steps

1. ✅ Deploy to Vercel
2. ✅ Verify all endpoints work
3. ✅ Test with real queries
4. 🔄 Implement proper embedding generation (TODO in api/index.py)
5. 🔄 Add Vercel AI Gateway integration
6. 🔄 Build frontend interface (optional)
7. 🔄 Set up monitoring/alerting

## Support

- **Vercel Documentation**: https://vercel.com/docs
- **Vercel Discord**: https://vercel.com/discord
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Supabase Documentation**: https://supabase.com/docs

## Files Reference

- **`api/index.py`**: FastAPI application entry point
- **`vercel.json`**: Vercel configuration (runtime, memory, excludes)
- **`requirements-vercel.txt`**: Python dependencies for deployment
- **`.env.example`**: Template for environment variables
- **`VERCEL_DEPLOYMENT.md`**: This file

---

## Quick Start Commands

```bash
# 1. Set environment variables
vercel env add SUPABASE_URL
vercel env add SUPABASE_ANON_KEY
vercel env add ANTHROPIC_API_KEY

# 2. Deploy
vercel --prod

# 3. Test
curl https://your-url.vercel.app/api/health

# 4. View logs
vercel logs --follow
```

**Your API is now live! 🚀**
