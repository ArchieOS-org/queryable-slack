# Start and Monitor Ingestion

## ✅ **Start Ingestion (Run This First)**

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && venv/bin/python -u -m conductor.ingest manado/my_export 2>&1 | tee ~/.conductor_logs/ingestion_$(date +%Y%m%d_%H%M%S).log &
```

## 📋 **Monitor (Run This in Another Terminal)**

### **Option 1: Simple Tail (Recommended)**

```bash
tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1)
```

### **Option 2: With Checkpoint Status**

```bash
bash /Volumes/LaCie/Coding-Projects/queryable-slack/monitor_live.sh
```

### **Option 3: Filter Important Lines**

```bash
tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1) | grep --color=always -E "✅|❌|⚠️|🔄|📊|Checkpoint|Processing|Step|completed|failed|Retrying|\[.*/.*\]"
```

### **Option 4: One-Liner with Status**

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && (echo "📊 Checkpoint:"; cat ~/.conductor_ingestion_checkpoint.json 2>/dev/null | python3 -m json.tool | head -15; echo ""; echo "📋 Log:"; tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1))
```

## 🔍 **Check Process Status**

```bash
ps aux | grep "conductor.ingest" | grep -v grep
```

## 📁 **View All Logs**

```bash
ls -lht ~/.conductor_logs/
```

## 🎯 **Key Features**

- ✅ Logs stored in `~/.conductor_logs/` (home directory) - no permission issues
- ✅ Automatically detects TTY vs file output
- ✅ Rich progress bars in interactive terminals
- ✅ Simple text progress when redirected to file
- ✅ Checkpoint system tracks progress and retries failed files

