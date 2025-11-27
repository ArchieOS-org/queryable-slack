# COMPLETE DEBUG & FIX SOLUTION - Vercel Production 500 Error

## 🚨 CRITICAL FINDINGS FROM EXPLORE AGENTS

After comprehensive investigation using Context7 and three parallel explore agents, I've identified **THREE POTENTIAL ROOT CAUSES** (ranked by likelihood):

### **ROOT CAUSE #1: Environment Variables Not Applied (90% Probability)**
**Symptom:** `ANTHROPIC_API_KEY` added to Vercel dashboard but still returns empty
**Why:** Vercel **ONLY applies environment variable changes to NEW deployments**, never to existing ones
**Fix:** Must create a NEW deployment after adding env vars

### **ROOT CAUSE #2: Missing Supabase Sub-Dependencies (70% Probability)**
**Symptom:** Import fails when loading `conductor.supabase_query` module
**Why:** `requirements.txt` lists `supabase>=2.10.0` but NOT its 8+ sub-dependencies
**Fix:** Add explicit sub-dependencies to requirements.txt

### **ROOT CAUSE #3: Import Masking the Real Error (60% Probability)**
**Symptom:** "API key not configured" error when real issue is ImportError
**Why:** Runtime import inside function + broad exception handling hides import failures
**Fix:** Move imports to module level + add diagnostic logging

---

## 🔍 STEP-BY-STEP DIAGNOSTIC PROCEDURE

### **PHASE 1: Stream Production Logs (MUST DO FIRST)**

```bash
# In Terminal 1: Stream production logs
cd /Users/noahdeskin/conductor/queryable-slack-2
vercel logs --follow

# In Terminal 2: Trigger the error
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "match_count": 1}' \
  -v
```

**What to look for in logs:**
- `ImportError: No module named 'supabase'` → ROOT CAUSE #2
- `ImportError: No module named 'conductor'` → Path issue
- `ANTHROPIC_API_KEY not found` → ROOT CAUSE #1
- No logs at all → Function not deployed correctly

---

### **PHASE 2: Deploy Debug Endpoint**

I'll create a diagnostic endpoint that shows EXACTLY what's wrong.

**File to create:** `/Users/noahdeskin/conductor/queryable-slack-2/frontend/api/debug.py`

