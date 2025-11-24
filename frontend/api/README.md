# Conductor API

FastAPI-based semantic search API for Slack exports.

## Endpoints

- `GET /` - API information
- `GET /api/health` - Health check
- `GET /api/sessions` - List recent sessions
- `GET /api/sessions/{id}` - Get specific session
- `POST /api/query` - Semantic search with Claude answer

## Local Development

```bash
# Install dependencies
pip install fastapi uvicorn supabase-py anthropic numpy python-dotenv

# Run locally
uvicorn api.index:app --reload --port 8000
```

## Environment Variables

Required:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `ANTHROPIC_API_KEY`

Optional:
- `AI_GATEWAY_API_KEY`

## Deployment

See `VERCEL_DEPLOYMENT.md` in project root.
