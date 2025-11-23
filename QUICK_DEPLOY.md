# Quick Deployment Guide

## Prerequisites Setup

### 1. Install CLIs

```bash
# Install Vercel CLI
npm install -g vercel

# Install Supabase CLI (macOS - use Homebrew, NOT npm!)
brew install supabase/tap/supabase

# Verify installations
vercel --version
supabase --version
```

### 2. Login to Services

```bash
# Login to Vercel
vercel login

# Login to Supabase
supabase login
```

## Step-by-Step Deployment

### Step 1: Create Supabase Project

```bash
# Get your org ID from Supabase dashboard first
supabase projects create queryable-slack \
  --org-id YOUR_ORG_ID \
  --db-password "YOUR_SECURE_PASSWORD" \
  --region us-east-1
```

**Save the project reference ID** - you'll need it!

### Step 2: Link Supabase Project

```bash
# Link to your remote project
supabase link --project-ref YOUR_PROJECT_REF
```

### Step 3: Get Supabase Credentials

From Supabase dashboard:
1. Go to Project Settings → API
2. Copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (keep secret!)

From Project Settings → Database:
- Copy `Connection string` → `DATABASE_URL`

### Step 4: Set Up Vercel Project

```bash
# Link project to Vercel
vercel link

# Follow prompts:
# - Set up and develop? Yes
# - Which scope? Your account
# - Link to existing? No
# - Project name? queryable-slack
# - Directory? ./
```

### Step 5: Set Environment Variables in Vercel

```bash
# Set each variable (you'll be prompted for the value)
vercel env add ANTHROPIC_API_KEY production
vercel env add SUPABASE_URL production
vercel env add SUPABASE_ANON_KEY production
vercel env add SUPABASE_SERVICE_ROLE_KEY production
vercel env add DATABASE_URL production
vercel env add CHROMADB_PATH production
```

**Or set via Vercel Dashboard:**
1. Go to your project → Settings → Environment Variables
2. Add each variable for Production, Preview, and Development

### Step 6: Upload ChromaDB Data to Supabase Storage

```bash
# Create storage bucket in Supabase dashboard first
# Then upload your ChromaDB database directory

# Option 1: Via Supabase dashboard
# - Go to Storage → Create bucket "chromadb"
# - Upload your conductor_db/ directory contents

# Option 2: Via CLI (if available)
# supabase storage upload chromadb /path/to/conductor_db
```

### Step 7: Deploy!

```bash
# Deploy to preview first
vercel

# If everything works, deploy to production
vercel --prod
```

### Step 8: Update Frontend API URL

After deployment, update `VITE_API_URL` in Vercel:
- Go to Environment Variables
- Add `VITE_API_URL` = `https://your-app.vercel.app/api`

## Testing

```bash
# Test the API endpoint
curl https://your-app.vercel.app/api/query \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# View logs
vercel logs https://your-app.vercel.app
```

## Troubleshooting

### Function Timeout
- Increase `maxDuration` in `vercel.json` (max 60s for Hobby plan)

### Database Not Found
- Check `CHROMADB_PATH` points to correct Supabase storage path
- Verify ChromaDB files were uploaded correctly

### CORS Errors
- Verify CORS headers in `web_api.py` allow your Vercel domain

### Import Errors
- Check `api/requirements.txt` includes all dependencies
- Verify Python version matches (3.12)

## Next Steps

1. Set up custom domain in Vercel
2. Configure CI/CD with GitHub
3. Set up monitoring and alerts
4. Optimize function performance

