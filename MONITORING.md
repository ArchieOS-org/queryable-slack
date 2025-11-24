# Monitoring Commands

## Quick Start

Run this in your Mac terminal to monitor the ingestion process:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
./monitor_ingestion.sh
```

## Individual Commands

### 1. Live Log Monitoring (Colored Output)
```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
tail -f ingestion_resume.log
```

### 2. Checkpoint Status Monitor (Updates Every 5 Seconds)
```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
./monitor_checkpoint.sh
```

### 3. Process Status + Logs (Combined)
```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
watch -n 2 'ps aux | grep "conductor.ingest" | grep -v grep && echo "---" && tail -20 ingestion_resume.log'
```

### 4. Simple Log Tail with Grep (Filter Important Lines)
```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
tail -f ingestion_resume.log | grep -E "✅|❌|⚠️|🔄|📊|Checkpoint|Processing|Step|completed|failed|Retrying"
```

### 5. Checkpoint Stats Only
```bash
cat ~/.conductor_ingestion_checkpoint.json | python3 -m json.tool | grep -E "completed|failed|error_type" | head -50
```

## Advanced: Split Terminal View

If you have `tmux` or `screen`, you can split your terminal:

**With tmux:**
```bash
tmux new-session -d -s ingestion
tmux split-window -h
tmux send-keys -t 0 "cd /Volumes/LaCie/Coding-Projects/queryable-slack && tail -f ingestion_resume.log" Enter
tmux send-keys -t 1 "cd /Volumes/LaCie/Coding-Projects/queryable-slack && ./monitor_checkpoint.sh" Enter
tmux attach -t ingestion
```

## What to Look For

- **✅ Completed conversations**: Shows progress
- **❌ Failed conversations**: Will be retried automatically
- **⚠️ Failed files**: Will be retried automatically
- **🔄 Retrying**: Files being retried from previous run
- **📊 Checkpoint Status**: Summary of what's been processed
- **Processing conversations**: Main progress indicator

## Exit Monitoring

Press `Ctrl+C` to exit any monitoring command.




