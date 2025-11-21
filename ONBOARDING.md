# Onboarding Guide - Setting Up Conductor on a New Computer

This guide will help you set up the Conductor project on a new computer from scratch.

## Prerequisites

- **Python 3.11, 3.12, or 3.13** (Python 3.14 is NOT supported by ChromaDB)
- **Git** installed
- **Anthropic API Key** (get from https://console.anthropic.com/)

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ArchieOS-org/queryable-slack.git
cd queryable-slack
```

### 2. Check Python Version

```bash
# Check available Python versions
python3.11 --version  # Should show 3.11.x
python3.12 --version  # Should show 3.12.x
python3.13 --version  # Should show 3.13.x

# Use one of the above (e.g., Python 3.12)
```

### 3. Create Virtual Environment

```bash
# Create virtual environment with compatible Python version
python3.12 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

**Note:** This will install:
- pydantic (data validation)
- chromadb (vector database)
- anthropic (Claude SDK)
- langchain-community (document loaders)
- langchain-unstructured (DOCX loader)
- unstructured (file parsing)
- python-dotenv (environment variables)

### 5. Set Up Environment Variables

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your Anthropic API key
# On macOS/Linux:
nano .env
# OR
code .env  # If you have VS Code

# On Windows:
notepad .env
```

Edit `.env` and add:
```
ANTHROPIC_API_KEY=your_api_key_here
```

**Get your API key:**
1. Go to https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to API Keys
4. Create a new API key
5. Copy and paste it into `.env`

### 6. Verify Installation

```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate    # Windows

# Test imports
python -c "import pydantic; import chromadb; import anthropic; from langchain_community.document_loaders import PyPDFLoader; from langchain_unstructured import UnstructuredLoader; print('✅ All imports successful!')"
```

### 7. Prepare Your Slack Export

You'll need a Slack export directory. This should contain:
- `users.json`
- `channels.json`
- `dms.json`
- `mpims.json`
- Conversation directories with daily JSON files

**Note:** The Slack export data is NOT in the repository (it's excluded by .gitignore for privacy). You'll need to:
- Export it from Slack, OR
- Copy it from another computer, OR
- Use the existing export if you have access to it

### 8. Run a Trial (Recommended First Step)

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux

# Run trial with small subset (3 conversations, 5 days each)
python -m conductor.trial_run /path/to/your/slack/export

# This will:
# - Create a trial_export/ directory
# - Process a small subset of data
# - Store results in conductor_db/
```

### 9. Test Querying

```bash
# Query the trial dataset
python -m conductor.ask "What conversations are in this dataset?"
```

### 10. Run Full Ingestion (After Trial Works)

```bash
# Process the full Slack export
python -m conductor.ingest /path/to/your/slack/export
```

## Troubleshooting

### Python Version Issues

**Problem:** `python` command not found or wrong version
**Solution:**
```bash
# Use python3.12 explicitly
python3.12 -m venv venv
python3.12 -m pip install -r requirements.txt
```

### ChromaDB Import Errors

**Problem:** `ModuleNotFoundError: No module named 'chromadb'` or compatibility errors
**Solution:**
- Ensure you're using Python 3.11-3.13 (NOT 3.14)
- Reinstall: `pip install --upgrade chromadb`

### Missing Dependencies

**Problem:** Import errors for specific packages
**Solution:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt --upgrade
```

### API Key Not Found

**Problem:** `ANTHROPIC_API_KEY environment variable not set`
**Solution:**
- Check that `.env` file exists in project root
- Verify `ANTHROPIC_API_KEY=your_key` is in `.env`
- Make sure you activated the virtual environment

### Permission Errors

**Problem:** Permission denied when creating files/directories
**Solution:**
- Check write permissions in the project directory
- On macOS/Linux, you may need: `chmod -R u+w .`

## Quick Reference

```bash
# Activate virtual environment (do this every time you open a new terminal)
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run trial
python -m conductor.trial_run /path/to/export

# Run full ingestion
python -m conductor.ingest /path/to/export

# Query the system
python -m conductor.ask "your question here"

# Deactivate virtual environment when done
deactivate
```

## Project Structure

```
queryable-slack/
├── conductor/          # Main package
│   ├── models.py       # Data models
│   ├── ingest.py       # Ingestion pipeline
│   ├── ask.py          # Query interface
│   └── ...
├── venv/               # Virtual environment (created by you)
├── conductor_db/       # ChromaDB storage (created after ingestion)
├── .env                # Your API key (create from .env.example)
├── requirements.txt    # Python dependencies
└── README.md          # Full documentation
```

## Next Steps

1. ✅ Clone repository
2. ✅ Set up Python environment
3. ✅ Install dependencies
4. ✅ Configure .env file
5. ✅ Get Slack export data
6. ✅ Run trial ingestion
7. ✅ Test queries
8. ✅ Run full ingestion

## Need Help?

- Check `README.md` for detailed documentation
- Check `SETUP.md` for setup troubleshooting
- Check `EXAMPLE_TRIAL_RUN.md` for trial run examples

