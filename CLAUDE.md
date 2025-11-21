# CLAUDE.md

This file provides guidance for Claude Code when working on the Conductor project - a production-grade Real Estate AI ingestion engine that transforms Slack exports into a queryable semantic memory bank.

## Overview

Conductor is a high-frequency Real Estate AI ingestion engine that transforms raw Slack exports and local files into a queryable, semantic memory bank using Vector Search and LLMs. The system processes Slack conversations, extracts file attachments, creates time-based sessions, and stores them in ChromaDB for semantic search.

## Project Structure

```plaintext
queryable-slack/
├── conductor/              # Main package
│   ├── __init__.py
│   ├── models.py          # Pydantic model definitions
│   ├── user_mapper.py     # Identity resolution (Bot vs Admin)
│   ├── file_parser.py     # LangChain/Unstructured loaders wrapper
│   ├── processor.py       # Timeline stitching & Sessionization
│   ├── ingest.py          # Main orchestration entry point
│   └── ask.py             # CLI for querying the system
├── tests/                 # Pytest suite
├── pyproject.toml         # Poetry configuration
├── CLAUDE.md             # This file
└── .conductor/
    └── manado/
        └── promt.xml      # Detailed specification
```

## Core Principles

1. **Strict Typing**: Use Pydantic at ALL I/O boundaries - no exceptions
2. **Idempotency**: Re-running the script must NEVER create duplicate vectors
3. **Robust Error Handling**: The pipeline must NEVER crash on bad data (corrupt PDFs, malformed JSON, etc.)
4. **Production-Grade Logging**: Use standard logging library with appropriate levels (INFO, WARNING, ERROR)
5. **Context7 Research**: MANDATORY - Always use explore agents with Context7 for documentation research
6. **Correctness Over Speed**: Prioritize reliability and correctness - do not optimize prematurely
7. **Deterministic IDs**: Use hash-based deterministic IDs for all vector records

## Tech Stack

- **Language**: Python 3.11+
- **Dependency Manager**: Poetry
- **Core Libraries**:
  - `pydantic` (v2.x) - Strict data models & schema validation
  - `chromadb` - Local vector store & embeddings
  - `anthropic` - Claude SDK for intelligence
  - `langchain-community` - ONLY for PyPDFLoader and UnstructuredFileLoader
  - `unstructured` - For parsing DOCX/TXT (via UnstructuredFileLoader)

## Research Methodology

### MANDATORY: Context7 Explore Agents

**CRITICAL**: You MUST use Context7 via explore agents for ALL documentation research. This is non-negotiable.

#### When to Spawn Explore Agents

1. **Before Phase 1**: Spawn explore agents in PARALLEL for all libraries:

   - ChromaDB: PersistentClient setup and collection management
   - Pydantic: v2 model validation patterns and field validators
   - LangChain: document loaders import paths and usage
   - Anthropic: Claude SDK message creation and system prompts

2. **During Implementation**: If you encounter:
   - Import errors or module not found
   - API method signature mismatches
   - Uncertainty about usage patterns
   - Need to verify current best practices

#### Explore Agent Template

When spawning an explore agent, use this template:

```text
You are an explore agent tasked with researching {library_name} documentation using Context7.

MANDATORY REQUIREMENTS:
1. Use resolve-library-id to find the correct library identifier
2. Use get-library-docs with specific topics (not entire manuals)
3. Fetch multiple pages if needed (page=1, page=2, etc.)
4. Return concrete code examples and API patterns
5. Note version-specific requirements or breaking changes
6. Document exact import paths and function signatures

Do NOT use training data - ONLY use Context7 documentation.
```

#### Parallel Execution

When researching multiple libraries, spawn explore agents **simultaneously** for efficiency. Do NOT spawn them sequentially.

## Workflow Protocol

### 4-Phase Lifecycle (MANDATORY)

Every time you work on this repository, you MUST adhere to this lifecycle. Do not skip phases.

#### Phase 1: Explore & Research

**MANDATORY FIRST STEP**: Spawn explore agents with Context7 before writing any code.

1. Spawn explore agents in parallel for all libraries (ChromaDB, Pydantic, LangChain, Anthropic)
2. Wait for ALL agents to complete
3. Review and verify findings:
   - Import paths are current and correct
   - API patterns match current library versions
   - Code examples are valid and complete
4. Document version-specific requirements and breaking changes

**Output**: Summary document with verified API patterns, import paths, and code examples from Context7.

#### Phase 2: Plan

Design before implementing:

- Define Pydantic models for Session, Message, and User with complete field definitions
- Define function signatures for the ingestion pipeline with type hints
- Determine idempotency strategy (deterministic IDs based on session hashes)
- Plan error handling strategy for each I/O operation

#### Phase 3: Implement

Write code in small, coherent steps:

1. Create file structure
2. Implement User mapping first (`user_mapper.py`)
3. Implement Sessionization logic second (`processor.py`)
4. Implement File Enrichment third (`file_parser.py`)
5. Implement Vector Store integration last (`ingest.py`)

**Constraints**:

- Every I/O boundary MUST be typed with Pydantic models
- Every file operation MUST have error handling
- Every function MUST have type hints

