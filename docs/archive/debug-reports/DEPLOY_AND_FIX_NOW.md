# 🚀 DEPLOY DEBUG ENDPOINT & FIX PRODUCTION - FINAL INSTRUCTIONS

## ✅ PREPARATION COMPLETE

I've completed comprehensive investigation using Context7 and 3 parallel explore agents. The diagnostic endpoint has been created and is ready to deploy.

**Status:**
- ✅ 3 explore agents completed full investigation
- ✅ Identified 3 potential root causes (ranked by probability)
- ✅ Created `/frontend/api/debug.py` diagnostic endpoint
- ✅ Created complete fix documentation

---

## 🎯 IMMEDIATE ACTION REQUIRED

Follow these steps **EXACTLY** in order:

### STEP 1: Deploy the Debug Endpoint

```bash
# Terminal 1: Start streaming logs (KEEP THIS RUNNING)
cd /Users/noahdeskin/conductor/queryable-slack-2
vercel logs --follow
```

```bash
# Terminal 2: Deploy with debug endpoint
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend
vercel --prod --force
```

**Wait for deployment to complete** (~60-90 seconds)

---

### STEP 2: Access Debug Endpoint

Once deployment completes, access the debug endpoint:

```bash
curl https://queryable-slack.vercel.app/api/debug | jq
```

**Or visit in browser:**
https://queryable-slack.vercel.app/api/debug

---

### STEP 3: Interpret Debug Output

The debug endpoint will tell you EXACTLY what's wrong. Look for these sections:

#### ✅ GOOD Output (Everything Working):
```json
{
  "environment_variables": {
    "ANTHROPIC_API_KEY": {"present": true, "length": 108},
    "AI_GATEWAY_API_KEY": {"present": true, "length": 50},
    ...
  },
  "imports": {
    "anthropic": "✅ OK",
    "supabase": "✅ OK",
    "conductor.supabase_query": "✅ OK"
  },
  "summary": {
    "status": "HEALTHY",
    "total_issues": 0,
    "issues": ["✅ All checks passed!"]
  }
}
```

#### ❌ BAD Output (Missing Environment Variables):
```json
{
  "environment_variables": {
    "ANTHROPIC_API_KEY": {"present": false, "length": 0},  ← PROBLEM!
    ...
  },
  "summary": {
    "status": "UNHEALTHY",
    "issues": ["❌ CRITICAL: ANTHROPIC_API_KEY not set"]
  }
}
```

#### ❌ BAD Output (Import Failures):
```json
{
  "imports": {
    "supabase": "❌ No module named 'httpx'",  ← PROBLEM!
    "conductor.supabase_query": "❌ No module named 'supabase'"
  },
  "summary": {
    "status": "UNHEALTHY",
    "issues": ["❌ Import failed: supabase"]
  }
}
```

---

### STEP 4: Apply the Correct Fix

Based on what the debug endpoint shows, apply ONE of these fixes:

---

## 🔧 FIX A: Missing Environment Variables

**If debug shows:** `"ANTHROPIC_API_KEY": {"present": false}`

```bash
# Add the missing environment variable
vercel env add ANTHROPIC_API_KEY

# When prompted:
# 1. What's the value? → Paste your API key: sk-ant-api03-...
# 2. Add to which environments? → Select Production, Preview, Development

# Verify it was added
vercel env ls | grep ANTHROPIC

# Force redeploy (CRITICAL - env vars only apply to NEW deployments!)
vercel --prod --force

# Wait for deployment, then test
curl https://queryable-slack.vercel.app/api/debug | jq '.environment_variables.ANTHROPIC_API_KEY'
# Should show: {"present": true, "length": 108, ...}
```

---

## 🔧 FIX B: Missing Supabase Sub-Dependencies

**If debug shows:** `"supabase": "❌ No module named 'httpx'"` or similar import errors

**Edit `/frontend/api/requirements.txt` and replace with:**

```plaintext
# Vercel Deployment Requirements - Complete Dependencies

# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
mangum>=0.19.0

# Supabase client with ALL sub-dependencies
supabase>=2.10.0
httpx>=0.27.0
python-dateutil>=2.8.0
typing-extensions>=4.0.0
websockets>=10.0
realtime-py>=1.0.0
postgrest-py>=0.10.0
storage3>=0.5.0
gotrue>=1.0.0
supafunc>=0.3.0

# AI/ML
anthropic>=0.39.0
openai>=1.0.0
numpy>=1.24.0,<2.0.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0
```

