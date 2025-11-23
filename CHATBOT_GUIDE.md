# Interactive Vector Database Chatbot

## 🎯 Overview

An interactive CLI chatbot that queries your vector database. Each message is a **fresh call** with **thinking mode** enabled, displaying beautiful markdown output that adapts to your terminal size.

## ✨ Features

- **Interactive Chat Interface** - Natural conversation flow
- **Fresh Calls** - No memory between queries, each is independent
- **Thinking Mode** - Chain-of-thought reasoning enabled by default
- **Beautiful Output** - Stunning markdown that adapts to terminal size
- **App-like Interface** - Full-screen TUI with Rich Layout
- **Context7-Guided** - Designed using Context7 best practices

## 🚀 Quick Start

```bash
# Start the chatbot
python -m conductor.chat

# With specific database
python -m conductor.chat --db-path conductor_db

# Disable thinking mode
python -m conductor.chat --no-thinking
```

## 💬 Usage

### Starting the Chatbot

```bash
python -m conductor.chat --db-path conductor_db
```

You'll see a welcome screen, then you can start asking questions!

### Asking Questions

Just type your question and press Enter:

```
You: what do agents say when they have listings?
```

The chatbot will:
1. Query the vector database
2. Format the context
3. Query Claude with thinking mode
4. Display beautiful markdown response

### Commands

Type `/help` to see all available commands:

- `/help` - Show help message
- `/exit` or `/quit` - Exit the chatbot
- `/clear` - Clear the screen
- `/db <path>` - Change database path
- `/hybrid` - Toggle hybrid search
- `/thinking` - Toggle thinking mode
- `/cache` - Toggle query caching

## 📝 Example Session

```
🔍 Vector Database Chatbot • Thinking Mode • Context7-Guided
DB: conductor_db | Type '/help' for commands | '/exit' to quit

You: what do agents say when they have listings?

[Beautiful markdown response displayed here]

You: how long does it take admins to complete tasks?

[Another beautiful response]

You: /exit
Goodbye!
```

## 🎨 Interface Features

### Adaptive Layout
- **Header** - Shows current database and status
- **Main Content** - Your questions and responses
- **Input Area** - Where you type
- **Footer** - Status and tips

### Beautiful Markdown
- Syntax-highlighted code blocks
- Formatted tables
- Clear headings and structure
- Responsive to terminal width

### Loading States
- Shows progress during query processing
- Updates in real-time
- Clean transitions between states

## ⚙️ Configuration

### Command Line Options

```bash
--db-path PATH      # Specify database path
--no-thinking       # Disable thinking mode
--no-hybrid         # Disable hybrid search
```

### In-Chat Commands

All settings can be toggled during the chat session:
- `/thinking` - Toggle thinking mode on/off
- `/hybrid` - Toggle hybrid search on/off
- `/cache` - Toggle query caching on/off
- `/db <path>` - Switch to different database

## 🔄 How It Works

1. **You type a question** - Natural language query
2. **Vector search** - Queries ChromaDB for similar sessions
3. **Context formatting** - Formats retrieved sessions
4. **Claude thinking** - Uses thinking mode for reasoning
5. **Beautiful display** - Shows formatted markdown response
6. **Fresh start** - Next question starts from scratch (no memory)

## 🎯 Best Practices

### For Best Results

- **Be specific** - "What do agents say about listings?" is better than "tell me stuff"
- **Use thinking mode** - Enabled by default for better reasoning
- **Try hybrid search** - Use `/hybrid` for keyword + semantic search
- **Clear screen** - Use `/clear` if output gets cluttered

### Query Examples

```
# Good queries
"What do agents say when they have listings?"
"How long does it take admins to complete deal processing?"
"Show me examples of broker loading workflows"

# Less effective
"stuff"
"tell me things"
"what's in the database"
```

## 🆚 Comparison

| Feature | `ask.py` | `chat.py` |
|---------|----------|-----------|
| Interface | Single query | Interactive chat |
| Memory | None | None (fresh each time) |
| Output | Plain text | Beautiful markdown |
| Commands | CLI flags | In-chat commands |
| Layout | Simple | App-like TUI |
| Use Case | One-off queries | Conversation flow |

## 🐛 Troubleshooting

### Rich Not Installed

```bash
pip install rich
```

### Terminal Too Small

The interface adapts to terminal size, but for best experience:
- Use terminal width of at least 80 characters
- Use terminal height of at least 24 lines

### Database Not Found

```bash
# Check database exists
ls -la conductor_db/

# Or specify full path
python -m conductor.chat --db-path /full/path/to/database
```

### API Key Issues

```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# Or add to .env file
echo "ANTHROPIC_API_KEY=your_key" >> .env
```

## 📚 Related Files

- `conductor/chat.py` - Main chatbot implementation
- `conductor/ask.py` - Single query tool
- `conductor/ask_beautiful.py` - Beautiful single query tool
- `CONTEXT7_CLI_GUIDE.md` - Context7 CLI documentation

## 🎉 Enjoy!

Start chatting with your vector database! Each question gets a fresh, thoughtful response with beautiful formatting.

```bash
python -m conductor.chat --db-path conductor_db
```

