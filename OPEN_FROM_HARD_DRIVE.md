# Opening Project from External Hard Drive

Yes! You can open this project directly from the hard drive on another Mac. Here's what you need to know:

## Quick Answer

**Yes, you can open it directly!** Just:
1. Plug in the hard drive
2. Open the project folder in your IDE (VS Code, PyCharm, etc.)
3. Set up a new Python environment (don't use the old venv)
4. Install dependencies
5. Create `.env` file with your API key

## Step-by-Step

### 1. Plug In Hard Drive & Open Project

```bash
# Navigate to the project on the hard drive
cd /Volumes/LaCie/Coding-Projects/queryable-slack

# Or open in your IDE:
# VS Code: File > Open Folder > Navigate to the project
# PyCharm: File > Open > Navigate to the project
```

### 2. Create a New Virtual Environment

**Important:** Don't use the existing `venv/` folder - it's tied to the original Mac's Python installation.

```bash
# Check Python version (must be 3.11, 3.12, or 3.13)
python3.12 --version

# Create NEW virtual environment
python3.12 -m venv venv

# Activate it
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Make sure venv is activated (you should see (venv) in your prompt)
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up .env File

**Option A: If .env already exists on the drive** (it might!)
```bash
# Check if .env exists
ls -la .env

# If it exists, you can use it directly (it already has the API key)
# Just verify it has your API key:
cat .env
```

**Option B: Create new .env file**
```bash
# Copy the example
cp .env.example .env

# Edit .env and add your API key
nano .env
# OR open in your IDE and edit
```

Add your API key to `.env`:
```
ANTHROPIC_API_KEY=your_api_key_here
```

**Get your API key:**
- Visit https://console.anthropic.com/
- Sign in or create account
- Navigate to API Keys section
- Create a new API key
- Copy and paste into `.env`

### 5. Verify Everything Works

```bash
# Test imports
python -c "import chromadb; import anthropic; from langchain_community.document_loaders import PyPDFLoader; from langchain_unstructured import UnstructuredLoader; print('✅ All imports successful!')"

# Check if Slack export exists
ls -la manado/my_export/ 2>/dev/null && echo "✅ Slack export found" || echo "⚠️  Slack export not found"

# Run a trial (if you have the Slack export on the drive)
python -m conductor.trial_run manado/my_export

# Or query existing database (if conductor_db/ exists)
python -m conductor.ask "test question"
```

## What's Already on the Hard Drive

✅ **All code** - Everything in `conductor/` directory  
✅ **Slack export data** - `manado/my_export/` (if it was on the drive)  
✅ **Documentation** - README.md, SETUP.md, ONBOARDING.md, etc.  
✅ **Configuration** - `.gitignore`, `requirements.txt`, `pyproject.toml`  
✅ **.env file** - May already exist with API key (check first!)  
✅ **ChromaDB database** - `conductor_db/` may exist if ingestion was run  

## What You Need to Set Up Fresh

❌ **Virtual environment** - Create new one (old `venv/` or `venv311/` won't work on different Mac)  
❌ **Dependencies** - Install from `requirements.txt` (even if old venv had them)  
⚠️ **.env file** - Check if it exists first, if not create from `.env.example`  
⚠️ **ChromaDB database** - Will be created automatically when you run ingestion (or reuse existing)  

## IDE-Specific Tips

### VS Code
1. File > Open Folder > Navigate to `/Volumes/LaCie/Coding-Projects/queryable-slack`
2. Select Python interpreter: `Cmd+Shift+P` > "Python: Select Interpreter" > Choose the new `venv/bin/python`
3. Install dependencies in integrated terminal

### PyCharm
1. File > Open > Navigate to project folder
2. PyCharm will detect it's a Python project
3. Configure interpreter: Settings > Project > Python Interpreter > Add > Existing Environment > Select `venv/bin/python`
4. Install packages from requirements.txt

## Important Notes

1. **Don't use the old venv/** - The existing `venv/` or `venv311/` folders are tied to the original Mac's Python installation and won't work on another Mac
2. **Python version matters** - Must be 3.11, 3.12, or 3.13 on the new Mac (Python 3.14 is NOT supported by ChromaDB)
3. **Slack export location** - If `manado/my_export/` is on the drive, you can use it directly. If not, you'll need to copy it or export fresh from Slack
4. **Database location** - `conductor_db/` will be created automatically in the project folder when you run ingestion. If it already exists, you can query it immediately
5. **.env file** - Check if it exists first (it might already have your API key). If not, create it from `.env.example`
6. **Project path** - The path `/Volumes/LaCie/Coding-Projects/queryable-slack` assumes your drive is named "LaCie". Adjust if your drive has a different name

## Troubleshooting

### "Python not found"
- Install Python 3.12 on the new Mac: `brew install python@3.12`
- Or use the system Python if it's 3.11-3.13

### "venv activation fails"
- Create a fresh venv (don't reuse the old one)
- Make sure you're using the right Python version

### "Import errors"
- Make sure venv is activated
- Reinstall: `pip install -r requirements.txt`

### "Can't find Slack export"
- Check if `manado/my_export/` exists: `ls -la manado/my_export/`
- If not, you'll need to:
  - Copy it from another location, OR
  - Export fresh from Slack (Settings > Workspace Settings > Import/Export Data)
- The export should contain: `users.json`, `channels.json`, `dms.json`, `mpims.json`, and conversation directories

### "ChromaDB database not found"
- This is normal if you haven't run ingestion yet
- Run: `python -m conductor.ingest manado/my_export` to create it
- Or run trial first: `python -m conductor.trial_run manado/my_export`

### "Drive path not found"
- Check what your drive is actually named: `ls /Volumes/`
- Adjust the path accordingly (e.g., `/Volumes/MyDrive/...` instead of `/Volumes/LaCie/...`)

## Complete Checklist

When opening on a new Mac:

- [ ] Plug in hard drive
- [ ] Open project folder in IDE
- [ ] Check Python version: `python3.12 --version` (must be 3.11-3.13)
- [ ] Create new virtual environment: `python3.12 -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Check if `.env` exists: `ls -la .env`
- [ ] If `.env` doesn't exist, create it: `cp .env.example .env` and add API key
- [ ] Verify imports work: `python -c "import chromadb; import anthropic; print('✅')"`
- [ ] Check if Slack export exists: `ls -la manado/my_export/`
- [ ] Run trial or full ingestion
- [ ] Query the system: `python -m conductor.ask "your question"`

## Summary

**Yes, you can absolutely open it from the hard drive!** The project is fully portable - all the code and data (if on the drive) will work on any Mac. Just remember to:

1. ✅ Create a fresh virtual environment (don't reuse old venv)
2. ✅ Install dependencies from `requirements.txt`
3. ✅ Set up `.env` file (or use existing one if present)
4. ✅ Run!

**Key Advantage:** Since everything is on the hard drive, you can work on the project from any Mac without needing to clone from GitHub or copy files around.

