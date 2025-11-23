# Vector Database Chatbot - Web App

## 🎨 Overview

A beautiful, mobile-first React web app for querying your vector database. Designed with Steve Jobs-level elegance - minimal, intentional, and delightful.

## ✨ Features

- **Mobile-First Design** - Perfect on phones, tablets, and desktops
- **Elegant & Minimal** - Clean, intentional design inspired by Apple
- **Real-time Chat** - Smooth, responsive chat interface
- **Markdown Rendering** - Beautiful formatted responses
- **FastAPI Backend** - High-performance async API
- **Context7-Guided** - Built using Context7 best practices

## 🚀 Quick Start

### One Command to Start Everything

```bash
./start_web.sh
```

This will:
1. ✅ Activate virtual environment
2. ✅ Start FastAPI backend (port 8000)
3. ✅ Start React frontend (port 3000)
4. ✅ Open browser automatically

### Manual Start

```bash
# Terminal 1: Start FastAPI backend
source venv312/bin/activate
python -m uvicorn web_api:app --reload --port 8000

# Terminal 2: Start React frontend
cd web
npm install  # First time only
npm run dev
```

Then open http://localhost:3000 in your browser.

## 📱 Mobile-First Design

The app is designed mobile-first:
- **Touch-optimized** - Large tap targets, smooth scrolling
- **Responsive** - Adapts beautifully to any screen size
- **Fast** - Optimized for mobile networks
- **Accessible** - Works great on all devices

## 🎯 Design Principles

### Steve Jobs Elegance

- **Minimal** - Only what's necessary
- **Intentional** - Every element has purpose
- **Delightful** - Smooth animations, perfect spacing
- **Focused** - No distractions, just the conversation

### Mobile-First

- **Touch-friendly** - 44px minimum tap targets
- **Readable** - Optimal font sizes and line heights
- **Fast** - Optimized loading and rendering
- **Responsive** - Works on any screen size

## 🏗️ Architecture

```
┌─────────────────┐
│  React Frontend │  Port 3000
│  (Vite + React) │
└────────┬────────┘
         │ HTTP REST API
         ▼
┌─────────────────┐
│  FastAPI Backend│  Port 8000
│  (Python)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector DB      │
│  (ChromaDB)     │
└─────────────────┘
```

## 📁 Project Structure

```
web/
├── src/
│   ├── App.jsx          # Main React component
│   ├── main.jsx         # React entry point
│   └── index.css        # Tailwind styles
├── public/              # Static assets
├── package.json         # Node dependencies
├── vite.config.js      # Vite configuration
└── tailwind.config.js  # Tailwind configuration

web_api.py              # FastAPI backend
start_web.sh            # Startup script
```

## 🎨 UI Components

### Chat Interface
- **Message Bubbles** - Clean, rounded bubbles
- **Markdown Rendering** - Beautiful formatted text
- **Loading States** - Smooth loading indicators
- **Error Handling** - Clear error messages

### Input
- **Fixed Bottom** - Always accessible
- **Auto-focus** - Ready to type immediately
- **Enter to Send** - Natural interaction
- **Disabled States** - Clear feedback

## 🔧 Configuration

### API URL

Edit `web/src/App.jsx` to change API URL:

```javascript
const API_URL = 'http://localhost:8000'
```

### Database Path

The default database is `conductor_db`. Change it in the API call:

```javascript
body: JSON.stringify({
  query: userMessage,
  db_path: 'conductor_db',  // Change this
  use_thinking: true,
  use_hybrid: false,
  use_refinement: true
})
```

## 📦 Dependencies

### Backend (Python)
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- Existing conductor dependencies

### Frontend (Node.js)
- `react` - UI library
- `react-dom` - React DOM bindings
- `react-markdown` - Markdown rendering
- `vite` - Build tool
- `tailwindcss` - Styling

## 🚀 Deployment

### Development
```bash
./start_web.sh
```

### Production Build
```bash
# Build React app
cd web
npm run build

# Serve with FastAPI (configure static files)
# Or use a production server like nginx
```

## 🎉 Features

- ✅ Mobile-first responsive design
- ✅ Elegant minimal UI
- ✅ Real-time chat interface
- ✅ Markdown rendering
- ✅ Loading states
- ✅ Error handling
- ✅ Auto-scroll to latest message
- ✅ Keyboard shortcuts (Enter to send)
- ✅ Clear button
- ✅ Refined query display

## 📱 Mobile Optimization

- Touch-optimized buttons (44px minimum)
- Smooth scrolling
- Responsive typography
- Optimized images
- Fast loading

## 🎨 Design Details

- **Colors**: Clean grays, blue accents
- **Typography**: System fonts (SF Pro on macOS)
- **Spacing**: Generous, intentional
- **Animations**: Subtle, smooth
- **Shadows**: Minimal, elegant

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill

# Kill process on port 3000
lsof -ti:3000 | xargs kill
```

### Dependencies Not Installed

```bash
# Backend
pip install fastapi uvicorn[standard]

# Frontend
cd web
npm install
```

### CORS Errors

Make sure the frontend URL is in the CORS origins list in `web_api.py`:

```python
allow_origins=["http://localhost:3000", "http://localhost:5173"]
```

## 🎯 Usage

1. **Start the app**: `./start_web.sh`
2. **Ask questions**: Type in the input at the bottom
3. **View responses**: Scroll through chat history
4. **Clear chat**: Click "Clear" button in header

Enjoy your beautiful, elegant chatbot! 🎨✨

