#!/bin/bash
# Start ingestion with proper logging to a local file (works on external drives)

cd /Volumes/LaCie/Coding-Projects/queryable-slack

# Create log file in home directory (not on external drive to avoid permission issues)
LOG_DIR="$HOME/.conductor_logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/ingestion_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 Starting Conductor Ingestion"
echo "📋 Log file: $LOG_FILE"
echo ""

# Activate venv and run with unbuffered output
source venv/bin/activate 2>/dev/null || venv/bin/python -m conductor.ingest "$@" 2>&1 | tee "$LOG_FILE" &
PID=$!

echo "✅ Process started (PID: $PID)"
echo "📋 Monitor with: tail -f $LOG_FILE"
echo ""

# Show initial log output
sleep 3
tail -20 "$LOG_FILE" 2>/dev/null || echo "Waiting for process to start..."




