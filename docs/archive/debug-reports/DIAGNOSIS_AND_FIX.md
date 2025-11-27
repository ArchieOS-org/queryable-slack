# CRITICAL: Error Diagnosis and Fix - "An error occurred while querying the archives"

## Executive Summary

**ROOT CAUSE IDENTIFIED:** Missing `ANTHROPIC_API_KEY` environment variable in production deployment.

**IMPACT:** Complete failure of query functionality in the web UI - users receive error message "An error occurred while querying the archives."

**SEVERITY:** CRITICAL - System is non-functional for end users

**FIX TIME:** 2-5 minutes (environment variable configuration)

---

## Technical Diagnosis

### Error Flow Analysis

Based on comprehensive code analysis and system testing, here's the exact error propagation:

```
User Query (Web UI)
    ↓
POST /api/query (Vercel Serverless Function)
    ↓
Line 234: anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ↓
Line 237-241: if not anthropic_key: return 500 error
    ↓
ERROR: "Anthropic API key not configured"
    ↓
Web UI displays: "An error occurred while querying the archives"
```

### Evidence from Code Review

**File:** `/api/index.py` (Lines 234-241)

```python
anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
ai_gateway_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()

if not anthropic_key:
    self.send_json_response(500, {
        "error": "Anthropic API key not configured"
    })
    return
```

**File:** `.conductor/doha/.env` (Line 3)

```bash
#ANTHROPIC_API_KEY=your_api_key_here  # ← COMMENTED OUT!
```

### Backend Health Status

✅ **VERIFIED WORKING:**
- Supabase connection: HEALTHY
- Database table access: OPERATIONAL (5 sessions found)
- RPC functions deployed: BOTH `match_conductor_sessions` and `match_conductor_sessions_filtered` exist
- Vector search functionality: FUNCTIONAL (test queries return results)
- AI Gateway API key: CONFIGURED (`AI_GATEWAY_API_KEY` present)
- Supabase credentials: CONFIGURED

❌ **FAILED:**
- Anthropic API key: MISSING (commented out in .env)

---

## Step-by-Step Fix Instructions

### Fix 1: Add Anthropic API Key to Workspace Environment

**Location:** `/Users/noahdeskin/conductor/queryable-slack-2/.conductor/doha/.env`

**Current State:**
```bash
#ANTHROPIC_API_KEY=your_api_key_here
```

**Required Action:**
```bash
# Uncomment and replace with actual API key
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Steps:**
1. Get your Anthropic API key from: https://console.anthropic.com/
2. Edit the `.env` file in the workspace directory
3. Uncomment line 3 (remove the `#` symbol)
4. Replace `your_api_key_here` with your actual API key
5. Save the file

**Verification:**
```bash
source .venv/bin/activate
grep ANTHROPIC_API_KEY .env | grep -v "^#"
# Should output: ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

### Fix 2: Configure Production Environment on Vercel

**CRITICAL:** The workspace `.env` file only affects local development. The production deployment requires separate configuration.

**Location:** Vercel Project Settings → Environment Variables

**Steps:**

1. **Navigate to Vercel Dashboard:**
   - Go to: https://vercel.com/nsd97s-projects/queryable-slack
   - Click on "Settings" tab
   - Click on "Environment Variables" in left sidebar

2. **Add ANTHROPIC_API_KEY:**
   ```
   Name: ANTHROPIC_API_KEY
   Value: sk-ant-api03-[your-actual-key]
   Environments: ☑ Production ☑ Preview ☑ Development
   ```

3. **Verify Existing Variables (should already be present):**
   - `AI_GATEWAY_API_KEY`: ✅ Already configured
   - `SUPABASE_URL`: ✅ Already configured
   - `SUPABASE_ANON_KEY`: ✅ Already configured

4. **Save and Redeploy:**
   - Click "Save"
   - Go to "Deployments" tab
   - Click "⋯" on latest deployment → "Redeploy"
   - OR push any commit to trigger automatic redeployment

**Verification after redeployment:**
```bash
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "match_count": 1}'

