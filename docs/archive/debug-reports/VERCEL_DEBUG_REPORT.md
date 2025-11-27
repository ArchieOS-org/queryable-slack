# Vercel Deployment Diagnostic & Debugging Guide

## Critical Issue: 500 Error from `/api/query` Endpoint

### Current Deployment Configuration

**Location:** `/Users/noahdeskin/conductor/queryable-slack-2/frontend/`

**Python API Structure:**
```
frontend/
├── api/
│   ├── index.py          # Main API with /api/query endpoint
│   ├── hello.py          # Simple test endpoint
│   ├── test.py
│   ├── debug.py          # NEW: Diagnostic endpoint (created by this report)
│   └── requirements.txt  # Python dependencies
├── conductor/
│   ├── supabase_query.py # Vector search integration
│   └── [other modules]
└── vercel.json           # Vercel configuration
```

**vercel.json Configuration:**
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "functions": {
    "api/**/*.py": {
      "memory": 1024,
      "maxDuration": 60,
      "includeFiles": "conductor/**"
    }
  }
}
```

---

## Step 1: View Production Logs (URGENT)

### CLI Commands to Get Real-Time Logs

```bash
# Option 1: Stream logs in real-time (recommended)
vercel logs --follow

# Option 2: Get logs for specific deployment
vercel logs <deployment-url> --follow

# Option 3: Get recent logs without streaming
vercel logs

# Option 4: Stream with more context
vercel logs --output=combined
```

### How to Use These Commands

1. **Install/Update Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel@latest
   # or
   pnpm i -g vercel@latest
   ```

2. **Navigate to project directory**:
   ```bash
   cd /Users/noahdeskin/conductor/queryable-slack-2/frontend
   ```

3. **Link project to Vercel** (if not already linked):
   ```bash
   vercel link
   ```

4. **Start streaming logs**:
   ```bash
   vercel logs --follow
   ```

5. **In another terminal, trigger the error**:
   - Make a request to `/api/query` endpoint
   - Watch the logs in real-time to see the exact error

---

## Step 2: Use Diagnostic Endpoint

### Access the Debug Endpoint

A diagnostic endpoint has been created at `/frontend/api/debug.py`. After deployment, access it at:

```
https://your-deployment-url.vercel.app/api/debug
```

### What the Debug Endpoint Checks

1. **Environment Variables**:
   - Confirms if `ANTHROPIC_API_KEY` is set (shows "SET" or "MISSING")
   - Confirms if `AI_GATEWAY_API_KEY` is set
   - Confirms if `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
   - Shows actual length of each variable (to catch truncation)
   - Shows first 8 characters of ANTHROPIC_API_KEY (for verification)

2. **Python Environment**:
   - Python version
   - Python executable path
   - sys.path contents

3. **Module Imports**:
   - Tests if `anthropic`, `openai`, `supabase` can be imported
   - Tests if `conductor.supabase_query` can be imported
   - Tests other required dependencies

4. **File System**:
   - Shows current directory structure
   - Lists files in `conductor/` directory
   - Confirms `includeFiles` is working

### Expected Output

```json
{
  "python_info": {...},
  "environment_variables": {
    "ANTHROPIC_API_KEY": "SET",  // Should be "SET", not "MISSING"
    "AI_GATEWAY_API_KEY": "SET",
    "SUPABASE_URL": "SET",
    "SUPABASE_ANON_KEY": "SET",
    "VERCEL": "1",
    "VERCEL_ENV": "production"
  },
  "environment_variable_lengths": {
    "ANTHROPIC_API_KEY_length": 108,  // Should be ~100+ characters
    "AI_GATEWAY_API_KEY_length": 50   // Typical length
  },
  "importable_modules": {
    "anthropic": "SUCCESS",  // All should say "SUCCESS"
    "openai": "SUCCESS",
    "supabase": "SUCCESS",
    "conductor.supabase_query": "SUCCESS"
  },
  "conductor_files": [
    "supabase_query.py",
    "models.py",
    ...
  ]
}
```

---

## Step 3: Verify Environment Variables in Production

### Common Issue: Environment Variables Not Persisting

**Problem:** Adding environment variables via Vercel dashboard doesn't automatically apply to existing deployments.

### Solution: Force Redeploy After Adding Variables

```bash
# Navigate to project
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend

# Option 1: Trigger new deployment with current commit
vercel --prod

# Option 2: Redeploy existing deployment (RECOMMENDED)
vercel redeploy <deployment-url> --target=production

# Option 3: Force rebuild from scratch (clears cache)
vercel --prod --force
```

### Verify Variables Are Set

```bash
# Check environment variables for your project
vercel env ls

# Pull environment variables to local (for verification)
vercel env pull .env.vercel
cat .env.vercel
```

---

## Step 4: Cache Invalidation & Clean Rebuild

### When to Invalidate Cache

Environment variables are **build-time** and **runtime** values. If you added `ANTHROPIC_API_KEY` after initial deployment:

1. The build cache may not include it
2. The runtime environment may not have been refreshed

### Force Clean Rebuild

```bash
# Clear build cache and force rebuild
vercel --prod --force

# Alternative: Redeploy with build logs
vercel deploy --prod --logs
```

### Check for Build-Time vs Runtime Issues

**Build-time variables** (used during `poetry install`, `pip install`):
- Set via Vercel dashboard → Environment Variables → "Production"

**Runtime variables** (used by Python functions at request time):
- Same location, but Vercel must restart functions

**Key Point:** After adding environment variables, you MUST redeploy or trigger a new build.

---

## Step 5: Debugging Specific to Your Setup

### Current Code Analysis: `/frontend/api/index.py`

**Lines 242-255 (Error Handling):**
```python
anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
ai_gateway_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()

