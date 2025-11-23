#!/bin/bash
# Live monitoring command - works from anywhere, no permission issues

# Find latest log file
LATEST_LOG=$(ls -t ~/.conductor_logs/ingestion_*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "⚠️  No log files found in ~/.conductor_logs/"
    echo "   Waiting for ingestion to start..."
    # Wait for log file to appear
    while [ ! -f "$LATEST_LOG" ]; do
        LATEST_LOG=$(ls -t ~/.conductor_logs/ingestion_*.log 2>/dev/null | head -1)
        sleep 2
    done
fi

echo "🔍 Monitoring: $LATEST_LOG"
echo "================================"
echo ""

# Show checkpoint status if available
if [ -f ~/.conductor_ingestion_checkpoint.json ]; then
    echo "📊 Checkpoint Status:"
    python3 << 'PYTHON'
import json
try:
    with open('$HOME/.conductor_ingestion_checkpoint.json', 'r') as f:
        data = json.load(f)
    completed = len(data.get('completed', {}))
    failed_convos = len(data.get('failed', {}))
    failed_files = data.get('failed_files', {})
    print(f'   ✅ Completed: {completed}')
    print(f'   ❌ Failed convos: {failed_convos}')
    print(f'   ⚠️  Failed files: {len(failed_files)}')
    if failed_files:
        error_types = {}
        for info in failed_files.values():
            err_type = info.get('error_type', 'unknown')
            error_types[err_type] = error_types.get(err_type, 0) + 1
        for err_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f'      - {err_type}: {count}')
except Exception as e:
    print(f'   ⚠️  Error: {e}')
PYTHON
    echo ""
fi

# Show process status
PID=$(ps aux | grep -E "python.*conductor.ingest" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$PID" ]; then
    echo "🔄 Process: PID $PID (running)"
else
    echo "⚠️  No active ingestion process"
fi

echo ""
echo "📋 Live Log (Ctrl+C to exit):"
echo "================================"
echo ""

# Tail with color highlighting
tail -f "$LATEST_LOG" 2>/dev/null | while IFS= read -r line; do
    if echo "$line" | grep -qE "✅|SUCCESS|completed"; then
        echo -e "\033[32m$line\033[0m"
    elif echo "$line" | grep -qE "❌|ERROR|Failed|failed"; then
        echo -e "\033[31m$line\033[0m"
    elif echo "$line" | grep -qE "⚠️|WARNING|warning"; then
        echo -e "\033[33m$line\033[0m"
    elif echo "$line" | grep -qE "🔄|Retrying|retry"; then
        echo -e "\033[36m$line\033[0m"
    elif echo "$line" | grep -qE "📊|Checkpoint|Processing|Step|\[.*/.*\]"; then
        echo -e "\033[35m$line\033[0m"
    else
        echo "$line"
    fi
done