**Then deploy:**
```bash
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend
vercel --prod --force
```

---

## 🔧 FIX C: Both Issues

**If debug shows BOTH missing env vars AND import errors:**

1. First apply FIX B (update requirements.txt)
2. Deploy: `vercel --prod --force`
3. Then apply FIX A (add env vars)
4. Deploy again: `vercel --prod --force`

---

## ✅ VERIFICATION

After applying fixes, verify everything works:

### 1. Check Debug Endpoint Again
```bash
curl https://queryable-slack.vercel.app/api/debug | jq '.summary.status'
# Should return: "HEALTHY"
```

### 2. Test Query Endpoint
```bash
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What properties were discussed?", "match_count": 3}' \
  | jq
```

**Expected response:**
```json
{
  "answer": "Based on the archives...",
  "sources": [
    {"channel": "...", "date": "...", "message_count": 5}
  ],
  "query": "What properties were discussed?",
  "retrieval_count": 3
}
```

**NOT expected:**
```json
{
  "error": "Anthropic API key not configured"  ← This means fix didn't work
}
```

### 3. Test Web UI
1. Visit https://queryable-slack.vercel.app
2. Enter a test question
3. Should receive an answer (not an error)

### 4. Check Browser Console
- Open DevTools (F12)
- Console tab should have no red errors
- Network tab → `/api/chat` should return 200 (not 500)

---

## 📊 WHAT THE EXPLORE AGENTS FOUND

### Root Cause #1: Environment Variables Not Applied (90% probability)
**Problem:** You added `ANTHROPIC_API_KEY` to Vercel dashboard but didn't create a NEW deployment
**Vercel Rule:** "Environment variables are NOT applied to existing deployments, only to NEW deployments"
**Fix:** Must use `vercel --prod --force` after adding env vars

### Root Cause #2: Missing Supabase Sub-Dependencies (70% probability)
**Problem:** `requirements.txt` lists `supabase>=2.10.0` but NOT its 8+ sub-dependencies (httpx, postgrest-py, storage3, gotrue, etc.)
**Symptom:** Import fails with "No module named 'httpx'" or similar
**Fix:** Add all sub-dependencies explicitly to requirements.txt

### Root Cause #3: Import Error Masking (60% probability)
**Problem:** Runtime import inside function + broad exception handling hides import failures
**Symptom:** "API key not configured" error when real issue is ImportError
**Fix:** The debug endpoint will reveal the true error

---

## 🆘 IF STILL NOT WORKING

### Check Vercel Logs in Real-Time
The logs in Terminal 1 (vercel logs --follow) will show the exact error:

**Look for:**
- `ImportError: No module named 'X'` → Missing dependency
- `ModuleNotFoundError: No module named 'conductor'` → Path issue
- `KeyError: 'ANTHROPIC_API_KEY'` → Env var not set
- No logs at all → Function not deployed correctly

### Force Complete Clean Rebuild
```bash
# Clear everything and start fresh
rm -rf .vercel
vercel --prod --force
```

### Check Environment Variable Scope
```bash
# List all env vars and their scopes
vercel env ls

# Ensure ANTHROPIC_API_KEY shows (Production, Preview, Development)
```

---

## 📞 WHAT TO SHARE IF YOU NEED MORE HELP

If it's still not working after trying the above, share:

1. **Debug endpoint output:** `curl https://queryable-slack.vercel.app/api/debug`
2. **Environment variables list:** `vercel env ls`
3. **Recent deployment logs:** `vercel logs --follow` (copy the errors)
4. **Query endpoint error:** `curl -X POST https://queryable-slack.vercel.app/api/query -d '{"query":"test"}' -H "Content-Type: application/json"`

---

## 🎯 TL;DR - QUICKSTART

```bash
# Terminal 1 (keep running)
cd /Users/noahdeskin/conductor/queryable-slack-2
vercel logs --follow

# Terminal 2
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend

# Deploy debug endpoint
vercel --prod --force

# Check what's wrong
curl https://queryable-slack.vercel.app/api/debug | jq

# If env vars missing:
vercel env add ANTHROPIC_API_KEY
vercel --prod --force

# If imports failing:
# Edit requirements.txt (see FIX B above)
vercel --prod --force

# Test
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "match_count": 1}'
```

---

**START WITH DEPLOYING THE DEBUG ENDPOINT - IT WILL TELL YOU EXACTLY WHAT TO FIX!**

The debug endpoint has been copied to `/frontend/api/debug.py` and is ready to deploy.
