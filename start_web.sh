#!/bin/bash

# Start Vector Database Chatbot Web App
# Starts FastAPI backend and React frontend, opens browser

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Vector Database Chatbot Web App...${NC}\n"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv312" ]; then
    source venv312/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
elif [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠ No virtual environment found. Please create one first.${NC}"
    exit 1
fi

# Check if FastAPI dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing FastAPI dependencies...${NC}"
    pip install fastapi uvicorn[standard] > /dev/null 2>&1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠ Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Check if npm dependencies are installed
if [ ! -d "web/node_modules" ]; then
    echo -e "${YELLOW}Installing React dependencies...${NC}"
    cd web
    npm install
    cd ..
fi

# Get local IP address for network access
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

# Start FastAPI backend in background
echo -e "${BLUE}Starting FastAPI backend on port 8000...${NC}"
python -m uvicorn web_api:app --host 0.0.0.0 --port 8000 --reload > /tmp/fastapi.log 2>&1 &
FASTAPI_PID=$!

# Wait for FastAPI to start
sleep 2

# Start React frontend
echo -e "${BLUE}Starting React frontend on port 3000...${NC}"
cd web
npm run dev > /tmp/react.log 2>&1 &
REACT_PID=$!
cd ..

# Wait for React to start
sleep 3

# Display URLs
echo -e "\n${GREEN}✓ Backend running:${NC}"
echo -e "  - Local: http://localhost:8000"
echo -e "  - Network: http://${LOCAL_IP}:8000"
echo -e "\n${GREEN}✓ Frontend running:${NC}"
echo -e "  - Local: http://localhost:3000"
echo -e "  - Network: http://${LOCAL_IP}:3000"
echo -e "\n${YELLOW}📱 Access from iPhone: http://${LOCAL_IP}:3000${NC}\n"

# Try to open browser (works on macOS, Linux with xdg-open, Windows with start)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:3000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:3000 2>/dev/null || true
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    start http://localhost:3000
fi

echo -e "${GREEN}🎉 Web app is running!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}\n"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping servers...${NC}"
    kill $FASTAPI_PID 2>/dev/null || true
    kill $REACT_PID 2>/dev/null || true
    echo -e "${GREEN}✓ Servers stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Wait for processes
wait

