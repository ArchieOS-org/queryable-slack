# Setup Guide

Complete setup instructions for Conductor on a new computer.

## Prerequisites

- **Python 3.11, 3.12, or 3.13** (Python 3.14 is NOT supported)
- **Node.js 18+** with pnpm installed
- **Git** installed
- **Anthropic API Key** (get from https://console.anthropic.com/)
- **Supabase Project** (get from https://supabase.com/)

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

### 4. Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r api/requirements.txt
```

This will install:
- `pydantic` - Data validation
- `anthropic` - Claude SDK
- `supabase` - Supabase client
- `langchain-community` - Document loaders
- `unstructured` - File parsing
- `python-dotenv` - Environment variables

### 5. Install Node.js Dependencies

```bash
# Install pnpm if not already installed
npm install -g pnpm

# Install project dependencies
pnpm install
```

### 6. Set Up Environment Variables

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your credentials
nano .env  # or code .env or vim .env
```

Edit `.env` and add:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

**Get your Anthropic API key:**
1. Go to https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to API Keys
4. Create a new API key
5. Copy and paste it into `.env`

**Get your Supabase credentials:**
1. Go to https://supabase.com/
2. Create a new project or select existing
3. Go to Settings → API
4. Copy the Project URL and anon/public key
5. Paste into `.env`

### 7. Set Up Supabase Database

Enable the pgvector extension in your Supabase project:

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Run this SQL:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  channel_name TEXT NOT NULL,
  conversation_type TEXT NOT NULL,
  start_time TIMESTAMP WITH TIME ZONE NOT NULL,
  end_time TIMESTAMP WITH TIME ZONE NOT NULL,
  message_count INTEGER NOT NULL,
  file_count INTEGER NOT NULL,
  enriched_transcript TEXT NOT NULL,
  embedding vector(384),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX ON sessions USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

### 8. Verify Installation

```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Test Python imports
python -c "import pydantic; import anthropic; from supabase import create_client; print('✅ Python imports successful!')"

# Test Node.js setup
pnpm --version  # Should show pnpm version
```

### 9. Prepare Your Slack Export

You'll need a Slack export directory. This should contain:
- `users.json`
- `channels.json`
- `dms.json`
- `mpims.json`
- Conversation directories with daily JSON files

**Note:** The Slack export data is NOT in the repository (it's excluded by .gitignore for privacy).

### 10. Run Ingestion (One-Time)

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux

# Run ingestion on your Slack export
python -m conductor.ingest /path/to/your/slack/export
```

This will:
- Process all conversations
- Extract text from attachments
- Create sessions and embeddings
- Store in Supabase

### 11. Start Development Server

```bash
# Start Next.js development server
pnpm dev
```

Open http://localhost:3000 in your browser.

### 12. Test the Application

1. Type a question in the chat interface
2. The system should retrieve relevant context from Supabase
3. Claude will generate a response based on the context

## Troubleshooting

### Python Version Issues

**Problem:** `python` command not found or wrong version

**Solution:**
```bash
# Use python3.12 explicitly
python3.12 -m venv venv
python3.12 -m pip install -r api/requirements.txt
```

### Import Errors

**Problem:** `ModuleNotFoundError` for Python packages

**Solution:**
```bash
# Reinstall all dependencies
pip install -r api/requirements.txt --upgrade
```

### API Key Not Found

**Problem:** `ANTHROPIC_API_KEY environment variable not set`

**Solution:**
- Check that `.env` file exists in project root
- Verify `ANTHROPIC_API_KEY=your_key` is in `.env`
- Make sure you activated the virtual environment

### Supabase Connection Errors

**Problem:** Cannot connect to Supabase or queries fail

**Solution:**
1. Verify credentials in `.env` are correct
2. Check that pgvector extension is enabled:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```
3. Verify sessions table exists:
   ```sql
   SELECT * FROM information_schema.tables
   WHERE table_name = 'sessions';
   ```

### Port Already in Use

**Problem:** Port 3000 is already in use

**Solution:**
```bash
# Use a different port
pnpm dev -- -p 3001
```

### pnpm Not Found

**Problem:** `pnpm: command not found`

**Solution:**
```bash
# Install pnpm globally
npm install -g pnpm
```

## Quick Reference

```bash
# Activate virtual environment (do this every time you open a new terminal)
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run ingestion (one-time)
python -m conductor.ingest /path/to/export

# Query via CLI
python -m conductor.ask "your question here"

# Start development server
pnpm dev

# Deactivate virtual environment when done
deactivate
```

## Next Steps

After setup is complete:

1. ✅ Test the web interface at http://localhost:3000
2. ✅ Try querying your Slack data
3. ✅ Review [ARCHITECTURE.md](ARCHITECTURE.md) to understand how it works
4. ✅ See [DEPLOYMENT.md](DEPLOYMENT.md) to deploy to production

## Need Help?

- Check [README.md](README.md) for overview
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system details
- Check [API.md](API.md) for API documentation
