# Simple Monitoring Commands

## ✅ **RECOMMENDED: Monitor from Home Directory**

The log file is now stored in `~/.conductor_logs/` (your home directory) to avoid macOS external drive permission issues.

### **Monitor Live Log:**

```bash
tail -f ~/.conductor_logs/ingestion_*.log | tail -1
```

Or find the latest log:

```bash
LATEST=$(ls -t ~/.conductor_logs/ingestion_*.log | head -1) && tail -f "$LATEST"
```

### **One-Liner to Find and Monitor Latest:**

```bash
tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1)
```

### **With Checkpoint Status:**

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && (echo "📊 Checkpoint:"; cat ~/.conductor_ingestion_checkpoint.json 2>/dev/null | python3 -m json.tool | head -20; echo ""; echo "📋 Latest Log:"; tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1))
```

### **Filter Important Lines:**

```bash
tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1) | grep --color=always -E "✅|❌|⚠️|🔄|📊|Checkpoint|Processing|Step|completed|failed|Retrying|\[.*/.*\]"
```

### **Check Process Status:**

```bash
ps aux | grep "conductor.ingest" | grep -v grep
```

### **View All Logs:**

```bash
ls -lht ~/.conductor_logs/
```

## Why This Works

- Logs are stored in `~/.conductor_logs/` (home directory) - no external drive permission issues
- Process detects TTY vs file output and adapts
- Simple text-based progress when redirected to file
- Rich progress bars when running in interactive terminal




