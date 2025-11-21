# Example Trial Run

This guide shows you how to test Conductor with a small subset of your Slack export before processing the full dataset.

## Step 1: Create a Trial Export

```bash
# Basic trial run (3 conversations, 5 days each)
python -m conductor.trial_run /path/to/slack/export

# Custom trial size
python -m conductor.trial_run /path/to/slack/export \
  --max-conversations 5 \
  --max-days 10

# Create trial export without running ingestion
python -m conductor.trial_run /path/to/slack/export --no-ingest
```

## Step 2: Verify Trial Export

The trial export will be created in `trial_export/` directory (or custom path if specified).

Check the structure:
```bash
ls -la trial_export/
# Should see: users.json, channels.json, and a few conversation directories
```

## Step 3: Test Ingestion (if not auto-run)

If you used `--no-ingest`, run ingestion manually:
```bash
python -m conductor.ingest trial_export/
```

## Step 4: Test Querying

```bash
export ANTHROPIC_API_KEY=your_key_here
python -m conductor.ask "What conversations are in this trial dataset?"
```

## Step 5: If Successful, Run Full Ingestion

Once you've verified everything works:
```bash
python -m conductor.ingest /path/to/slack/export
```

## What Gets Included in Trial Export?

- **Essential metadata**: users.json, channels.json, dms.json, mpims.json
- **Limited conversations**: Only the first N conversations (default: 3)
- **Limited daily files**: Only the first N daily files per conversation (default: 5)
- **All attachments**: All attachment files from included conversations are copied

## Benefits

✅ **Fast**: Test in minutes instead of hours  
✅ **Safe**: Doesn't modify your original export  
✅ **Debuggable**: Small dataset makes it easy to verify results  
✅ **Cost-effective**: Test queries on small dataset before full run  

