#!/bin/bash
# Monitor ingestion process with logs and visuals

LOG_FILE="ingestion_resume.log"
CHECKPOINT_FILE="$HOME/.conductor_ingestion_checkpoint.json"

echo "🔍 Conductor Ingestion Monitor"
echo "================================"
echo ""

# Function to show checkpoint stats
show_checkpoint() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        echo "📊 Checkpoint Status:"
        python3 -c "
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
        # Count by error type
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
" 2>/dev/null || echo "   ⚠️  Could not read checkpoint"
    else
        echo "   📝 No checkpoint file found (fresh start)"
    fi
}

# Function to show process status
show_process() {
    PID=$(ps aux | grep -E "python.*conductor.ingest" | grep -v grep | awk '{print $2}' | head -1)
    if [ -n "$PID" ]; then
        STATS=$(ps -p $PID -o pid,pcpu,pmem,etime,command 2>/dev/null | tail -1)
        echo "🔄 Process Status:"
        echo "   PID: $PID"
        echo "   Stats: $STATS" | awk '{print "   CPU:", $2"%, Memory:", $3"%, Runtime:", $4}'
    else
        echo "⚠️  No ingestion process found"
    fi
}

# Show initial status
show_process
echo ""
show_checkpoint
echo ""
echo "📋 Live Log (Ctrl+C to exit):"
echo "================================"
echo ""

# Tail the log file with colors
tail -f "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
    # Color code different log levels
    if echo "$line" | grep -qE "✅|SUCCESS|completed"; then
        echo -e "\033[32m$line\033[0m"  # Green
    elif echo "$line" | grep -qE "❌|ERROR|Failed|failed"; then
        echo -e "\033[31m$line\033[0m"  # Red
    elif echo "$line" | grep -qE "⚠️|WARNING|warning"; then
        echo -e "\033[33m$line\033[0m"  # Yellow
    elif echo "$line" | grep -qE "🔄|Retrying|retry"; then
        echo -e "\033[36m$line\033[0m"  # Cyan
    elif echo "$line" | grep -qE "📊|Checkpoint|Processing|Step"; then
        echo -e "\033[35m$line\033[0m"  # Magenta
    else
        echo "$line"
    fi
done
