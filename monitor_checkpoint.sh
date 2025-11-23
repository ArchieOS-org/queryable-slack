#!/bin/bash
# Monitor checkpoint status in real-time

CHECKPOINT_FILE="$HOME/.conductor_ingestion_checkpoint.json"

watch -n 5 -c '
echo "📊 Checkpoint Status - $(date)"
echo "================================"
echo ""

if [ -f "'$CHECKPOINT_FILE'" ]; then
    python3 << PYTHON
import json
import sys
from datetime import datetime

try:
    with open("'$CHECKPOINT_FILE'", "r") as f:
        data = json.load(f)
    
    completed = data.get("completed", {})
    failed_convos = data.get("failed", {})
    failed_files = data.get("failed_files", {})
    last_updated = data.get("last_updated", "Never")
    
    print(f"✅ Completed conversations: {len(completed)}")
    print(f"❌ Failed conversations: {len(failed_convos)}")
    print(f"⚠️  Failed files: {len(failed_files)}")
    print(f"🕐 Last updated: {last_updated}")
    print("")
    
    if failed_files:
        print("Failed Files by Error Type:")
        error_types = {}
        for f, info in failed_files.items():
            err_type = info.get("error_type", "unknown")
            error_types[err_type] = error_types.get(err_type, 0) + 1
        
        for err_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"  • {err_type}: {count}")
    
    if completed:
        print("")
        print("Recently Completed:")
        sorted_completed = sorted(completed.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True)[:5]
        for conv, info in sorted_completed:
            sessions = info.get("sessions", 0)
            files = info.get("files", 0)
            print(f"  • {conv}: {sessions} sessions, {files} files")
            
except Exception as e:
    print(f"Error: {e}")
PYTHON
else:
    echo "📝 No checkpoint file found"
fi
'