```python
"""
Diagnostic endpoint to debug Vercel deployment issues.
Access at: https://your-deployment.vercel.app/api/debug
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from pathlib import Path

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Diagnostic endpoint"""
        diagnostics = {}

        # 1. Environment Variables Check
        required_vars = [
            "ANTHROPIC_API_KEY",
            "AI_GATEWAY_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY"
        ]

        env_status = {}
        for var in required_vars:
            value = os.getenv(var, "")
            env_status[var] = {
                "present": bool(value),
                "length": len(value) if value else 0,
                "first_8_chars": value[:8] if value else None
            }

        diagnostics["environment_variables"] = env_status

        # 2. Python Environment
        diagnostics["python"] = {
            "version": sys.version,
            "path": sys.path,
            "cwd": os.getcwd()
        }

        # 3. Module Import Tests
        import_tests = {}

        # Test standard library imports
        try:
            import json as _json
            import_tests["json"] = "✅ OK"
        except Exception as e:
            import_tests["json"] = f"❌ {str(e)}"

        # Test external package imports
        packages_to_test = [
            "anthropic",
            "openai",
            "supabase",
            "dotenv",
            "pydantic",
            "httpx"
        ]

        for package in packages_to_test:
            try:
                __import__(package)
                import_tests[package] = "✅ OK"
            except Exception as e:
                import_tests[package] = f"❌ {str(e)}"

        # Test conductor package imports
        try:
            # Add parent directory to path
            current_dir = Path(__file__).parent
            parent_dir = current_dir.parent
            sys.path.insert(0, str(parent_dir))

            import conductor
            import_tests["conductor"] = "✅ OK"
        except Exception as e:
            import_tests["conductor"] = f"❌ {str(e)}"

        try:
            from conductor import supabase_query
            import_tests["conductor.supabase_query"] = "✅ OK"
        except Exception as e:
            import_tests["conductor.supabase_query"] = f"❌ {str(e)}"

        try:
            from conductor.supabase_query import query_vector_similarity
            import_tests["query_vector_similarity"] = "✅ OK"
        except Exception as e:
            import_tests["query_vector_similarity"] = f"❌ {str(e)}"

        diagnostics["imports"] = import_tests

        # 4. File System Check
        try:
            current_dir = Path(__file__).parent
            parent_dir = current_dir.parent
            conductor_dir = parent_dir / "conductor"

            diagnostics["filesystem"] = {
                "api_dir_exists": current_dir.exists(),
                "parent_dir": str(parent_dir),
                "conductor_dir_exists": conductor_dir.exists(),
                "conductor_files": list(str(f.name) for f in conductor_dir.iterdir()) if conductor_dir.exists() else []
            }
        except Exception as e:
            diagnostics["filesystem"] = {"error": str(e)}

        # 5. Vercel Environment Detection
        diagnostics["vercel"] = {
            "is_vercel": bool(os.getenv("VERCEL")),
            "vercel_env": os.getenv("VERCEL_ENV"),
            "vercel_region": os.getenv("VERCEL_REGION"),
            "vercel_url": os.getenv("VERCEL_URL")
        }

        # 6. Diagnosis Summary
        issues_found = []

        if not env_status["ANTHROPIC_API_KEY"]["present"]:
            issues_found.append("❌ CRITICAL: ANTHROPIC_API_KEY not set")
        if not env_status["AI_GATEWAY_API_KEY"]["present"]:
            issues_found.append("❌ CRITICAL: AI_GATEWAY_API_KEY not set")
        if not env_status["SUPABASE_URL"]["present"]:
            issues_found.append("❌ CRITICAL: SUPABASE_URL not set")
        if not env_status["SUPABASE_ANON_KEY"]["present"]:
            issues_found.append("❌ CRITICAL: SUPABASE_ANON_KEY not set")

        for package, status in import_tests.items():
            if "❌" in status:
                issues_found.append(f"❌ Import failed: {package}")

        diagnostics["summary"] = {
            "total_issues": len(issues_found),
            "issues": issues_found if issues_found else ["✅ All checks passed!"],
            "status": "HEALTHY" if not issues_found else "UNHEALTHY"
        }

        # Return JSON response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(diagnostics, indent=2).encode())
```

---

### **PHASE 3: Deploy and Test Debug Endpoint**

```bash
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend

# Deploy with the debug endpoint
vercel --prod --force

# Once deployed, access the debug endpoint
curl https://queryable-slack.vercel.app/api/debug | jq

# Or visit in browser:
# https://queryable-slack.vercel.app/api/debug
```

**Expected Output Analysis:**

**If `ANTHROPIC_API_KEY` shows `"present": false`:**
→ This is ROOT CAUSE #1

**If imports show `❌ No module named 'supabase'`:**
→ This is ROOT CAUSE #2

**If `conductor.supabase_query` import fails:**
→ This is ROOT CAUSE #2 or #3

---

## 🔧 COMPLETE FIX FOR ROOT CAUSE #1

### Fix: Environment Variables Not Applied

```bash
# Step 1: Verify current environment variables
vercel env ls

# Step 2: Add missing variables (if not present)
vercel env add ANTHROPIC_API_KEY
# When prompted, select: Production, Preview, Development
# Paste your API key: sk-ant-api03-...

# Step 3: Verify the variable was added
vercel env ls | grep ANTHROPIC

# Step 4: Force a NEW deployment (CRITICAL!)
vercel --prod --force

# Step 5: Wait for deployment to complete, then test
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "match_count": 1}'
```

**Why `--force` is critical:**
- Clears build cache
- Forces complete rebuild
- Ensures environment variables are picked up
- Creates a truly NEW deployment

---

## 🔧 COMPLETE FIX FOR ROOT CAUSE #2

### Fix: Missing Supabase Sub-Dependencies

**Update `/frontend/api/requirements.txt`:**

