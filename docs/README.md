# Conductor - Real Estate AI Ingestion Engine

A production-grade pipeline that transforms raw Slack exports and local files into a queryable, semantic memory bank using Vector Search and LLMs.

## Overview

Conductor ingests Slack conversation exports, extracts text from attached files (PDFs, DOCX, TXT), organizes conversations into time-based sessions, and stores them in a vector database for semantic search. Query the system using natural language to find information across all conversations.

## Features

- **Strict Typing**: Pydantic v2 models at all I/O boundaries for type safety
- **Idempotent**: Re-running ingestion never creates duplicate vectors
- **Robust Error Handling**: Pipeline continues processing even when encountering bad data
- **Production Logging**: Structured logging throughout for observability
- **File Enrichment**: Automatically extracts text from PDF, DOCX, and TXT attachments
- **Sessionization**: Groups messages into conversation sessions based on 6-hour time gaps
- **Semantic Search**: Vector-based similarity search using Supabase pgvector
- **LLM Integration**: Claude 3.5 Sonnet for intelligent query responses
- **Web Interface**: Next.js frontend with real-time chat interface

## Requirements

- **Python**: 3.11, 3.12, or 3.13
- **Node.js**: 18+ with pnpm
- **Anthropic API Key**: Required for querying
- **Supabase Project**: For vector storage and search

## Quick Start

**New to the project?** See [SETUP.md](SETUP.md) for a complete setup guide.

### Local Development

1. **Clone and install dependencies**:
   ```bash
   git clone https://github.com/ArchieOS-org/queryable-slack.git
   cd queryable-slack

   # Install Python dependencies
   pip install -r api/requirements.txt

   # Install Node dependencies
   pnpm install
   ```

2. **Set up environment variables** - Create `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and add:
   # - ANTHROPIC_API_KEY
   # - SUPABASE_URL
   # - SUPABASE_KEY
   ```

3. **Run ingestion** (one-time):
   ```bash
   python -m conductor.ingest /path/to/slack/export
   ```

4. **Start development server**:
   ```bash
   pnpm dev
   ```

5. **Open browser**: http://localhost:3000

### Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Vercel deployment instructions.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture and data flow.

## Project Structure

```
queryable-slack-2/
├── src/                    # Next.js frontend
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   └── lib/               # Frontend utilities
├── api/                   # Python serverless functions
│   ├── index.py          # Main query endpoint
│   ├── chat.py           # Chat endpoint
│   └── requirements.txt  # Python dependencies
├── conductor/             # Python package (shared code)
│   ├── models.py         # Pydantic data models
│   ├── supabase_query.py # Vector search
│   ├── ingest.py         # Ingestion pipeline
│   └── ask.py            # CLI query tool
├── public/                # Static assets
├── docs/                  # Documentation
├── vercel.json            # Vercel configuration
├── package.json           # Node.js dependencies
└── next.config.ts         # Next.js configuration
```

## API Documentation

See [API.md](API.md) for API endpoint documentation.

## Development

### Running Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy conductor/
```

### Linting

```bash
ruff check conductor/
```

## Troubleshooting

### Python Version Issues

Ensure you're using Python 3.11-3.13:
```bash
python --version  # Should show 3.11.x, 3.12.x, or 3.13.x
```

### API Key Issues

Check that `.env` file exists and contains:
```bash
ANTHROPIC_API_KEY=your_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Supabase Connection Issues

Verify pgvector extension is enabled:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## License

[Add your license here]

## Author

Noah Deskin