# Should return JSON with "answer" field, NOT an error about API key
```

---

### Fix 3: Enhanced Error Handling (Optional but Recommended)

To prevent similar silent failures in the future, update the API endpoint with better error reporting.

**File to edit:** `/api/index.py`

**Enhancement 1: Add detailed logging (Lines 234-247)**

Replace:
```python
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

With:
```python
import logging
logger = logging.getLogger(__name__)

if not anthropic_key:
    error_msg = "Anthropic API key not configured - check ANTHROPIC_API_KEY environment variable"
    logger.error(error_msg)
    self.send_json_response(500, {
        "error": "Configuration Error",
        "message": error_msg,
        "fix": "Set ANTHROPIC_API_KEY in Vercel environment variables"
    })
    return

if not ai_gateway_key:
    error_msg = "AI Gateway API key not configured - check AI_GATEWAY_API_KEY environment variable"
    logger.error(error_msg)
    self.send_json_response(500, {
        "error": "Configuration Error",
        "message": error_msg,
        "fix": "Set AI_GATEWAY_API_KEY in Vercel environment variables"
    })
    return
```

**Enhancement 2: Add startup configuration check endpoint**

Add this new endpoint after line 45:

```python
# Configuration check endpoint
elif path == '/api/config-check':
    self.handle_config_check()
    return
```

Add this handler function after line 136:

```python
def handle_config_check(self):
    """Configuration validation endpoint"""
    checks = {
        "anthropic_api_key": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
        "ai_gateway_api_key": bool(os.getenv("AI_GATEWAY_API_KEY", "").strip()),
        "supabase_url": bool(os.getenv("SUPABASE_URL", "").strip()),
        "supabase_anon_key": bool(os.getenv("SUPABASE_ANON_KEY", "").strip())
    }

    all_configured = all(checks.values())
    missing = [k for k, v in checks.items() if not v]

    self.send_json_response(
        200 if all_configured else 503,
        {
            "status": "ready" if all_configured else "misconfigured",
            "checks": checks,
            "missing": missing,
            "message": "All required environment variables configured" if all_configured
                      else f"Missing environment variables: {', '.join(missing)}"
        }
    )
```

**Test the new endpoint:**
```bash
curl https://queryable-slack.vercel.app/api/config-check
```

Expected output after fix:
```json
{
  "status": "ready",
  "checks": {
    "anthropic_api_key": true,
    "ai_gateway_api_key": true,
    "supabase_url": true,
    "supabase_anon_key": true
  },
  "missing": [],
  "message": "All required environment variables configured"
}
```

---

## Verification Checklist

### Pre-Fix Verification (Confirm the Issue)

- [ ] Visit the web UI and attempt a query
- [ ] Observe error: "An error occurred while querying the archives"
- [ ] Check browser DevTools → Network tab → Look for 500 error on `/api/query`
- [ ] Inspect response body for "Anthropic API key not configured"

### Post-Fix Verification (Confirm Resolution)

- [ ] **Local Testing:**
  - [ ] Uncomment `ANTHROPIC_API_KEY` in `.conductor/doha/.env`
  - [ ] Run: `source .venv/bin/activate && python -m conductor.ask "test query"`
  - [ ] Verify it returns a Claude-generated response

- [ ] **Production Testing:**
  - [ ] Add `ANTHROPIC_API_KEY` to Vercel environment variables
  - [ ] Redeploy the application
  - [ ] Visit web UI and submit a test query
  - [ ] Verify you receive an answer (not an error message)
  - [ ] Check DevTools → Network → `/api/query` returns 200 OK
  - [ ] Verify response contains `"answer"` field with text content

- [ ] **Health Check:**
  - [ ] Visit: `https://queryable-slack.vercel.app/api/health`
  - [ ] Verify: `"status": "healthy"` and `"supabase_connected": true`

- [ ] **Configuration Check (if implemented):**
  - [ ] Visit: `https://queryable-slack.vercel.app/api/config-check`
  - [ ] Verify: `"status": "ready"` and all checks are `true`

---

## Additional Debugging Commands