if not anthropic_key:
    self.send_json_response(500, {
        "error": "Anthropic API key not configured"
    })
    return

if not ai_gateway_key:
    self.send_json_response(500, {
        "error": "AI Gateway API key not configured"
    })
    return
```

### Likely Cause of 500 Error

Based on the code, the 500 error is likely one of:

1. **"Anthropic API key not configured"** - `ANTHROPIC_API_KEY` environment variable is missing or empty
2. **"AI Gateway API key not configured"** - `AI_GATEWAY_API_KEY` is missing
3. **Import error** - `from conductor.supabase_query import query_vector_similarity` fails
4. **Import error** - `from anthropic import Anthropic` fails (package not installed)

### Quick Test Commands

```bash
# Test the API locally before deploying
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend
vercel dev

# In another terminal, test the endpoint
curl -X POST http://localhost:3000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "match_count": 5}'
```

---

## Step 6: Common Vercel Python Issues & Solutions

### Issue 1: Environment Variables Not Available at Runtime

**Symptom:** Debug endpoint shows `ANTHROPIC_API_KEY: "MISSING"`

**Solution:**
```bash
# 1. Add variable via CLI (most reliable)
vercel env add ANTHROPIC_API_KEY production

# 2. Paste your API key when prompted

# 3. Redeploy
vercel --prod --force
```

### Issue 2: Module Import Failures

**Symptom:** Debug endpoint shows `"anthropic": "FAILED: No module named 'anthropic'"`

**Solution:**
```bash
# Check requirements.txt is in correct location
cat /Users/noahdeskin/conductor/queryable-slack-2/frontend/api/requirements.txt

# Ensure it contains:
# anthropic>=0.39.0
# openai>=1.0.0
# supabase>=2.10.0

# Redeploy to trigger pip install
vercel --prod --force
```

### Issue 3: Conductor Module Not Found

**Symptom:** `"conductor.supabase_query": "FAILED: No module named 'conductor'"`

**Cause:** `includeFiles` in `vercel.json` not working

**Solution:**
```json
// vercel.json - ensure this is correct
{
  "functions": {
    "api/**/*.py": {
      "memory": 1024,
      "maxDuration": 60,
      "includeFiles": "conductor/**"  // This makes conductor/ available
    }
  }
}
```

Then redeploy:
```bash
vercel --prod --force
```

---

## Step 7: Complete Diagnostic Workflow

### Execute This Sequence

```bash
# 1. Navigate to frontend directory
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend

# 2. Verify environment variables are set
vercel env ls

# If ANTHROPIC_API_KEY is missing:
vercel env add ANTHROPIC_API_KEY production
# Paste key: sk-ant-api03-...

# 3. Deploy with force rebuild
vercel --prod --force --logs

# 4. Get deployment URL from output
# Example: https://queryable-slack-abc123.vercel.app

# 5. Test debug endpoint
curl https://your-deployment-url.vercel.app/api/debug

# 6. Check logs in real-time
vercel logs --follow

# 7. Test the actual query endpoint
curl -X POST https://your-deployment-url.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "match_count": 5}'

# 8. Watch logs for errors
```

---

## Step 8: Vercel Dashboard Debugging

### Check Deployment Status

1. Visit: https://vercel.com/dashboard
2. Select your project
3. Go to **Deployments** tab
4. Click on latest deployment
5. View:
   - **Build Logs** - Check for dependency installation errors
   - **Runtime Logs** - Check for function execution errors
   - **Environment Variables** - Verify they're set for Production

### Check Function Configuration

1. Go to **Settings** → **Functions**
2. Verify:
   - Python runtime is detected
   - Memory is set to 1024 MB (from vercel.json)
   - Timeout is 60s (from vercel.json)

---

## Summary: Most Likely Issues & Fixes

### Issue 1: Environment Variable Not Set (80% probability)

**Fix:**
```bash
vercel env add ANTHROPIC_API_KEY production
vercel env add AI_GATEWAY_API_KEY production
vercel --prod --force
```

### Issue 2: Need to Redeploy After Adding Variables (15% probability)

**Fix:**
```bash
vercel redeploy <deployment-url> --target=production
```

### Issue 3: Import Error - Dependencies Not Installed (5% probability)

**Fix:**
```bash
# Ensure requirements.txt is at /frontend/api/requirements.txt
# Redeploy
vercel --prod --force
```

---

## Quick Reference: Essential Commands

```bash
# View real-time logs
vercel logs --follow

# Add environment variable
vercel env add <KEY> production

# Force rebuild and deploy
vercel --prod --force

# Check environment variables
vercel env ls

# Redeploy existing deployment
vercel redeploy <url> --target=production

# Test locally
vercel dev

# Pull environment variables
vercel env pull .env.vercel
```

---

## Next Steps

1. **URGENT:** Run `vercel logs --follow` to see exact error
2. Access `/api/debug` endpoint to verify environment
3. If environment variables are missing, add them via CLI
4. Force redeploy with `vercel --prod --force`
5. Test again and monitor logs

---

## Additional Resources

- **Vercel Python Runtime Docs:** https://vercel.com/docs/functions/runtimes/python
- **Vercel CLI Reference:** https://vercel.com/docs/cli
- **Vercel Environment Variables:** https://vercel.com/docs/environment-variables
- **Vercel Logs API:** https://vercel.com/docs/rest-api/reference/endpoints/logs

---

## Diagnostic Endpoint Code

The complete diagnostic endpoint is at:
`/Users/noahdeskin/conductor/queryable-slack-2/frontend/api/debug.py`

Deploy it with:
```bash
vercel --prod
```

Access at:
```
https://your-deployment-url.vercel.app/api/debug
```

