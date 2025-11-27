#!/bin/bash
# Script to add Supabase MCP to Claude settings

SETTINGS_FILE="$HOME/.claude/settings.json"
BACKUP_FILE="$HOME/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)"

# Create backup
cp "$SETTINGS_FILE" "$BACKUP_FILE"
echo "Created backup at: $BACKUP_FILE"

# Create the updated settings file using Python (more reliable JSON handling)
python3 << 'EOF'
import json
import sys

settings_file = "/Users/noahdeskin/.claude/settings.json"

with open(settings_file, 'r') as f:
    settings = json.load(f)

# Add Supabase MCP server
settings['mcpServers']['supabase'] = {
    "url": "https://mcp.supabase.com/mcp?project_ref=gxpcrohsbtndndypagie"
}

# Add permission for Supabase MCP tools
if 'mcp__supabase' not in settings['permissions']['allowedTools']:
    settings['permissions']['allowedTools'].append('mcp__supabase')

# Write back
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("Successfully added Supabase MCP to settings.json")
print("Added 'mcp__supabase' to allowedTools")
EOF

echo ""
echo "Done! Please restart Conductor for changes to take effect."
echo "When you first use Supabase MCP, it will prompt you to authenticate via browser."
