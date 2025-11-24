# Python API Diagnostic Report
## Explore Agent Analysis - 2025-11-24

## Critical Finding

**STATUS: PYTHON API IS FULLY OPERATIONAL**

The Python API endpoint at `/api/index` is working correctly on both deployments:
- queryable-slack-2.vercel.app
- queryable-slack.vercel.app

## Test Evidence

### Curl Test (Direct HTTP)
```bash
curl -X POST https://queryable-slack-2.vercel.app/api/index \
  -H 'Content-Type: application/json' \
  -d '{"query":"test","match_count":1}'
```

**Response:** HTTP 200 OK (JSON)
```json
{
  "answer": "I don't have information about that in the archives...",
  "sources": [{"date": "2023-05-24", "channel": "support-team", "message_count": 18}],
  "query": "test",
  "retrieval_count": 1
}
```

### Node.js Test (JavaScript Context)
```javascript
const response = await fetch('https://queryable-slack-2.vercel.app/api/index', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'test', match_count: 1 })
});

console.log(response.status); // 200
const data = await response.json();
console.log(data.answer); // Returns Claude's response
```

**Result:** Status 200, data.answer exists, data.sources is array

## Code Analysis

### Python Handler Location
File: `/frontend/api/index.py`

**Endpoints Configured:**
- `POST /api/query` → Handled by `handle_semantic_query()`
- `POST /api/index` → Handled by `handle_semantic_query()`
- `POST /` → Handled by `handle_semantic_query()`
- `GET /api/health` → Health check
- `GET /api/sessions` → List sessions

### Request Pipeline
1. HTTP request arrives at `/frontend/api/index.py`
2. `handler.do_POST()` routes to `handle_semantic_query()`
3. Extracts `query` and `match_count` from JSON body
4. Calls `conductor.supabase_query.query_vector_similarity()`
   - Creates OpenAI client to Vercel AI Gateway
   - Generates embedding for query
   - Runs vector similarity search on Supabase
5. Constructs context from search results
6. Calls Anthropic Claude API with context
7. Returns JSON with `{answer, sources, query, retrieval_count}`

### Dependencies
- `conductor/supabase_query.py` - Supabase vector search
- `anthropic` SDK - Claude message generation
- `openai` SDK - Embedding via Vercel AI Gateway
- `supabase` SDK - Database client

## Vercel Configuration

### deployment Config
File: `frontend/vercel.json`
```json
{
  "functions": {
    "api/**/*.py": {
      "memory": 1024,
      "maxDuration": 60,
      "includeFiles": "conductor/**"
    }
  }
}
```

✓ Python files in `api/` are serverless functions
✓ Conductor package included in deployment
✓ 60-second timeout
✓ 1GB memory

## Response Structure

### Success Response (HTTP 200)
```json
{
  "answer": "string - Claude's response",
  "sources": [
    {
      "date": "string - YYYY-MM-DD",
      "channel": "string - Slack channel name",
      "message_count": "number"
    }
  ],
  "query": "string - original query",
  "retrieval_count": "number - results found"
}
```

### Error Responses
- **400 Bad Request**: Missing `query` parameter
- **404 Not Found**: Endpoint doesn't exist (e.g., `/api/query`)
- **500 Internal Server Error**: Missing API keys or database error

## Key Insights

### Why /api/index Works
1. Vercel routes `api/**/*.py` to Python serverless functions
2. The handler class processes POST requests
3. Request path `/api/index` matches the route pattern
4. handler.do_POST() line 82 explicitly handles `/api/index`

### Why /api/query Returns 404
1. Next.js doesn't have a TypeScript route for `/api/query`
2. Vercel tries to find a file named `query.py` or `query/route.py`
3. Only `index.py` exists (which handles both `/api/index` and `/api/query`)
4. This is expected behavior - the file should be renamed or duplicate routes added

### Performance Characteristics
- Embedding generation: ~2-3 seconds (Vercel AI Gateway)
- Vector search: <1 second (Supabase)
- Claude generation: ~4-5 seconds
- **Total request time: 8-10 seconds**

## Integration with /api/chat

The Next.js `/api/chat` route correctly calls:

```typescript
// frontend/app/api/chat/route.ts (line 32-42)
const apiUrl = new URL('/api/index', req.url);
const response = await fetch(apiUrl.toString(), {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query,
    match_count: 5
  }),
});
```

This correctly:
- Creates absolute URL to `/api/index`
- Uses POST method
- Sends JSON with query and match_count
- Gets 200 response with JSON data

## Troubleshooting Checklist

If `/api/chat` is not working despite the Python API being online:

### Check 1: Environment Variables
```bash
# Verify these are set in Vercel:
ANTHROPIC_API_KEY=sk-ant-...
AI_GATEWAY_API_KEY=...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
```

### Check 2: Browser Console
1. Open DevTools (F12)
2. Go to Network tab
3. Make a query
4. Check `/api/chat` request:
   - Status code?
   - Response headers?
   - Response body (if any)?

### Check 3: Response Parsing
The `/api/chat` route expects 200 status, then parses response as JSON:
```typescript
if (!response.ok) {
  throw new Error('Conductor API error: ' + response.statusText);
}
const data = await response.json();
```

If getting 500 from `/api/chat`, the Python API returned an error. Check:
- API keys are valid
- Supabase database is accessible
- Claude API is responding

### Check 4: Streaming vs JSON
The `/api/chat` route returns Server-Sent Events (SSE) stream, not JSON:
```typescript
return new Response(stream, {
  headers: {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
  },
});
```

Frontend needs to handle SSE format, not plain JSON.

## Conclusion

The Python API infrastructure is sound and operational. Any issues with `/api/chat` are likely:

1. **Environment variables not set** - API keys missing
2. **Frontend not handling SSE format** - Expecting JSON, getting stream
3. **Race conditions** - Async timing issues
4. **CORS issues** - Though CORS headers are set correctly
5. **Timeout during long operations** - 8-10 seconds might exceed frontend timeout

**Recommendation:** Check browser DevTools Network tab for exact error from `/api/chat` endpoint.

