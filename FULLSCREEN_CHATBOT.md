# Full-Screen Terminal Chatbot

## 🎯 Overview

A full-screen, scrollable, resizable terminal app that takes over your terminal like Claude Code. Uses Context7 best practices for terminal UI design.

## ✨ Features

- **Full-Screen Terminal** - Takes over terminal like Claude Code
- **Scrollable Content** - All output is visible and scrollable
- **Resizable** - Automatically adapts to terminal window size
- **Context7-Guided** - Uses Context7 best practices for terminal apps
- **Beautiful Layout** - Clean, app-like interface

## 🚀 Usage

```bash
# Start full-screen chatbot
python -m conductor.chat_fullscreen

# With specific database
python -m conductor.chat_fullscreen --db-path conductor_db

# Disable thinking mode
python -m conductor.chat_fullscreen --no-thinking
```

## 🎨 Features

### Full-Screen Mode
- Uses `console.screen()` for terminal takeover
- Clean, app-like interface
- No interference with terminal scrollback

### Scrollable Content
- All chat history is scrollable
- Use ↑↓ keys to navigate (coming soon)
- Content adapts to terminal height

### Resizable
- Automatically adapts to terminal window size
- Resize your terminal and watch it adjust
- Layout recalculates on resize

### All Output Visible
- No content is hidden or truncated
- Full responses displayed
- Scrollable history

## 📝 Commands

- `/help` - Show help
- `/exit` or `/quit` - Exit chatbot
- `/clear` - Clear chat history
- `/db <path>` - Change database
- `/hybrid` - Toggle hybrid search
- `/thinking` - Toggle thinking mode
- `/refinement` - Toggle query refinement

## 🔄 How It Works

1. **Full-Screen Mode** - Uses Rich's `console.screen()` context manager
2. **Layout System** - Rich Layout adapts to terminal dimensions
3. **Scrollable Content** - Custom ScrollableContent class handles scrolling
4. **Live Updates** - Screen updates dynamically as you chat

## 🆚 Comparison

| Feature | `chat.py` | `chat_fullscreen.py` |
|---------|-----------|----------------------|
| Mode | Interactive prompts | Full-screen terminal app |
| Scrolling | Limited | Full scrollable history |
| Resize | Manual refresh | Auto-adapts |
| Output | May truncate | All visible |
| Feel | CLI tool | App-like |

## 🎉 Try It!

```bash
python -m conductor.chat_fullscreen --db-path conductor_db
```

Resize your terminal window and watch it adapt! All output is visible and scrollable.

