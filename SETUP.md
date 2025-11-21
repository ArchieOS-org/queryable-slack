# Setup Guide

## Python Version Requirements

**Important**: This project requires Python 3.11, 3.12, or 3.13. Python 3.14 is not yet fully supported by ChromaDB.

## Quick Start

### 1. Create Virtual Environment

```bash
# Using Python 3.11, 3.12, or 3.13
python3.11 -m venv venv
# OR
python3.12 -m venv venv
# OR  
python3.13 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2. Install Dependencies

**Option A: Using requirements.txt (Recommended)**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Option B: Install individually**
```bash
pip install --upgrade pip
pip install pydantic chromadb anthropic langchain-community unstructured
```

### 3. Run Ingestion

```bash
# Activate venv first
source venv/bin/activate

# Run ingestion on your Slack export
python -m conductor.ingest /path/to/slack/export
```

### 4. Query the System

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here

# Query the system
python -m conductor.ask "Your question here"
```

## Troubleshooting

### If `python` command not found:
- Use `python3` instead of `python`
- Or activate your virtual environment: `source venv/bin/activate`

### If ChromaDB import errors:
- Ensure you're using Python 3.11-3.13 (not 3.14)
- Try: `pip install --upgrade chromadb`

### If Poetry is broken:
- Use the virtual environment approach above instead
- Poetry's environment may need to be recreated

