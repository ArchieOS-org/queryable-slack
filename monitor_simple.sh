#!/bin/bash
# Simple monitor - can be run with bash directly

LOG_FILE="/Volumes/LaCie/Coding-Projects/queryable-slack/ingestion_resume.log"
CHECKPOINT_FILE="$HOME/.conductor_ingestion_checkpoint.json"

echo "🔍 Conductor Ingestion Monitor"
echo "================================"
echo ""

# Show process status
PID=$(ps aux | grep -E "python.*conductor.ingest" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$PID" ]; then
    echo "🔄 Process Status:"
    ps -p $PID -o pid,pcpu,pmem,etime,command 2>/dev/null | tail -1 | awk '{print "   PID:", $1, "| CPU:", $2"% | Memory:", $3"% | Runtime:", $4}'
else
    echo "⚠️  No ingestion process found"
fi

echo ""
echo "📋 Live Log (Ctrl+C to exit):"
echo "================================"
echo ""

# Tail the log file
tail -f "$LOG_FILE" 2>/dev/null
