#!/bin/bash
# Monitor ingestion with percentage progress, ETA, and visual progress bar
# Uses Context7 Rich library patterns for progress monitoring

LOG_FILE="/Volumes/LaCie/Coding-Projects/queryable-slack/ingestion_resume.log"
CHECKPOINT_FILE="$HOME/.conductor_ingestion_checkpoint.json"
EXPORT_PATH="/Users/noahdeskin/slack-vectoriezed-data/slack_export"

# Track start time for ETA calculation
START_TIME_FILE="/tmp/conductor_monitor_start.$$"
echo $(date +%s) > "$START_TIME_FILE"

# Function to calculate total conversations
get_total_conversations() {
    if [ -d "$EXPORT_PATH" ]; then
        channels=$(find "$EXPORT_PATH" -name "channels.json" -exec python3 -c "import json, sys; print(len(json.load(open(sys.argv[1]))))" {} \; 2>/dev/null | head -1)
        dms=$(find "$EXPORT_PATH" -name "dms.json" -exec python3 -c "import json, sys; print(len(json.load(open(sys.argv[1]))))" {} \; 2>/dev/null | head -1)
        mpims=$(find "$EXPORT_PATH" -name "mpims.json" -exec python3 -c "import json, sys; print(len(json.load(open(sys.argv[1]))))" {} \; 2>/dev/null | head -1)
        
        total=$((channels + dms + mpims))
        echo $total
    else
        echo "0"
    fi
}

# Function to format time duration
format_duration() {
    local seconds=$1
    if [ $seconds -lt 60 ]; then
        echo "${seconds}s"
    elif [ $seconds -lt 3600 ]; then
        local mins=$((seconds / 60))
        local secs=$((seconds % 60))
        echo "${mins}m ${secs}s"
    else
        local hours=$((seconds / 3600))
        local mins=$(((seconds % 3600) / 60))
        local secs=$((seconds % 60))
        echo "${hours}h ${mins}m ${secs}s"
    fi
}

# Function to parse process runtime (format: HH:MM:SS or MM:SS)
parse_runtime() {
    local runtime=$1
    local total_seconds=0
    
    # Parse HH:MM:SS or MM:SS format
    if echo "$runtime" | grep -qE "^[0-9]+:[0-9]+:[0-9]+$"; then
        # HH:MM:SS format
        hours=$(echo "$runtime" | cut -d: -f1)
        mins=$(echo "$runtime" | cut -d: -f2)
        secs=$(echo "$runtime" | cut -d: -f3)
        total_seconds=$((hours * 3600 + mins * 60 + secs))
    elif echo "$runtime" | grep -qE "^[0-9]+:[0-9]+$"; then
        # MM:SS format
        mins=$(echo "$runtime" | cut -d: -f1)
        secs=$(echo "$runtime" | cut -d: -f2)
        total_seconds=$((mins * 60 + secs))
    elif echo "$runtime" | grep -qE "^[0-9]+$"; then
        # Just seconds
        total_seconds=$runtime
    fi
    
    echo $total_seconds
}

