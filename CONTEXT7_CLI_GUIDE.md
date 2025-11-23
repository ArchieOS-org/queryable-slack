# Context7 CLI Guide - Beautiful Query Interface

## 🎨 Overview

A beautiful CLI tool that automatically uses Context7 for library documentation, makes fresh calls every time (no memory), and displays results in stunning markdown format.

## ✨ Features

- **Automatic Context7** - Uses Context7 automatically when library docs are needed
- **Fresh Calls** - No chat memory, each query is independent
- **Beautiful Output** - Stunning markdown rendering with Rich
- **Chain-of-Thought** - Optional structured reasoning mode
- **Clean Interface** - Steve Jobs-level elegance

## 🚀 Installation

```bash
# Install Rich for beautiful output
pip install rich

# Or install all requirements
pip install -r requirements.txt
```

## 📖 Usage

### Basic Query

```bash
python -m conductor.query_context7 "How do I use ChromaDB PersistentClient?"
```

### With Options

```bash
# Disable thinking mode
python -m conductor.query_context7 "Simple question" --no-thinking

# Use different model
python -m conductor.query_context7 "Complex question" --model claude-opus-3

# Plain text output (no Rich formatting)
python -m conductor.query_context7 "Question" --plain
```

## 🎯 Examples

### Library Documentation Queries

```bash
# Automatically uses Context7 to get ChromaDB docs
python -m conductor.query_context7 "How do I create a ChromaDB collection?"

# Automatically uses Context7 to get Pydantic docs
python -m conductor.query_context7 "What's the Pydantic v2 syntax for field validation?"

# Automatically uses Context7 to get Rich docs
python -m conductor.query_context7 "Show me examples of using Rich for markdown output"
```

### General Questions

```bash
# Any question - Context7 will be used automatically if needed
python -m conductor.query_context7 "Explain how to build a REST API with FastAPI"

# Complex reasoning questions
python -m conductor.query_context7 "How should I structure a microservices architecture?" 
```

## 🎨 Output Format

The CLI produces beautiful markdown output with:

- **Clear headings** - Well-structured sections
- **Code blocks** - Syntax highlighted code
- **Lists** - Bullet points and numbered lists
- **Tables** - Formatted tables when appropriate
- **Emphasis** - Bold and italic text
- **Panels** - Beautiful bordered panels

## ⚙️ Configuration

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY=your_anthropic_key

# Optional (for Context7 MCP)
export CONTEXT7_API_KEY=your_context7_key
```

### Default Settings

- **Model**: `claude-sonnet-4-5-20250929`
- **Thinking**: Enabled by default
- **Max Tokens**: 4096
- **Temperature**: 0.3 (when thinking enabled)

## 🔧 How It Works

1. **You ask a question** - Simple natural language query
2. **Context7 auto-detection** - System automatically detects if library docs are needed
3. **Fresh API call** - Each query is independent, no memory
4. **Beautiful formatting** - Response formatted as markdown and rendered with Rich
5. **Stunning display** - Clean, elegant output in your terminal

## 💡 Tips

### For Best Results

- **Be specific** - "How do I use ChromaDB PersistentClient?" is better than "Tell me about databases"
- **Use thinking mode** - Enabled by default for complex questions
- **Let Context7 work** - Don't manually specify "use context7" - it's automatic

### Output Customization

- Use `--plain` for simple text output
- Use `--no-thinking` for faster, simpler responses
- Use `--model` to try different Claude models

## 🆚 Comparison with `ask.py`

| Feature | `ask.py` | `query_context7.py` |
|---------|----------|---------------------|
| Database | Uses ChromaDB vector search | Direct Claude queries |
| Memory | Uses cached context | Fresh calls every time |
| Context7 | Manual | Automatic |
| Output | Plain text | Beautiful markdown |
| Use Case | Query archived data | General questions + library docs |

## 🎉 Example Output

```
┌─────────────────────────────────────────────────────────────┐
│              Context7 Query Result                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ # Query Result                                              │
│                                                             │
│ **Question:** How do I use ChromaDB PersistentClient?     │
│                                                             │
│ ---                                                         │
│                                                             │
│ ## ChromaDB PersistentClient                                │
│                                                             │
│ To use ChromaDB's PersistentClient:                         │
│                                                             │
│ ```python                                                   │
│ import chromadb                                             │
│                                                             │
│ client = chromadb.PersistentClient(path="./chroma_db")      │
│ collection = client.get_or_create_collection("my_collection")│
│ ```                                                         │
│                                                             │
│ [More beautiful formatted content...]                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### Rich Not Installed

```bash
pip install rich
```

### API Key Issues

```bash
# Check your API key is set
echo $ANTHROPIC_API_KEY

# Or add to .env file
echo "ANTHROPIC_API_KEY=your_key" >> .env
```

### Context7 Not Working

- Context7 is used automatically when needed
- If you want explicit Context7 usage, mention the library name in your query
- Example: "Use library /chroma-core/chroma to show me how to create a collection"

## 📚 Related Files

- `conductor/query_context7.py` - Main CLI implementation
- `conductor/ask.py` - Database query tool (different use case)
- `CONTEXT7_SETUP.md` - Context7 configuration guide

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install rich anthropic python-dotenv

# 2. Set API key
export ANTHROPIC_API_KEY=your_key

# 3. Ask a question!
python -m conductor.query_context7 "How do I use Pydantic v2?"
```

Enjoy your beautiful, Context7-powered CLI! 🎨✨

