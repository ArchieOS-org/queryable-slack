# Run the Chatbot - Quick Commands

## 🚀 Basic Commands

### Start the Chatbot

```bash
# Activate virtual environment
source venv312/bin/activate

# Start chatbot with default database
python -m conductor.chat
```

### With Specific Database

```bash
# Use conductor_db database
python -m conductor.chat --db-path conductor_db

# Use preview database
python -m conductor.chat --db-path conductor_db_preview_20251120_225158
```

### With Options

```bash
# Disable thinking mode
python -m conductor.chat --db-path conductor_db --no-thinking

# Enable hybrid search from start
python -m conductor.chat --db-path conductor_db --no-hybrid=false
```

## 📝 Full Command Examples

```bash
# Most common usage
cd /Volumes/LaCie/Coding-Projects/queryable-slack
source venv312/bin/activate
python -m conductor.chat --db-path conductor_db
```

## 💬 Once Running

Type your questions directly:

```
You: what do agents say when they have listings?
You: how long does it take admins to complete tasks?
You: /help
You: /exit
```

## 🎯 Quick Start (Copy & Paste)

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
source venv312/bin/activate
python -m conductor.chat --db-path conductor_db
```

Then start asking questions!

