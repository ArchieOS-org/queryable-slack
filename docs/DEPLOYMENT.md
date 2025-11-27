# Deployment Guide

Complete guide for deploying Conductor to Vercel.

## Overview

Conductor deploys as a single monorepo project to Vercel containing:
- **Next.js Frontend**: React app with real-time chat interface
- **Python Serverless Functions**: API endpoints for querying and ingestion
- **Shared Python Package**: `conductor/` package used by API functions

## Prerequisites

- Vercel account (free tier works)
- GitHub repository with your code
- Anthropic API key
- Supabase project with pgvector enabled

## Deployment Architecture

```
Single Vercel Project
├── Next.js App (src/app/)           → Deployed as static + SSR
├── Python API Functions (api/*.py)  → Deployed as serverless functions
└── Shared Python Package (conductor/) → Bundled with API functions
```

**Benefits of single deployment:**
- Same-origin requests (no CORS needed)
- Shared environment variables
- Atomic deployments (frontend + backend together)
- Simpler configuration

## Step-by-Step Deployment

### 1. Prepare Your Repository

Ensure your repository has this structure:

```
queryable-slack-2/
├── src/                    # Next.js frontend
│   ├── app/
│   ├── components/
│   └── lib/
├── api/                    # Python serverless functions
│   ├── index.py
│   ├── chat.py
│   ├── debug.py
│   └── requirements.txt
├── conductor/              # Shared Python package
│   ├── models.py
│   ├── supabase_query.py
│   └── ...
├── public/
├── vercel.json             # Vercel configuration
├── next.config.ts
├── package.json
└── tsconfig.json
```

### 2. Configure Vercel

The `vercel.json` should look like this:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "buildCommand": "pnpm build",
  "installCommand": "pnpm install",
  "functions": {
    "api/**/*.py": {
      "runtime": "python3.11",
      "memory": 1024,
      "maxDuration": 60,
      "includeFiles": "conductor/**"
    }
  },
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "/api/:path*"
    }
  ]
}
```

**Key configuration:**
- `framework`: "nextjs" - Vercel auto-detects Next.js
- `includeFiles`: "conductor/**" - Bundles shared package with API functions
- `runtime`: "python3.11" - Python version for serverless functions
- `maxDuration`: 60 - Max execution time (60s on Pro plan, 10s on free tier)

### 3. Push to GitHub

```bash
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### 4. Import Project to Vercel

1. Go to https://vercel.com/
2. Sign in with GitHub
3. Click "Add New Project"
4. Import your repository
5. Vercel will auto-detect Next.js configuration

**Project Settings:**
- **Framework Preset**: Next.js (auto-detected)
- **Root Directory**: Leave as `.` (root)
- **Build Command**: `pnpm build` (auto-detected)
- **Output Directory**: `.next` (auto-detected)
- **Install Command**: `pnpm install` (auto-detected)

### 5. Configure Environment Variables

In Vercel dashboard → Settings → Environment Variables, add:

**Required:**
```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJh...
```

**Optional (for debugging):**
```
LOG_LEVEL=INFO
DEBUG=false
```

**Important:**
- Set environment variables for **all environments** (Production, Preview, Development)
- Never commit API keys to git

### 6. Deploy

Click "Deploy" in Vercel dashboard. Deployment process:

1. **Install Dependencies**: Vercel runs `pnpm install`
2. **Build Next.js**: Runs `pnpm build`
3. **Deploy Functions**: Builds Python functions with `conductor/` package
4. **Deploy Static Assets**: Uploads public/ and .next/ files
5. **Assign Domain**: Your app is live at `your-project.vercel.app`

**Deployment time:** 2-3 minutes typically

### 7. Verify Deployment

Test these endpoints:

1. **Frontend**: https://your-project.vercel.app/
   - Should show chat interface
   - Check browser console for errors

2. **Health Check**: https://your-project.vercel.app/api/debug
   - Should return status and configuration

3. **Query API**: https://your-project.vercel.app/api/index
   ```bash
   curl -X POST https://your-project.vercel.app/api/index \
     -H "Content-Type: application/json" \
     -d '{"query": "test"}'
   ```
   - Should return results from Supabase

## Continuous Deployment

Vercel automatically deploys on git push:

- **Push to `main`**: Deploys to production
- **Push to other branches**: Deploys to preview URLs
- **Pull Requests**: Creates preview deployments

**Preview deployments:**
- Each PR gets unique URL: `your-project-git-branch.vercel.app`
- Test changes before merging to main
- Automatically deleted when PR is closed

## Custom Domain (Optional)

To use a custom domain:

