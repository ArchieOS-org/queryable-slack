# Chat Debug Endpoint Guide

Critical diagnostic endpoint for capturing and fixing 500 errors in `/api/chat` production failures.

## What This Does

The `/api/chat-debug` endpoint is a comprehensive diagnostic tool that:

1. **Logs all incoming requests** - captures full request body with detailed logging
2. **Tests environment variables** - verifies all API keys are configured
3. **Tests Python module imports** - identifies missing dependencies
4. **Tests Supabase connectivity** - checks database connection
5. **Tests Vercel AI Gateway** - validates embeddings API
6. **Tests Anthropic API** - verifies Claude API connection
7. **Tests the full request flow** - simulates the complete /api/chat flow step-by-step
8. **Provides actionable diagnostics** - identifies exact failures and suggests fixes

## Files

- **Location**: `/frontend/api/chat-debug.py` (719 lines)
- **Handler**: Compatible with Vercel Functions
- **Endpoints**:
  - `GET /api/chat-debug` - Run full diagnostics
  - `POST /api/chat-debug` - Run diagnostics + test request flow
  - `OPTIONS /api/chat-debug` - CORS preflight

## Deployment

### Step 1: Deploy to Vercel

```bash
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend
vercel --prod --force
```

### Step 2: Verify Deployment

```bash
# Check endpoint is accessible
curl https://queryable-slack.vercel.app/api/chat-debug
```

## Usage

### Option 1: GET Request (Quick Diagnostics)

Returns full system diagnostics without testing the actual request flow:

```bash
curl https://queryable-slack.vercel.app/api/chat-debug
```

**Response includes**:
- Environment variables status
- Python environment info
- Module import status
- File system structure
- Supabase connectivity
- API Gateway connectivity
- Anthropic API status
- Summary of issues and next steps

### Option 2: POST Request (Full Flow Test)

Simulates the complete `/api/chat` flow:

```bash
curl -X POST https://queryable-slack.vercel.app/api/chat-debug \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the current status?",
    "match_count": 5
  }'
```

**Response includes**:
- All diagnostics from GET request
- Step-by-step test results for:
  1. Query parameter extraction
  2. Embedding generation via AI Gateway
  3. Vector similarity search in Supabase
  4. Claude response generation

## Understanding the Response

### Success Example

```json
{
  "timestamp": "2025-11-24T10:30:45.123456",
  "endpoint": "/api/chat-debug",
  "status": "diagnostic_run_complete",
  "environment": {
    "ANTHROPIC_API_KEY": {
      "present": true,
      "length": 123
    },
    "AI_GATEWAY_API_KEY": {
      "present": true,
      "length": 456
    }
  },
  "module_imports": {
    "anthropic": {"status": "OK"},
    "openai": {"status": "OK"},
    "conductor.supabase_query": {"status": "OK"}
  },
  "supabase_connectivity": {
    "status": "OK",
    "connected": true,
    "table_accessible": true
  },
  "api_gateway": {
    "status": "OK",
    "embedding_received": 384
  },
  "anthropic_api": {
    "status": "OK",
    "model": "claude-opus-4-1-20250805"
  },
  "summary": {
    "overall_status": "HEALTHY",
    "total_issues": 0,
    "issues": ["All systems operational"],
    "next_steps": [
      "1. System is fully operational",
      "2. Test the /api/chat endpoint with a query",
      "3. Monitor Vercel logs for runtime errors"
    ]
  }
}
```

### Failure Example

```json
{
  "summary": {
    "overall_status": "UNHEALTHY",
    "total_issues": 2,
    "issues": [
      "CRITICAL: ANTHROPIC_API_KEY not configured",
      "ERROR: Supabase connection failed - Credentials not configured"
    ],
    "next_steps": [
      "FIX ENVIRONMENT VARIABLES:",
      "  1. vercel env add ANTHROPIC_API_KEY production",
      "  2. vercel env add SUPABASE_URL production",
      "  3. vercel env add SUPABASE_ANON_KEY production",
      "  4. vercel --prod --force"
    ]
  }
}
```

## Debugging 500 Errors

### Workflow

1. **Access the debug endpoint**:
   ```bash
   curl https://queryable-slack.vercel.app/api/chat-debug
   ```

2. **Read the summary** - identifies critical issues

3. **Check next_steps** - provides exact commands to fix

4. **Apply fixes**:
   - Add missing environment variables
   - Update requirements.txt if dependencies are missing
   - Redeploy

5. **Test again**:
   ```bash
   curl -X POST https://queryable-slack.vercel.app/api/chat-debug \
     -d '{"query":"test"}'
   ```

6. **Verify with /api/chat**:
   ```bash
   curl -X POST https://queryable-slack.vercel.app/api/query \
     -d '{"query":"What happened?"}'
   ```

## Common Issues & Fixes

### Issue 1: Missing Environment Variables