### Check environment variables in workspace:
```bash
cd /Users/noahdeskin/conductor/queryable-slack-2/.conductor/doha
cat .env | grep -v "^#" | grep -v "^$"
```

### Test Supabase connectivity:
```bash
source .venv/bin/activate
python supabase/test_connection.py
```

### Test query endpoint locally (requires all env vars):
```bash
source .venv/bin/activate
python -c "
import os
from conductor.supabase_query import query_vector_similarity
from anthropic import Anthropic
import numpy as np

# Test embedding generation
print('Testing vector search...')
dummy_vec = np.random.random(384).tolist()
results = query_vector_similarity(dummy_vec, match_count=1)
print(f'Vector search: OK ({len(results[\"ids\"][0])} results)')

# Test Claude API
print('Testing Claude API...')
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    print('ERROR: ANTHROPIC_API_KEY not set!')
else:
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=100,
        messages=[{'role': 'user', 'content': 'Say hello'}]
    )
    print(f'Claude API: OK')
"
```

### Test full query pipeline:
```bash
source .venv/bin/activate
python -m conductor.ask "What properties were discussed?"
```

### Check Vercel deployment logs:
```bash
cd /Users/noahdeskin/conductor/queryable-slack-2
vercel logs --follow
# Then trigger a query in the web UI
# Look for error messages related to ANTHROPIC_API_KEY
```

---

## Root Cause Analysis

### Why This Happened

1. **Development vs Production Environment Split:**
   - The `.env` file in `.conductor/doha/` is only used for local development
   - Vercel deployments use environment variables configured in Vercel dashboard
   - The Anthropic API key was never added to Vercel environment variables

2. **Silent Failure Mode:**
   - The API returns a generic 500 error
   - The frontend displays "An error occurred while querying the archives"
   - No clear indication in the UI about what specific configuration is missing

3. **Incomplete Deployment Checklist:**
   - `AI_GATEWAY_API_KEY` was configured in Vercel (from `.env.production`)
   - `SUPABASE_URL` and `SUPABASE_ANON_KEY` were configured in Vercel
   - `ANTHROPIC_API_KEY` was skipped or forgotten during deployment setup

### Prevention Strategies

1. **Add Configuration Check Endpoint** (see Fix 3 above)
2. **Update Deployment Documentation** with complete environment variable checklist
3. **Add Startup Health Check** that fails fast if required env vars are missing
4. **Improve Error Messages** to be more specific about missing configuration
5. **Add Environment Variable Template** to Vercel deployment guide

---

## Quick Reference: Environment Variables Required

| Variable Name | Purpose | Required In | Currently Set? |
|---------------|---------|-------------|----------------|
| `ANTHROPIC_API_KEY` | Claude API for generating answers | Production, Local | ❌ NO (commented out) |
| `AI_GATEWAY_API_KEY` | Vercel AI Gateway for embeddings | Production, Local | ✅ YES |
| `SUPABASE_URL` | Supabase project URL | Production, Local | ✅ YES |
| `SUPABASE_ANON_KEY` | Supabase anonymous API key | Production, Local | ✅ YES |

**Get API Keys:**
- Anthropic: https://console.anthropic.com/
- Vercel AI Gateway: https://vercel.com/dashboard/ai
- Supabase: https://supabase.com/dashboard/project/_/settings/api

---

## Contact and Support

If the issue persists after following these steps:

1. **Check Vercel Deployment Logs:**
   ```bash
   vercel logs --project queryable-slack
   ```

2. **Verify API Key Validity:**
   - Test Anthropic key: https://console.anthropic.com/
   - Regenerate if expired or invalid

3. **Review Full Error Stack:**
   - Open browser DevTools
   - Go to Network tab
   - Trigger the error
   - Inspect the `/api/query` request response body
   - Copy full error message

4. **File an Issue:**
   - Repository: https://github.com/ArchieOS-org/conductor
   - Include: Error message, deployment logs, and configuration checklist results

---

**Status:** READY FOR IMPLEMENTATION
**Priority:** P0 - CRITICAL
**Owner:** Review Board
**Last Updated:** 2025-11-24