1. Go to Vercel dashboard → Settings → Domains
2. Add your domain (e.g., `conductor.yourdomain.com`)
3. Update DNS records as instructed by Vercel
4. SSL certificate is automatically provisioned

## Monitoring & Logs

### View Logs

**Real-time logs:**
```bash
vercel logs --follow
```

**Specific deployment:**
```bash
vercel logs <deployment-url>
```

**Via Dashboard:**
- Go to Vercel dashboard → Deployments
- Click on a deployment
- View logs in "Function Logs" tab

### Common Log Locations

- **Next.js Build**: Build-time logs
- **API Functions**: Runtime logs for Python endpoints
- **Edge Network**: Request routing logs

### Debugging Failed Deployments

If deployment fails:

1. **Check build logs** in Vercel dashboard
2. **Common issues**:
   - Missing dependencies in `api/requirements.txt`
   - Import errors (check `includeFiles` in `vercel.json`)
   - Environment variables not set
   - Python version incompatibility

3. **Test locally first**:
   ```bash
   vercel dev
   ```
   This runs the same environment locally

## Performance Optimization

### Cold Starts

Python functions have cold start latency (~1-3 seconds):

**Mitigation strategies:**
1. Keep dependencies minimal in `api/requirements.txt`
2. Use function-level caching where possible
3. Consider upgrading to Pro plan for lower latency
4. Optimize imports (lazy load heavy modules)

### Caching

Configure caching in `vercel.json`:

```json
{
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "s-maxage=60, stale-while-revalidate"
        }
      ]
    }
  ]
}
```

### Function Regions

Deploy to regions close to your users:

```json
{
  "functions": {
    "api/**/*.py": {
      "regions": ["sfo1", "iad1"]
    }
  }
}
```

## Troubleshooting

### Deployment Fails with "Function Too Large"

**Problem:** API function exceeds size limit (50MB)

**Solution:**
1. Reduce dependencies in `api/requirements.txt`
2. Remove unused imports
3. Use lighter alternatives (e.g., `httpx` instead of `requests`)

### Import Errors in API Functions

**Problem:** `ModuleNotFoundError: No module named 'conductor'`

**Solution:**
- Verify `includeFiles: "conductor/**"` in `vercel.json`
- Check that `conductor/` package has `__init__.py`
- Test locally with `vercel dev`

### Environment Variables Not Working

**Problem:** API returns "environment variable not set"

**Solution:**
1. Verify variables are set in Vercel dashboard
2. Check they're enabled for correct environment (Production/Preview/Development)
3. Redeploy after adding new variables

### CORS Errors

**Problem:** Frontend can't call API endpoints

**Solution:**
- Since frontend and API are same domain, CORS shouldn't be needed
- If using custom domain, ensure both use same domain
- Check that API routes are under `/api/` path

### Supabase Connection Timeout

**Problem:** API functions timeout when querying Supabase

**Solution:**
1. Increase `maxDuration` in `vercel.json` (requires Pro plan for >10s)
2. Optimize Supabase queries (add indexes)
3. Check Supabase connection pooling settings

## Security Best Practices

1. **Never commit secrets** to git
   - Use `.env.local` for local development
   - Set environment variables in Vercel dashboard

2. **Use environment-specific keys**
   - Different API keys for production vs preview
   - Rotate keys regularly

3. **Enable rate limiting**
   ```typescript
   // In API route
   import { Ratelimit } from "@upstash/ratelimit";
   ```

4. **Validate all inputs**
   - Use Pydantic models in Python API
   - Validate in Next.js API routes

## Cost Considerations

**Free Tier Limits:**
- 100 GB bandwidth/month
- 100 hours serverless function execution/month
- 10-second function timeout
- 6,000 build minutes/month

**When to upgrade to Pro:**
- Need >10s function timeout (for large queries)
- Need custom domains
- Need team collaboration
- Need faster builds

## Rollback Procedure

If a deployment breaks production:

1. **Via Dashboard:**
   - Go to Deployments
   - Find last working deployment
   - Click "Promote to Production"

2. **Via CLI:**
   ```bash
   vercel rollback
   ```

3. **Via Git:**
   ```bash
   git revert HEAD
   git push origin main
   ```

## CI/CD Integration

For advanced workflows, integrate with GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Vercel
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
```

## Additional Resources

- **Vercel Docs**: https://vercel.com/docs
- **Next.js Deployment**: https://nextjs.org/docs/deployment
- **Python Functions**: https://vercel.com/docs/functions/serverless-functions/runtimes/python
- **Vercel CLI**: https://vercel.com/docs/cli

## Support

If you encounter deployment issues:

1. Check Vercel dashboard logs
2. Test locally with `vercel dev`
3. Review [troubleshooting section](#troubleshooting)
4. Contact Vercel support (Pro plan)