# Function to show progress with percentage and ETA
show_progress() {
    # Get process runtime for ETA calculation
    PID=$(ps aux | grep -E "python.*conductor.ingest" | grep -v grep | awk '{print $2}' | head -1)
    PROCESS_RUNTIME=""
    PROCESS_ELAPSED_SECONDS=0
    
    if [ -n "$PID" ]; then
        PROCESS_RUNTIME=$(ps -p $PID -o etime= 2>/dev/null | tr -d ' ')
        if [ -n "$PROCESS_RUNTIME" ]; then
            PROCESS_ELAPSED_SECONDS=$(parse_runtime "$PROCESS_RUNTIME")
        fi
    fi
    
    # Get total conversations
    TOTAL_CONVERSATIONS=$(get_total_conversations)
    
    if [ -f "$CHECKPOINT_FILE" ]; then
        python3 << PYTHON
import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

checkpoint_file = "$CHECKPOINT_FILE"
export_path = "$EXPORT_PATH"
process_elapsed = int("$PROCESS_ELAPSED_SECONDS" or "0")
total_conversations = int("$TOTAL_CONVERSATIONS" or "0")

try:
    # Load checkpoint
    with open(checkpoint_file, 'r') as f:
        data = json.load(f)
    
    completed = len(data.get("completed", {}))
    failed = len(data.get("failed", {}))
    failed_files = len(data.get("failed_files", {}))
    last_updated_str = data.get("last_updated", None)
    
    # Use total from parameter or calculate
    total = total_conversations
    if total == 0 and os.path.exists(export_path):
        try:
            channels_file = Path(export_path) / "channels.json"
            dms_file = Path(export_path) / "dms.json"
            mpims_file = Path(export_path) / "mpims.json"
            
            if channels_file.exists():
                with open(channels_file) as f:
                    total += len(json.load(f))
            if dms_file.exists():
                with open(dms_file) as f:
                    total += len(json.load(f))
            if mpims_file.exists():
                with open(mpims_file) as f:
                    total += len(json.load(f))
        except:
            pass
    
    # Calculate percentage and ETA
    if total > 0:
        processed = completed + failed
        percentage = (processed / total) * 100
        remaining = total - processed
        
        # Use process runtime for elapsed time (more accurate)
        elapsed_seconds = process_elapsed if process_elapsed > 0 else 0
        
        # Calculate rate and ETA
        eta_seconds = 0
        rate_per_second = 0
        
        if processed > 0 and elapsed_seconds > 0:
            rate_per_second = processed / elapsed_seconds
            if rate_per_second > 0 and remaining > 0:
                eta_seconds = int(remaining / rate_per_second)
        elif elapsed_seconds > 0 and processed == 0:
            # Process running but no progress yet - estimate based on time per conversation
            # Assume average 2-5 minutes per conversation (conservative estimate)
            avg_seconds_per_conv = 180  # 3 minutes average
            eta_seconds = total * avg_seconds_per_conv - elapsed_seconds
            rate_per_second = 1.0 / avg_seconds_per_conv if avg_seconds_per_conv > 0 else 0
        
        # Format elapsed time
        elapsed_str = ""
        if elapsed_seconds > 0:
            if elapsed_seconds < 60:
                elapsed_str = f"{elapsed_seconds}s"
            elif elapsed_seconds < 3600:
                mins = elapsed_seconds // 60
                secs = elapsed_seconds % 60
                elapsed_str = f"{mins}m {secs}s"
            else:
                hours = elapsed_seconds // 3600
                mins = (elapsed_seconds % 3600) // 60
                secs = elapsed_seconds % 60
                elapsed_str = f"{hours}h {mins}m {secs}s"
        
        # Format ETA
        eta_str = ""
        if eta_seconds > 0:
            if eta_seconds < 60:
                eta_str = f"{eta_seconds}s"
            elif eta_seconds < 3600:
                mins = eta_seconds // 60
                secs = eta_seconds % 60
                eta_str = f"{mins}m {secs}s"
            else:
                hours = eta_seconds // 3600
                mins = (eta_seconds % 3600) // 60
                secs = eta_seconds % 60
                eta_str = f"{hours}h {mins}m {secs}s"
        elif processed == 0 and elapsed_seconds > 0:
            # Still estimating
            eta_str = "calculating..."
        
        # Format rate
        rate_str = ""
        if rate_per_second > 0:
            if rate_per_second < 0.1:
                rate_str = f"{rate_per_second * 60:.2f} conv/min"
            else:
                rate_str = f"{rate_per_second:.2f} conv/s"
        
        print(f"\033[1m📊 Progress: {processed}/{total} conversations ({percentage:.1f}%)\033[0m")
        print(f"   ✅ Completed: {completed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏳ Remaining: {remaining}")
        
        # Visual progress bar (50 chars wide)
        bar_width = 50
        filled = int((percentage / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"   [{bar}] {percentage:.1f}%")
        
        # Time information - ALWAYS show ETA
        print(f"\n   ⏱️  Elapsed: {elapsed_str if elapsed_str else '0s'}", end="")
        if rate_str:
            print(f" | Rate: {rate_str}", end="")
        print(f" | ⏰ ETA: {eta_str if eta_str else 'calculating...'}")
        
    else:
        print(f"\033[1m📊 Progress: {completed} completed, {failed} failed\033[0m")
        print(f"   (Total conversations: Unknown)")
    
    print(f"\n   ⚠️  Failed files: {failed_files}")
    if last_updated_str:
        print(f"   🕐 Last updated: {last_updated_str}")
    
    # Show total sessions and files processed
    total_sessions = sum(info.get("sessions", 0) for info in data.get("completed", {}).values())
    total_files = sum(info.get("files", 0) for info in data.get("completed", {}).values())
    print(f"\n   📦 Total sessions processed: {total_sessions}")
    print(f"   📄 Total files processed: {total_files}")
    
except Exception as e:
    print(f"Error reading checkpoint: {e}")
    import traceback
    traceback.print_exc()
PYTHON
    else
        # Check if process is running but checkpoint doesn't exist yet
        if [ -n "$PID" ] && [ "$TOTAL_CONVERSATIONS" -gt 0 ]; then
            # Calculate ETA even without checkpoint
            python3 << PYTHON
import sys
total = int("$TOTAL_CONVERSATIONS")
elapsed = int("$PROCESS_ELAPSED_SECONDS" or "0")

# Estimate based on average time per conversation
avg_seconds_per_conv = 180  # 3 minutes conservative estimate
estimated_total_seconds = total * avg_seconds_per_conv
eta_seconds = max(0, estimated_total_seconds - elapsed)

# Format elapsed
elapsed_str = ""
if elapsed > 0:
    if elapsed < 60:
        elapsed_str = f"{elapsed}s"
    elif elapsed < 3600:
        mins = elapsed // 60
        secs = elapsed % 60
        elapsed_str = f"{mins}m {secs}s"
    else:
        hours = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        elapsed_str = f"{hours}h {mins}m {secs}s"

# Format ETA
eta_str = ""
if eta_seconds > 0:
    if eta_seconds < 60:
        eta_str = f"{eta_seconds}s"
    elif eta_seconds < 3600:
        mins = eta_seconds // 60
        secs = eta_seconds % 60
        eta_str = f"{mins}m {secs}s"
    else:
        hours = eta_seconds // 3600
        mins = (eta_seconds % 3600) // 60
        secs = eta_seconds % 60
        eta_str = f"{hours}h {mins}m {secs}s"

print(f"\033[1m📊 Progress: 0/{total} conversations (0.0%)\033[0m")
print(f"   ✅ Completed: 0")
print(f"   ❌ Failed: 0")
print(f"   ⏳ Remaining: {total}")
print(f"   [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0.0%")
print(f"\n   ⏱️  Elapsed: {elapsed_str if elapsed_str else '0s'} | ⏰ ETA: {eta_str if eta_str else 'calculating...'}")
print(f"\n   📝 Checkpoint not created yet (process starting...)")
print(f"   Waiting for first conversation to complete...")
PYTHON
        elif [ -n "$PID" ]; then
            echo "📝 Checkpoint not created yet (process starting...)"
            echo "   Waiting for first conversation to complete..."
        else
            echo "📝 No checkpoint file found (fresh start)"
        fi
    fi
}

# Function to show process status
show_process() {
    PID=$(ps aux | grep -E "python.*conductor.ingest" | grep -v grep | awk '{print $2}' | head -1)
    if [ -n "$PID" ]; then
        STATS=$(ps -p $PID -o pid,pcpu,pmem,etime,rss 2>/dev/null | tail -1)
        if [ -n "$STATS" ]; then
            PID_VAL=$(echo $STATS | awk '{print $1}')
            CPU=$(echo $STATS | awk '{print $2}')
            MEM=$(echo $STATS | awk '{print $3}')
            TIME=$(echo $STATS | awk '{print $4}')
            RSS=$(echo $STATS | awk '{print $5}')
            MEM_MB=$((RSS / 1024))
            echo "🔄 Process Status:"
            echo "   PID: $PID_VAL | CPU: ${CPU}% | Memory: ${MEM_MB}MB (${MEM}%) | Runtime: $TIME"
        fi
    else
        echo "⚠️  No ingestion process running"
    fi
}

# Cleanup function
cleanup() {
    rm -f "$START_TIME_FILE" 2>/dev/null
    kill $REFRESH_PID 2>/dev/null
    exit 0
}

trap cleanup EXIT INT TERM

# Clear screen and show header
clear
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Conductor Ingestion Progress Monitor                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Show initial status
show_process
echo ""
show_progress
echo ""
echo "📋 Live Log (Press Ctrl+C to exit):"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Tail log with colors and auto-refresh progress every 5 seconds
(
    while true; do
        sleep 5
        # Clear progress area and refresh
        tput sc
        tput cup 2 0
        show_process
        echo ""
        show_progress
        echo ""
        tput rc
    done
) &
REFRESH_PID=$!

# Tail the log file with colors
tail -f "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
    # Color code different log levels
    if echo "$line" | grep -qE "✅|SUCCESS|completed|Stored.*sessions"; then
        echo -e "\033[32m$line\033[0m"  # Green
    elif echo "$line" | grep -qE "❌|ERROR|Failed|failed|Exception"; then
        echo -e "\033[31m$line\033[0m"  # Red
    elif echo "$line" | grep -qE "⚠️|WARNING|warning|Skipped"; then
        echo -e "\033[33m$line\033[0m"  # Yellow
    elif echo "$line" | grep -qE "🔄|Retrying|retry|Processing"; then
        echo -e "\033[36m$line\033[0m"  # Cyan
    elif echo "$line" | grep -qE "📊|Checkpoint|Step|Discovered|conversations"; then
        echo -e "\033[35m$line\033[0m"  # Magenta
    elif echo "$line" | grep -qE "📦|📄|💾|📝"; then
        echo -e "\033[34m$line\033[0m"  # Blue
    else
        echo "$line"
    fi
done

# Cleanup on exit
cleanup