**Symptom**:
```json
{
  "total_issues": 4,
  "issues": [
    "CRITICAL: ANTHROPIC_API_KEY not configured",
    "CRITICAL: AI_GATEWAY_API_KEY not configured",
    "CRITICAL: SUPABASE_URL not configured",
    "CRITICAL: SUPABASE_ANON_KEY not configured"
  ]
}
```

**Fix**:
```bash
vercel env add ANTHROPIC_API_KEY production
vercel env add AI_GATEWAY_API_KEY production
vercel env add SUPABASE_URL production
vercel env add SUPABASE_ANON_KEY production
vercel --prod --force
```

### Issue 2: Import Failures

**Symptom**:
```json
{
  "module_imports": {
    "conductor.supabase_query": {
      "status": "FAILED",
      "error": "ModuleNotFoundError: No module named 'supabase'"
    }
  }
}
```

**Fix**:
1. Check `requirements.txt` includes all dependencies
2. Add missing packages:
   ```bash
   pip install supabase httpx postgrest-py python-dotenv
   ```
3. Update `requirements.txt`:
   ```bash
   pip freeze > requirements.txt
   ```
4. Redeploy:
   ```bash
   vercel --prod --force
   ```

### Issue 3: Supabase Connection Failed

**Symptom**:
```json
{
  "supabase_connectivity": {
    "status": "FAILED",
    "error": "Failed to connect to Supabase"
  }
}
```

**Fix**:
1. Verify credentials are correct in Vercel environment
2. Check Supabase project is active
3. Verify pgvector extension is enabled
4. Test locally:
   ```bash
   source .env
   python -c "from conductor.supabase_query import get_supabase_client; client = get_supabase_client(); print('OK')"
   ```

### Issue 4: API Gateway Failed

**Symptom**:
```json
{
  "api_gateway": {
    "status": "FAILED",
    "error": "401 Unauthorized"
  }
}
```

**Fix**:
1. Verify `AI_GATEWAY_API_KEY` is correct
2. Check key is from Vercel AI Gateway (not OpenAI API key)
3. Regenerate key if necessary in Vercel dashboard
4. Redeploy:
   ```bash
   vercel env add AI_GATEWAY_API_KEY production
   vercel --prod --force
   ```

## Integration with Monitoring

### Add to Frontend Error Handler

```typescript
// In your frontend error handler:
async function diagnoseError() {
  const diagnostic = await fetch(
    'https://queryable-slack.vercel.app/api/chat-debug'
  ).then(r => r.json());
  
  console.error('System Diagnostic:', diagnostic);
  
  if (diagnostic.summary.overall_status !== 'HEALTHY') {
    console.error('Next steps:', diagnostic.summary.next_steps);
  }
}
```

### Add to Monitoring System

Track these metrics:
- `diagnostic.summary.overall_status` - HEALTHY/DEGRADED/UNHEALTHY
- `diagnostic.summary.total_issues` - number of issues
- `supabase_connectivity.status` - database connectivity
- `api_gateway.status` - embedding API status
- `anthropic_api.status` - Claude API status

## Logs

All diagnostics are logged to stdout with DEBUG level:

```
2025-11-24 10:30:45,123 - __main__ - INFO - GET request received at /api/chat-debug
2025-11-24 10:30:45,234 - __main__ - INFO - Running full system diagnostics...
2025-11-24 10:30:45,345 - __main__ - INFO - Checking environment variables...
2025-11-24 10:30:45,456 - __main__ - INFO -   ANTHROPIC_API_KEY: PRESENT (len=123)
2025-11-24 10:30:45,567 - __main__ - INFO -   AI_GATEWAY_API_KEY: PRESENT (len=456)
...
2025-11-24 10:30:47,890 - __main__ - INFO - Diagnostics complete. Status: HEALTHY
```

View in Vercel:
```bash
vercel logs --follow
```

## Key Features

### Request Body Logging
- Full request body captured and logged
- Sensitive headers masked
- Request/response sizes tracked
- Content-Type validation

### Comprehensive Testing
- 4-step flow simulation
- Individual error handling at each step
- Detailed error messages with stack traces
- Metrics for each step (embedding_length, results_found, etc.)

### Actionable Output
- Auto-detected issues categorized by type
- Specific next steps provided
- Copy-paste ready commands
- Links to relevant documentation

### Performance
- Minimal overhead (only test queries)
- Runs in under 5 seconds
- No side effects on production data
- Non-intrusive diagnostic mode

## Notes

- Endpoint is public - consider restricting access in production
- API calls (embeddings, Claude test) consume tokens - use sparingly
- Sensitive data (API keys) are masked in responses
- Full logs only visible in Vercel dashboard
- Keep endpoint deployed for ongoing diagnostics

## Next Steps After Deployment

1. Visit https://queryable-slack.vercel.app/api/chat-debug
2. Review the diagnostic output
3. Follow the suggested next steps
4. Re-test with a POST request to verify the full flow
5. Disable or restrict endpoint access in production

---

**Created**: 2025-11-24
**Purpose**: Emergency diagnostics for 500 errors in /api/chat
**Status**: Ready for deployment
