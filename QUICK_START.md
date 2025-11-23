# Quick Start Commands

## 🚀 **Start Ingestion**

Copy and paste this command:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && nohup venv/bin/python -u -m conductor.ingest manado/my_export > ~/.conductor_logs/ingestion_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

## 📋 **Monitor (Copy/Paste This)**

```bash
tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1)
```

## 📊 **Monitor with Checkpoint Status**

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && (echo "📊 Checkpoint:"; cat ~/.conductor_ingestion_checkpoint.json 2>/dev/null | python3 -m json.tool | head -20; echo ""; echo "📋 Live Log:"; tail -f $(ls -t ~/.conductor_logs/ingestion_*.log | head -1))
```

## 🔍 **Check if Running**

```bash
ps aux | grep "conductor.ingest" | grep -v grep
```

## 🛑 **Stop Process**

```bash
pkill -f "conductor.ingest"
```

## 📁 **View All Logs**

```bash
ls -lht ~/.conductor_logs/
```

---

**Note**: Logs are stored in `~/.conductor_logs/` (your home directory) to avoid macOS external drive permission issues.

