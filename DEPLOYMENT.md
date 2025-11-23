# Deployment Guide: Vercel + Supabase

This guide walks you through deploying the Queryable Slack application to Vercel (frontend + backend) and Supabase (database).

## Prerequisites

1. **Vercel Account**: Sign up at https://vercel.com
2. **Supabase Account**: Sign up at https://supabase.com
3. **Vercel CLI**: Install with `npm i -g vercel`
4. **Supabase CLI**: Install with `brew install supabase/tap/supabase` (macOS) - **DO NOT use npm!**

## Architecture

```
┌─────────────────┐
│  Vercel         │
│  ┌───────────┐  │
│  │ React App │  │  Static Site (web/)
│  └───────────┘  │
│  ┌───────────┐  │
│  │ API       │  │  Serverless Functions (api/)
│  └─────┬─────┘  │
└────────┼─────────┘
         │
         ▼
┌─────────────────┐
│  Supabase       │
│  ┌───────────┐  │
│  │ Postgres  │  │  Database (ChromaDB data)
│  └───────────┘  │
└─────────────────┘
```

## Step 1: Set Up Supabase

### 1.1 Create Supabase Project

```bash
# Login to Supabase
supabase login

# Create a new project (you'll need your org ID from Supabase dashboard)
supabase projects create queryable-slack \
  --org-id YOUR_ORG_ID \
  --db-password "YOUR_SECURE_PASSWORD" \
  --region us-east-1
```

### 1.2 Link Local Project to Supabase

```bash
# Link to your remote project (get project ref from Supabase dashboard)
supabase link --project-ref YOUR_PROJECT_REF
```

### 1.3 Set Up Database Schema

We'll use Supabase Postgres to store ChromaDB data. Create a migration:

```bash
supabase migration new setup_chromadb_storage
```

Edit the migration file in `supabase/migrations/` to set up tables for ChromaDB metadata.

### 1.4 Push Migrations

```bash
supabase db push
```

### 1.5 Get Supabase Credentials

```bash
# Get your project credentials
supabase projects list
```

Note down:
- `SUPABASE_URL`: Your project URL (e.g., `https://xxxxx.supabase.co`)
- `SUPABASE_ANON_KEY`: Your anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Your service role key (keep secret!)
- `DATABASE_URL`: Your database connection string

## Step 2: Set Up Vercel

### 2.1 Install Vercel CLI (if not already installed)

```bash
npm i -g vercel
```

### 2.2 Login to Vercel

```bash
vercel login
```

### 2.3 Link Project to Vercel

```bash
# In the project root
vercel link
```

Follow the prompts to:
- Set up and develop? **Yes**
- Which scope? **Your account**
- Link to existing project? **No** (create new)
- Project name? **queryable-slack**
- Directory? **./**

### 2.4 Set Environment Variables

```bash
# Set environment variables in Vercel
vercel env add ANTHROPIC_API_KEY
vercel env add SUPABASE_URL
vercel env add SUPABASE_ANON_KEY
vercel env add SUPABASE_SERVICE_ROLE_KEY
vercel env add DATABASE_URL
vercel env add CHROMADB_PATH  # Path to ChromaDB data in Supabase storage
```

Or set them via Vercel dashboard:
1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add each variable for Production, Preview, and Development

### 2.5 Deploy to Vercel

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

## Step 3: Configure Frontend

### 3.1 Update API URL

Edit `web/src/App.jsx` to use your Vercel API URL:

```javascript
// For production
const API_URL = process.env.VITE_API_URL || 'https://your-app.vercel.app/api'

// For development
// const API_URL = 'http://localhost:8000'
```

### 3.2 Build Frontend

```bash
cd web
npm install
npm run build
```

## Step 4: Database Migration Strategy

Since ChromaDB uses local file storage, we have two options:

### Option A: Use Supabase Storage for ChromaDB Files

1. Upload ChromaDB database files to Supabase Storage
2. Mount storage bucket as filesystem in Vercel functions
3. Point ChromaDB to mounted path

### Option B: Use Supabase Postgres Directly

1. Migrate ChromaDB data to Supabase Postgres tables
2. Use Supabase's native vector search capabilities
3. Update `conductor/ask.py` to query Supabase instead

**Recommended**: Option A for now (simpler migration)

## Step 5: Deploy Database Files to Supabase Storage

```bash
# Install Supabase storage CLI tools
npm install -g @supabase/storage-js

# Upload ChromaDB database directory
# (You'll need to create a storage bucket first in Supabase dashboard)
supabase storage upload chromadb-bucket /path/to/chromadb/data
```

## Step 6: Update Configuration

### 6.1 Update `conductor/config.py`

```python
import os
from pathlib import Path

# For Vercel/Supabase deployment
if os.environ.get('VERCEL'):
    # Use Supabase storage path
    DEFAULT_DB_PATH = Path(os.environ.get('CHROMADB_PATH', '/tmp/chromadb'))
else:
    # Local development
    DEFAULT_DB_PATH = Path("/Users/noahdeskin/slack-vectoriezed-data")
```

### 6.2 Create `api/requirements.txt`

```bash
# Copy requirements.txt to api/requirements.txt
cp requirements.txt api/requirements.txt
```

## Step 7: Final Deployment

```bash
# Deploy everything to Vercel
vercel --prod

# Verify deployment
vercel inspect
```

## Step 8: Post-Deployment

### 8.1 Test the API

```bash
curl https://your-app.vercel.app/api/query \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

### 8.2 Monitor Logs

```bash
# View Vercel function logs
vercel logs https://your-app.vercel.app

# View Supabase logs
supabase db logs
```

## Troubleshooting

### Issue: Function timeout
- **Solution**: Increase `maxDuration` in `vercel.json` (max 60s for Hobby, 300s for Pro)

### Issue: Database connection errors
- **Solution**: Check `DATABASE_URL` and ensure Supabase allows connections from Vercel IPs

### Issue: ChromaDB not found
- **Solution**: Ensure `CHROMADB_PATH` points to correct location in Supabase storage

### Issue: CORS errors
- **Solution**: Verify CORS headers in `api/query.py` match your frontend domain

## Environment Variables Reference

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `ANTHROPIC_API_KEY` | Claude API key | Anthropic dashboard |
| `SUPABASE_URL` | Supabase project URL | Supabase dashboard |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Supabase dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Supabase dashboard |
| `DATABASE_URL` | Postgres connection string | Supabase dashboard |
| `CHROMADB_PATH` | Path to ChromaDB data | Supabase storage path |

## Next Steps

1. Set up CI/CD with GitHub Actions
2. Configure custom domain
3. Set up monitoring and alerts
4. Optimize function cold starts
5. Set up database backups

## Support

- Vercel Docs: https://vercel.com/docs
- Supabase Docs: https://supabase.com/docs
- Project Issues: Open an issue on GitHub

