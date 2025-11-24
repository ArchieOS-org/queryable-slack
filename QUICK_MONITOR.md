# Quick Monitor Commands

## Option 1: Direct Command (No Script Needed)

Run this directly in your terminal:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && tail -f ingestion_resume.log
```

## Option 2: With Checkpoint Status

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && bash -c '
echo "📊 Checkpoint Status:"
cat ~/.conductor_ingestion_checkpoint.json 2>/dev/null | python3 -m json.tool | head -30
echo ""
echo "📋 Live Log:"
tail -f ingestion_resume.log
'
```

## Option 3: Run Script with bash

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && bash monitor_ingestion.sh
```

## Option 4: Simple One-Liner

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && tail -f ingestion_resume.log | grep --color=always -E "✅|❌|⚠️|🔄|📊|Checkpoint|Processing|Step|completed|failed|Retrying|^"
```

## Option 5: Check Process + Logs

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && while true; do clear; echo "=== $(date) ==="; ps aux | grep "conductor.ingest" | grep -v grep; echo ""; tail -20 ingestion_resume.log; sleep 5; done
```

## If Permission Issues Persist

Use `bash` explicitly:
```bash
bash /Volumes/LaCie/Coding-Projects/queryable-slack/monitor_ingestion.sh
```

Or run the commands directly without a script file.




