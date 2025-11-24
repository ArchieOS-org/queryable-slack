# Conductor API - Quick Reference

## API Status

Python API: **OPERATIONAL** ✓
- Endpoint: `POST https://queryable-slack-2.vercel.app/api/index`
- Status: HTTP 200
- Response: JSON with {answer, sources, query, retrieval_count}

## Quick Test

```bash
# Test if API is working
curl -X POST https://queryable-slack-2.vercel.app/api/index \
  -H 'Content-Type: application/json' \
  -d '{"query":"test","match_count":1}'

# Expected response (HTTP 200):
{
  "answer": "...",
  "sources": [{"date": "...", "channel": "...", "message_count": ...}],
  "query": "test",
  "retrieval_count": 1
}
```

## Request Format

```json
{
  "query": "string - user question",
  "match_count": 5
}
```

## Response Format

```json
{
  "answer": "Claude's response based on context",
  "sources": [
    {
      "date": "2023-05-24",
      "channel": "channel-name",
      "message_count": 18
    }
  ],
  "query": "original query",
  "retrieval_count": 1
}
```

## How It Works

1. Client calls `/api/chat` (Next.js)
2. `/api/chat` calls Python API at `/api/index`
3. Python API:
   - Generates embedding using OpenAI (via Vercel AI Gateway)
   - Searches vector database on Supabase
   - Generates Claude response using Anthropic SDK
   - Returns JSON
4. `/api/chat` streams response as Server-Sent Events (SSE)

## Performance

- Time per request: 8-10 seconds
- Breakdown:
  - Embedding generation: 2-3 seconds
  - Vector search: <1 second
  - Claude generation: 4-5 seconds

## Files

Location: `/frontend/api/index.py`

Key functions:
- `do_POST()` - Routes POST requests
- `handle_semantic_query()` - Main query handler
- `send_json_response()` - Sends JSON responses

## Dependencies

In `/conductor/`:
- `supabase_query.py` - Vector similarity search
- Installed packages: anthropic, openai, supabase

## Environment Variables Required

```
ANTHROPIC_API_KEY=sk-ant-...
AI_GATEWAY_API_KEY=...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
```

## Debugging

If `/api/chat` not working:

1. Test Python API directly:
   ```bash
   curl -X POST https://queryable-slack-2.vercel.app/api/index \
     -H 'Content-Type: application/json' \
     -d '{"query":"test","match_count":1}'
   ```

2. Check browser console (F12) for `/api/chat` errors

3. Verify environment variables in Vercel settings

4. Check response headers for content-type (should be `text/event-stream` for /api/chat)

## Endpoints

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| POST | /api/index | 200 | Semantic query (main) |
| POST | /api/query | 404 | Semantic query (mapped to /api/index) |
| GET | /api/health | 200 | Health check |
| GET | /api/sessions | 200 | List sessions |
| GET | /api/sessions/{id} | 200 | Get session |

## Technical Details

- Framework: Python `http.server.BaseHTTPRequestHandler`
- Deployment: Vercel (60s timeout, 1GB memory)
- Vector DB: Supabase (pgvector, cosine similarity)
- Embeddings: OpenAI text-embedding-3-small (384 dims)
- LLM: Anthropic Claude Sonnet 4

