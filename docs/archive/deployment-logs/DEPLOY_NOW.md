# 🚀 Deploy to Vercel - Quick Start

## Files Created ✅

- ✅ `api/index.py` - FastAPI application
- ✅ `vercel.json` - Vercel configuration
- ✅ `requirements-vercel.txt` - Python dependencies
- ✅ `.vercelignore` - Files to exclude from deployment
- ✅ `.gitignore` - Updated with Vercel entries
- ✅ `VERCEL_DEPLOYMENT.md` - Complete deployment guide

## Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

## Step 2: Login to Vercel

```bash
vercel login
```

## Step 3: Set Environment Variables

You need to set these environment variables in Vercel:

```bash
vercel env add SUPABASE_URL
# When prompted, enter: https://gxpcrohsbtndndypagie.supabase.co

vercel env add SUPABASE_ANON_KEY  
# Enter your Supabase anon key from .env

vercel env add ANTHROPIC_API_KEY
# Enter your Anthropic API key

vercel env add AI_GATEWAY_API_KEY
# Enter: vck_10FUrzsEszbdp3k75TGQ0dWFLzGnwj9zePsTQaAwGzXVUOFYjB4728l2
```

**For each variable:**
- Select all environments: Production, Preview, Development (use space bar)
- Press Enter to confirm

## Step 4: Deploy to Vercel

From the project root directory:

```bash
cd /Users/noahdeskin/conductor/queryable-slack-2
vercel --prod
```

Follow the prompts:
- **Set up and deploy?** Yes
- **Which scope?** (Select your account)
- **Link to existing project?** No (first time)
- **Project name?** `conductor-api` (or your choice)
- **In which directory?** ./ (press Enter)
- **Override settings?** No

## Step 5: Test Your Deployment

After deployment completes, you'll get a URL like: `https://conductor-api-xxx.vercel.app`

### Test Health:
```bash
curl https://your-url.vercel.app/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "supabase_connected": true,
  "version": "1.0.0"
}
```

### Test Sessions:
```bash
curl https://your-url.vercel.app/api/sessions?limit=3
```

### Interactive Docs:
Open in browser: `https://your-url.vercel.app/api/docs`

## Alternative: Deploy via Git

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add Vercel deployment"
   git push origin main
   ```

2. **Import in Vercel:**
   - Go to https://vercel.com/new
   - Click "Import Git Repository"
   - Select your repo
   - Vercel auto-detects `vercel.json`
   - Add environment variables in dashboard
   - Click "Deploy"

## Troubleshooting

### Error: "Environment variable not set"
- Add missing variables: `vercel env add VARIABLE_NAME`
- Redeploy: `vercel --prod`

### Error: "Module not found: conductor"
- Ensure `conductor/` directory is committed to git
- Check `.vercelignore` doesn't exclude it

### Error: "Build failed"
- Check Vercel build logs: `vercel logs`
- Verify `requirements-vercel.txt` has all dependencies

### Supabase Connection Fails
- Verify `SUPABASE_URL` is correct in Vercel environment
- Check `SUPABASE_ANON_KEY` is valid
- Ensure "Exposed schemas" includes `vecs` in Supabase Dashboard

## What Gets Deployed

✅ **Included:**
- `api/` directory (FastAPI app)
- `conductor/` package (Python modules)
- Python dependencies from `requirements-vercel.txt`

❌ **Excluded (via .vercelignore):**
- `.conductor/` directory (local context)
- `conductor_db/` (local ChromaDB)
- `.venv/`, `.git/`, tests/
- Documentation (except README and deployment guide)
- `.env` files (use Vercel environment variables)

## Environment Variables Summary

| Variable | Value | Source |
|----------|-------|--------|
| `SUPABASE_URL` | https://gxpcrohsbtndndypagie.supabase.co | Your .env file |
| `SUPABASE_ANON_KEY` | eyJhbGciOi... | Your .env file |
| `ANTHROPIC_API_KEY` | sk-ant-... | Your .env file |
| `AI_GATEWAY_API_KEY` | vck_10FUrz... | Vercel AI Gateway (q-slack) |

## Next Steps After Deployment

1. ✅ Verify all endpoints work
2. ✅ Test with real queries
3. 🔄 Implement proper embedding generation (currently uses recent sessions as fallback)
4. 🔄 Integrate Vercel AI Gateway for Claude queries
5. 🔄 Add rate limiting if needed
6. 🔄 Build frontend interface (optional)
7. 🔄 Set up custom domain (optional)

## Important Notes

- **Bundle Size**: Currently ~50-100 MB (well under 250 MB limit)
- **Max Duration**: 30 seconds (configurable in vercel.json)
- **Memory**: 3008 MB (maximum available)
- **Runtime**: Python 3.11
- **Region**: sfo1 (San Francisco - close to your location)

## Cost

**Vercel Hobby Plan (Free):**
- 100 GB-hours execution time per month
- With ~2 second queries: ~50,000 requests/month
- Enough for development and moderate usage

**Vercel Pro Plan ($20/month):**
- 1000 GB-hours included
- 60-second max duration
- Custom domains
- Team collaboration

## Support

- **Vercel Docs**: https://vercel.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Your deployment guide**: `VERCEL_DEPLOYMENT.md`

---

## Quick Deploy Commands (Copy & Paste)

```bash
# Login
vercel login

# Set environment variables
vercel env add SUPABASE_URL
vercel env add SUPABASE_ANON_KEY
vercel env add ANTHROPIC_API_KEY
vercel env add AI_GATEWAY_API_KEY

# Deploy to production
cd /Users/noahdeskin/conductor/queryable-slack-2
vercel --prod

# Test
curl $(vercel inspect --url)/api/health

# View logs
vercel logs --follow
```

**That's it! Your API is now live on Vercel! 🎉**