**If you encounter issues**: Immediately spawn an explore agent with Context7 - do NOT guess.

#### Phase 4: Review & Harden

Ensure production readiness:

- **Error Handling**: Test with corrupted PDFs and malformed JSON
- **Logging**: Verify INFO/WARNING/ERROR levels are used appropriately
- **Determinism**: Run ingestion script twice and verify no duplicate vectors

## Code Style Guidelines

### Python Best Practices

- Use `pathlib.Path` instead of `os.path` for file operations
- Use `logging` instead of `print` statements
- Use specific exceptions (e.g., `FileNotFoundError`, `json.JSONDecodeError`)
- Use type hints on all functions
- Use Pydantic models for all data structures at I/O boundaries

### Error Handling Pattern

```python
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

def load_json_file(file_path: Path) -> list[dict]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        raise
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading {file_path}: {e}")
        raise
```

### Pydantic Model Pattern

```python
from pydantic import BaseModel, field_validator, ValidationError
from typing import Optional

class UserMap(BaseModel):
    id: str
    real_name: str
    is_admin: bool
    is_bot: bool
    
    @field_validator('is_bot', mode='before')
    @classmethod
    def compute_is_bot(cls, v, info):
        raw_data = info.data if hasattr(info, 'data') else {}
        return raw_data.get('is_bot', False) or raw_data.get('is_app_user', False)
```

### Logging Pattern

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Usage:
logger.info(f"Processing session {session_id}")
logger.warning(f"Skipped file {filename}: unsupported type")
logger.error(f"Failed to process {conversation_dir}: {e}")
```

## Common Commands

### Setup & Installation

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run type checking
poetry run mypy conductor/

# Run tests
poetry run pytest tests/

# Run ingestion
poetry run python -m conductor.ingest /path/to/slack/export

# Query the system
poetry run python -m conductor.ask "How did we handle the 156 Seymour negotiation?"
```

### Development Workflow

```bash
# Before starting work: Spawn explore agents with Context7
# Then proceed with 4-phase lifecycle

# After implementation: Run tests
poetry run pytest tests/ -v

# Check code quality
poetry run ruff check conductor/
poetry run mypy conductor/
```

## File Structure Details

### Package: `conductor/`

- **`models.py`**: All Pydantic model definitions (UserMap, SlackMessage, Session, VectorRecord)
- **`user_mapper.py`**: Maps Slack user IDs to user metadata, handles bot detection
- **`file_parser.py`**: Wraps LangChain loaders (PyPDFLoader, UnstructuredFileLoader) with error handling
- **`processor.py`**: Core sessionization logic - merges daily files, creates time-based sessions
- **`ingest.py`**: Main orchestration - coordinates all steps of the ingestion pipeline
- **`ask.py`**: CLI interface for querying the semantic memory bank

### Key Data Models

- **UserMap**: Maps user IDs to metadata (id, real_name, is_admin, is_bot)
- **SlackMessage**: Represents a single Slack message (ts, user, text, type, files)
- **Session**: Atomic unit of memory - conversation session with transcript and metadata
- **VectorRecord**: What goes into ChromaDB (id, document, metadata)

## Slack Export Structure

The Slack export has this structure:

- **Top-level files**: `users.json`, `channels.json`, `dms.json`, `mpims.json`, `groups.json`
- **Conversation directories**: Named by channel name (channels) or ID (DMs/MPIMs)
- **Daily files**: `YYYY-MM-DD.json` files containing message arrays
- **Attachments**: `attachments/` subdirectory with files named `{FILE_ID}-{filename}`

**Critical**: Channel directories use the `name` field from `channels.json`, NOT the channel ID.

## ChromaDB Configuration

- **Client**: `PersistentClient(path="./conductor_db")`
- **Collection**: `conductor_sessions`
- **Embedding**: Default local embedding (sentence-transformers/all-MiniLM-L6-v2)
- **ID Strategy**: Deterministic hash of `"{channel_name}_{start_time_iso}"`
- **Storage**: Use `collection.upsert()` for idempotent inserts

## Important Constraints

1. **Never skip Phase 1**: Always research with Context7 explore agents first
2. **Never use training data**: Always verify APIs via Context7
3. **Never skip error handling**: Every I/O operation must have try/except
4. **Never skip type hints**: Every function must have type annotations
5. **Never create duplicates**: Use deterministic IDs for idempotency
6. **Never crash on bad data**: Handle errors gracefully and continue processing

## When in Doubt

1. **Spawn an explore agent with Context7** - do not guess
2. **Check the specification**: See `.conductor/manado/promt.xml` for detailed requirements
3. **Follow the 4-phase lifecycle**: Do not skip phases
4. **Use Pydantic models**: At all I/O boundaries
5. **Log everything**: Use appropriate log levels

## Best Practices for Claude Code

- Use parallel tool calling - spawn multiple explore agents simultaneously
- Be explicit and specific in instructions
- Default to action - use tools proactively to discover information
- Complete tasks fully - don't stop early due to token concerns
- Use explore agents for tasks benefiting from separate context windows

**Remember**: This project prioritizes correctness and reliability over speed. Take the time to do it right, use Context7 for research, and follow the 4-phase lifecycle religiously.
