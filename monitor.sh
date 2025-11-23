#!/bin/bash
# Direct inline monitoring - no file execution needed
# Copy and paste this entire block into your terminal

cd /Volumes/LaCie/Coding-Projects/queryable-slack

LOG_FILE="ingestion_resume.log"
CHECKPOINT_FILE="$HOME/.conductor_ingestion_checkpoint.json"

echo "🔍 Conductor Ingestion Monitor"
echo "================================"
echo ""

# Show process status
PID=$(ps aux | grep -E "python.*conductor.ingest" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$PID" ]; then
    echo "🔄 Process Status:"
    ps -p $PID -o pid,pcpu,pmem,etime 2>/dev/null | tail -1 | awk '{print "   PID:", $1, "| CPU:", $2"% | Memory:", $3"% | Runtime:", $4}'
else
    echo "⚠️  No ingestion process found"
fi

echo ""

# Show checkpoint status
if [ -f "$CHECKPOINT_FILE" ]; then
    echo "📊 Checkpoint Status:"
    python3 << 'PYTHON'
import json
import sys
try:
    with open('$CHECKPOINT_FILE', 'r') as f:
        data = json.load(f)
    completed = len(data.get('completed', {}))
    failed_convos = len(data.get('failed', {}))
    failed_files = data.get('failed_files', {})
    
    print(f'   ✅ Completed conversations: {completed}')
    print(f'   ❌ Failed conversations: {failed_convos}')
    
    if failed_files:
        total = len(failed_files)
        print(f'   ⚠️  Failed files: {total}')
        error_types = {}
        for f, info in failed_files.items():
            err_type = info.get('error_type', 'unknown')
            error_types[err_type] = error_types.get(err_type, 0) + 1
        for err_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f'      - {err_type}: {count}')
    else:
        print('   ✅ No failed files')
except Exception as e:
    print(f'   ⚠️  Error reading checkpoint: {e}')
PYTHON
else
    echo "📝 No checkpoint file found (fresh start)"
fi

echo ""
echo "📋 Live Log (Ctrl+C to exit):"
echo "================================"
echo ""

# Tail the log file
tail -f "$LOG_FILE" 2>/dev/null

