# Monitoring Commands - Logging, Visual Progress & Percentage

## 🎯 Best Command: Full Progress Monitor (Recommended)

Shows percentage, progress bar, process stats, and colored live logs:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
./monitor_progress.sh
```

**Features:**
- ✅ Percentage completion (X/Y conversations)
- ✅ Visual progress bar
- ✅ Process CPU/Memory/Runtime stats
- ✅ Total sessions and files processed
- ✅ Colored live logs (auto-refreshes progress every 10s)
- ✅ Failed files count

---

## 📊 Quick Progress Check (One-Time)

See current percentage and stats without live logs:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
source venv312/bin/activate
python3 << 'EOF'
import json
from pathlib import Path

checkpoint = Path.home() / ".conductor_ingestion_checkpoint.json"
export_path = Path("manado/my_export")

# Load checkpoint
with open(checkpoint) as f:
    data = json.load(f)

completed = len(data.get("completed", {}))
failed = len(data.get("failed", {}))
failed_files = len(data.get("failed_files", {}))

# Calculate total
total = 0
for f in ["channels.json", "dms.json", "mpims.json"]:
    p = export_path / f
    if p.exists():
        with open(p) as jf:
            total += len(json.load(jf))

# Calculate percentage
if total > 0:
    processed = completed + failed
    pct = (processed / total) * 100
    bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
    print(f"\n📊 Progress: {processed}/{total} ({pct:.1f}%)")
    print(f"[{bar}]")
    print(f"✅ Completed: {completed} | ❌ Failed: {failed} | ⏳ Remaining: {total - processed}")
    print(f"📦 Sessions: {sum(i.get('sessions', 0) for i in data.get('completed', {}).values())}")
    print(f"📄 Files: {sum(i.get('files', 0) for i in data.get('completed', {}).values())}")
else:
    print(f"✅ Completed: {completed} | ❌ Failed: {failed}")
EOF
```

---

## 📋 Live Logs Only (Simple)

Just watch the logs with colors:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
tail -f ingestion_resume.log | grep --color=always -E "✅|❌|⚠️|🔄|📊|Processing|Step|completed|failed|Retrying|^"
```

---

## 🔄 Checkpoint Status (Updates Every 5 Seconds)

Watch checkpoint stats update in real-time:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
./monitor_checkpoint.sh
```

---

## 📈 Process + Progress (Combined)

See process stats and progress together:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
watch -n 5 -c '
echo "🔄 Process:"
ps aux | grep "conductor.ingest" | grep -v grep | awk "{print \"   PID:\", \$2, \"| CPU:\", \$3\"% | Memory:\", \$4\"% | Runtime:\", \$10}"
echo ""
python3 << PYTHON
import json
from pathlib import Path
checkpoint = Path.home() / ".conductor_ingestion_checkpoint.json"
export_path = Path("/Volumes/LaCie/Coding-Projects/queryable-slack/manado/my_export")
with open(checkpoint) as f:
    data = json.load(f)
completed = len(data.get("completed", {}))
failed = len(data.get("failed", {}))
total = 0
for f in ["channels.json", "dms.json", "mpims.json"]:
    p = export_path / f
    if p.exists():
        import json as j
        with open(p) as jf:
            total += len(j.load(jf))
if total > 0:
    pct = ((completed + failed) / total) * 100
    print(f"📊 {completed + failed}/{total} ({pct:.1f}%) | ✅ {completed} | ❌ {failed}")
else:
    print(f"📊 ✅ {completed} | ❌ {failed}")
PYTHON
'
```

---

## 🎨 Split Terminal View (Advanced)

Use `tmux` to split terminal:

```bash
# Start tmux session
tmux new-session -d -s ingestion

# Split horizontally
tmux split-window -h

# Left pane: Progress monitor
tmux send-keys -t 0 "cd /Volumes/LaCie/Coding-Projects/queryable-slack && ./monitor_progress.sh" Enter

# Right pane: Checkpoint details
tmux send-keys -t 1 "cd /Volumes/LaCie/Coding-Projects/queryable-slack && watch -n 5 'cat ~/.conductor_ingestion_checkpoint.json | python3 -m json.tool | head -50'" Enter

# Attach to session
tmux attach -t ingestion
```

---

## 📱 Quick Status Check

One-liner to see current status:

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack && python3 -c "import json; d=json.load(open('$HOME/.conductor_ingestion_checkpoint.json')); print(f\"✅ {len(d['completed'])} | ❌ {len(d['failed'])} | ⚠️ {len(d['failed_files'])}\")"
```

---

## 🎯 What Each Command Shows

| Command | Percentage | Progress Bar | Process Stats | Live Logs | Auto-Refresh |
|---------|-----------|--------------|---------------|-----------|--------------|
| `monitor_progress.sh` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Quick Progress Check | ✅ | ✅ | ❌ | ❌ | ❌ |
| Live Logs Only | ❌ | ❌ | ❌ | ✅ | ❌ |
| Checkpoint Status | ❌ | ❌ | ❌ | ❌ | ✅ |
| Process + Progress | ✅ | ❌ | ✅ | ❌ | ✅ |

---

## 💡 Tips

- **Best for monitoring**: Use `./monitor_progress.sh` - it has everything
- **Quick check**: Use the "Quick Progress Check" command
- **Background monitoring**: Run `./monitor_progress.sh` in a separate terminal
- **Exit any monitor**: Press `Ctrl+C`

---

## 🔍 Understanding the Output

- **Percentage**: Based on total conversations discovered vs completed+failed
- **Progress Bar**: Visual representation (█ = done, ░ = remaining)
- **Completed**: Successfully processed conversations
- **Failed**: Conversations that failed (will be retried)
- **Remaining**: Total - (Completed + Failed)
- **Sessions**: Total conversation sessions created
- **Files**: Total files processed from attachments

