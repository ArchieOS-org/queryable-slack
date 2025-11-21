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
- **Semantic Search**: Vector-based similarity search using ChromaDB
- **LLM Integration**: Claude 3.5 Sonnet for intelligent query responses

## Requirements

- **Python**: 3.11, 3.12, or 3.13 (Python 3.14 is not yet supported by ChromaDB)
- **Anthropic API Key**: Required for querying (set via `ANTHROPIC_API_KEY` environment variable)

## Quick Start

**New to the project?** See [ONBOARDING.md](ONBOARDING.md) for a complete setup guide.

**Opening from external hard drive?** See [OPEN_FROM_HARD_DRIVE.md](OPEN_FROM_HARD_DRIVE.md) for specific instructions.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ArchieOS-org/queryable-slack.git
   cd queryable-slack
   ```

2. **Install dependencies** (see Installation below)

3. **Set up API key** - Create `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

4. **Run a trial** with a small subset:
   ```bash
   python -m conductor.trial_run /path/to/slack/export
   ```

5. **Test querying**:
   ```bash
   python -m conductor.ask "test question"
   ```

6. **If trial works, run full ingestion**:
   ```bash
   python -m conductor.ingest /path/to/slack/export
   ```

## Installation

### Using Virtual Environment (Recommended)

```bash
# Create virtual environment with Python 3.11-3.13
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies from requirements.txt
pip install --upgrade pip
pip install -r requirements.txt
```

**Alternative**: Install dependencies individually:
```bash
pip install pydantic chromadb anthropic langchain-community unstructured
```

### Using Poetry

```bash
poetry install
poetry shell
```

## Trial Run (Recommended First Step)

Before processing your full Slack export, test the pipeline with a small subset:

```bash
# Activate virtual environment first
source venv/bin/activate

# Create a trial export with 3 conversations and 5 days each
python -m conductor.trial_run /path/to/slack/export

# Or customize the trial size
python -m conductor.trial_run /path/to/slack/export --max-conversations 5 --max-days 10

# Create trial export without running ingestion
python -m conductor.trial_run /path/to/slack/export --no-ingest
```

**What it does:**
- Creates a `trial_export/` directory with a subset of your data
- Copies essential metadata files (users.json, channels.json, etc.)
- Limits conversations and daily message files for quick testing
- Optionally runs ingestion on the trial data

**Benefits:**
- Test the pipeline quickly before processing full dataset
- Verify file parsing works correctly
- Check ChromaDB setup and storage
- Debug any issues with a manageable dataset

## Usage

### 1. Ingest Slack Export

```bash
# Activate virtual environment first
source venv/bin/activate

# Run ingestion
python -m conductor.ingest /path/to/slack/export
```

The ingestion process:
1. Loads user mappings from `users.json`
2. Discovers all conversations (channels, DMs, MPIMs)
3. Merges daily message files into time-sorted timelines
4. Groups messages into sessions (6-hour threshold)
5. Extracts text from file attachments (PDF, DOCX, TXT)
6. Stores sessions in ChromaDB with vector embeddings

**Output**: Creates `./conductor_db/` directory with persistent vector store

### 2. Query the System

**Option A: Using .env file (Recommended)**

Create a `.env` file in the project root:
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
ANTHROPIC_API_KEY=your_api_key_here
```

Then query:
```bash
python -m conductor.ask "How did we handle the 156 Seymour negotiation?"
```

**Option B: Environment variable**

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here

# Query the semantic memory bank
python -m conductor.ask "How did we handle the 156 Seymour negotiation?"
```

The query process:
1. Embeds your query using the same embedding model
2. Searches ChromaDB for top 5 most similar sessions
3. Formats retrieved context with metadata
4. Sends to Claude 3.5 Sonnet with system prompt
5. Returns intelligent answer citing sources

## Project Structure

```
conductor/
├── __init__.py          # Package initialization
├── models.py            # Pydantic data models (UserMap, SlackMessage, Session, VectorRecord)
├── user_mapper.py       # Identity resolution (Bot vs Admin)
├── file_parser.py       # File extraction wrappers (PDF, DOCX, TXT)
├── processor.py         # Timeline stitching & sessionization logic
├── ingest.py            # Main orchestration entry point
├── ask.py               # CLI for querying the system
└── trial_run.py         # Trial run script for testing with subset of data

tests/                   # Pytest test suite
.env                     # Environment variables (API keys) - NOT in git
.env.example             # Example .env file template
.gitignore               # Git ignore rules
pyproject.toml           # Poetry configuration
requirements.txt         # Python dependencies (for pip install)
CLAUDE.md                # Detailed specification document
```