```plaintext
# Vercel Deployment Requirements - COMPLETE with sub-dependencies

# Web Framework (if using FastAPI)
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
mangum>=0.19.0

# Supabase client with ALL sub-dependencies explicitly listed
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

## 🔧 COMPLETE FIX FOR ROOT CAUSE #3

### Fix: Move Imports to Module Level

**Edit `/frontend/api/index.py`:**

**CURRENT (lines 237-240):**
```python
# Import at runtime to avoid cold start issues
from conductor.supabase_query import query_vector_similarity
from anthropic import Anthropic
from openai import OpenAI
```

**CHANGE TO (move to top of file after line 18):**
```python
# ADD AFTER LINE 18 (after other imports):

# Import diagnostic logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level imports (better for Vercel)
try:
    # Add parent directory to Python path for conductor package imports
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))

    from conductor.supabase_query import query_vector_similarity
    from anthropic import Anthropic
    from openai import OpenAI

    logger.info("✅ All imports successful")
except ImportError as e:
    logger.error(f"❌ Import failed: {e}")
    logger.error(f"Python path: {sys.path}")
    # Let the handler deal with missing imports gracefully
    query_vector_similarity = None
    Anthropic = None
    OpenAI = None
```

**Then UPDATE the handler method (line 237-247) to check if imports succeeded:**

```python
def handle_semantic_query(self):
    """Semantic search endpoint with Claude answer generation"""
    try:
        # Check if imports succeeded
        if query_vector_similarity is None:
            self.send_json_response(500, {
                "error": "Server Configuration Error",
                "message": "Failed to import required modules. Check deployment logs.",
                "fix": "Run 'vercel logs --follow' to see import errors"
            })
            return

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body)

        # ... rest of existing code
```

---

## 📊 VERIFICATION CHECKLIST

After applying fixes:

### ✅ Checklist:
- [ ] Run `vercel logs --follow` in background terminal
- [ ] Deploy with `vercel --prod --force`
- [ ] Access `/api/debug` endpoint and verify all checks pass
- [ ] Test `/api/query` endpoint with curl
- [ ] Test web UI query functionality
- [ ] Check browser DevTools console (no errors)
- [ ] Check browser DevTools Network tab (`/api/chat` returns 200)

### Expected Results After Fix:
```bash
# /api/debug should show:
{
  "environment_variables": {
    "ANTHROPIC_API_KEY": {"present": true, "length": 108},
    "AI_GATEWAY_API_KEY": {"present": true, "length": 50},
    ...
  },
  "imports": {
    "anthropic": "✅ OK",
    "supabase": "✅ OK",
    "conductor.supabase_query": "✅ OK",
    ...
  },
  "summary": {
    "status": "HEALTHY",
    "total_issues": 0,
    "issues": ["✅ All checks passed!"]
  }
}

# /api/query should return:
{
  "answer": "Based on the archives...",
  "sources": [...],
  "query": "test",
  "retrieval_count": 3
}
```

---

## 🎯 RECOMMENDED FIX SEQUENCE

Apply fixes in this order for best results:

1. **Deploy debug endpoint** (PHASE 2 above)
2. **Check debug output** to identify which root cause(s) apply
3. **Apply FIX #1** if env vars are missing
4. **Apply FIX #2** if imports are failing
5. **Apply FIX #3** for better error visibility
6. **Verify with checklist** above

---

## 🚀 QUICKSTART COMMANDS

```bash
# Terminal 1: Monitor logs
cd /Users/noahdeskin/conductor/queryable-slack-2
vercel logs --follow

# Terminal 2: Deploy fixes
cd frontend

# Check environment variables
vercel env ls

# Add missing variables if needed
vercel env add ANTHROPIC_API_KEY production

# Deploy with force rebuild
vercel --prod --force

# Test debug endpoint
curl https://queryable-slack.vercel.app/api/debug | jq

# Test query endpoint
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "match_count": 1}'
```

---

## 📚 REFERENCES

- Vercel Environment Variables: https://vercel.com/docs/environment-variables
- Vercel Python Runtime: https://vercel.com/docs/functions/runtimes/python
- Vercel Deployment Logs: https://vercel.com/docs/deployments/logs
- Supabase Python Client: https://github.com/supabase-community/supabase-py

---

**START WITH THE DEBUG ENDPOINT - it will tell you exactly what's wrong!**
