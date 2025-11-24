# Quick Debug Start Guide

Your life-critical debug endpoint is ready. Follow this exactly.

## 1. Deploy Now

```bash
cd /Users/noahdeskin/conductor/queryable-slack-2/frontend
vercel --prod --force
```

Wait for deployment to complete.

## 2. Test Immediately

```bash
# Quick status check
curl https://queryable-slack.vercel.app/api/chat-debug | jq '.summary'
```

You should see:
```json
{
  "overall_status": "HEALTHY",
  "total_issues": 0,
  "issues": ["All systems operational"]
}
```

If not healthy, follow the `next_steps` in the response.

## 3. Full Flow Test

```bash
# Test the complete /api/chat flow
curl -X POST https://queryable-slack.vercel.app/api/chat-debug \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}' | jq '.request_test'
```

## 4. Monitor Live Logs

```bash
vercel logs --follow
```

Watch for any errors during requests.

## 5. If Things Break

```bash
# Get full diagnostic output
curl https://queryable-slack.vercel.app/api/chat-debug | jq '.'
```

Look for:
- `"status": "FAILED"` - indicates a failure point
- `"next_steps"` - exact commands to fix it

## Common Failures

### Missing Env Vars
```
CRITICAL: ANTHROPIC_API_KEY not configured
```

Fix:
```bash
vercel env add ANTHROPIC_API_KEY production
vercel --prod --force
```

### Missing Modules
```
FAILED: Import failed: conductor.supabase_query
```

Fix:
```bash
pip install -r requirements.txt
vercel --prod --force
```

### Database Connection
```
ERROR: Supabase connection failed
```

Fix:
1. Check Supabase URL and key are correct in Vercel
2. Verify Supabase project is active
3. Redeploy

## Structure

```
frontend/api/
├── index.py          # Main /api/query endpoint
├── chat-debug.py     # NEW: Diagnostic endpoint
├── debug.py          # Existing environment diagnostics
└── ...
```

## Testing the Original Endpoint

Once diagnostics pass:

```bash
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello world"}' | jq '.'
```

## Key Files

- `/frontend/api/chat-debug.py` - 719 lines of comprehensive diagnostics
- `/CHAT_DEBUG_GUIDE.md` - Full documentation
- `/QUICK_DEBUG_START.md` - This file

## What We're Debugging

The endpoint simulates the complete flow:
1. Receives query
2. Generates embedding via Vercel AI Gateway
3. Searches Supabase vectors
4. Returns Claude answer

Each step is tested independently to isolate failures.

## Emergency: Can't Deploy?

```bash
# Check Vercel CLI is installed
vercel --version

# Check you're in the right directory
pwd  # Should end in /frontend

# Force clear and redeploy
rm -rf .vercel
vercel --prod --force
```

## Real Endpoint Status

After diagnostics pass, test the real endpoint:

```bash
# Real query endpoint
curl -X POST https://queryable-slack.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Show me recent sessions"}' 
```

Should return results or meaningful error.

## Remember

- Debug endpoint is your window into what's happening
- Follow the `next_steps` suggestions exactly
- Redeploy after ANY fix
- Test again to confirm
- Check logs with `vercel logs --follow`

---

**Status**: Ready to deploy
**Created**: 2025-11-24
**Your work depends on this** - deploy and test immediately