## Architecture

### Data Flow

```
Slack Export
    ↓
[1] Identity Mapping (users.json → UserMap dictionary)
    ↓
[2] Conversation Discovery (channels.json, dms.json, mpims.json)
    ↓
[3] Timeline & Sessionization
    ├── Load daily YYYY-MM-DD.json files
    ├── Merge into time-sorted message list
    └── Group into sessions (6-hour threshold)
    ↓
[4] File Enrichment
    ├── Extract text from attachments (PDF, DOCX, TXT)
    └── Inject into session transcripts
    ↓
[5] Vectorization & Storage
    ├── Generate deterministic session IDs
    ├── Embed enriched transcripts
    └── Store in ChromaDB with metadata
```

### Key Design Decisions

- **Deterministic IDs**: Session IDs are hashes of `{channel_name}_{start_time_iso}` ensuring idempotency
- **6-Hour Sessions**: Messages separated by >6 hours are split into different sessions
- **File Enrichment**: File content is injected into transcripts with delimiters for context
- **Bot Filtering**: Bot messages are labeled but not filtered (can be filtered in queries)

## Data Models

### UserMap
Maps Slack user IDs to metadata:
- `id`: User ID
- `real_name`: Display name
- `is_admin`: Admin status
- `is_bot`: Bot detection (is_bot OR is_app_user)

### SlackMessage
Represents a single Slack message:
- `ts`: Timestamp string
- `user`: User ID (optional)
- `text`: Message content
- `type`: Message type (filtered to "message")
- `files`: Array of file metadata

### Session
Atomic unit of memory:
- `session_id`: Deterministic hash
- `start_time` / `end_time`: Session boundaries
- `channel_name`: Conversation identifier
- `conversation_type`: "channel", "dm", or "mpim"
- `transcript`: Pure text conversation
- `enriched_transcript`: Transcript + file content
- `file_count` / `message_count`: Statistics

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Required for querying (Claude API)

### ChromaDB Storage

- Default location: `./conductor_db/`
- Collection name: `conductor_sessions`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (default)

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

### Code Style

- Type hints required for all functions
- Pydantic models for all I/O boundaries
- Structured logging with appropriate levels
- Error handling that never crashes the pipeline

## Best Practices

### Error Handling
- All Pydantic models use comprehensive error handling
- Invalid data is logged but doesn't stop the pipeline
- Validation errors are caught and handled gracefully

### Testing Before Full Run
- Always run `trial_run.py` first with a small subset
- Verify file parsing works with your specific file types
- Check that sessions are created correctly
- Test queries before processing the full dataset

### Idempotency
- Re-running ingestion is safe - uses deterministic IDs
- Same session data will update existing records, not create duplicates
- Can safely re-run if you need to update embeddings

### Performance
- Process conversations in parallel (future enhancement)
- Large exports may take time - use trial run to estimate
- ChromaDB uses local embeddings by default (fast, no API calls)

## Troubleshooting

### Python Version Issues

If you see ChromaDB import errors, ensure you're using Python 3.11-3.13:
```bash
python3.12 --version  # Should show 3.12.x
```

### Missing Dependencies

If imports fail, reinstall dependencies:
```bash
pip install -r requirements.txt
# OR install individually:
pip install --upgrade pydantic chromadb anthropic langchain-community unstructured
```

### ChromaDB Collection Not Found

If querying fails, ensure ingestion completed successfully:
```bash
# Check if conductor_db directory exists
ls -la conductor_db/
```

### API Key Issues

**Using .env file (Recommended):**
- Ensure `.env` file exists in project root
- Check that `ANTHROPIC_API_KEY=your_key` is set in `.env`
- The `.env` file is automatically loaded by `ask.py`

**Using environment variable:**
```bash
echo $ANTHROPIC_API_KEY  # Should show your key
```

**Get your API key:**
- Visit https://console.anthropic.com/
- Create an account or sign in
- Navigate to API Keys section
- Create a new API key

### Trial Run Issues

If trial run fails, check:
- Source export path is correct
- You have write permissions for trial_export directory
- Enough disk space for trial export

## License

[Add your license here]

## Author

Noah Deskin
