# Context7 Quick Start - Optimal AI Responses

## ✅ What Was Configured

1. **CLAUDE.md** - Added Context7 auto-invoke rules
2. **manado/promt.xml** - Added Context7 auto-invoke configuration
3. **.cursorrules** - Created Cursor-specific auto-invoke rules
4. **CONTEXT7_SETUP.md** - Comprehensive setup guide

## 🚀 Quick Setup (3 Steps)

### Step 1: Get Context7 API Key
1. Visit https://context7.com/dashboard
2. Sign up/login
3. Create API key (starts with `ctx7sk_`)

### Step 2: Add to Environment
Add to your `.env` file:
```bash
CONTEXT7_API_KEY=ctx7sk_your_actual_api_key_here
```

### Step 3: Configure Cursor MCP (if using Cursor)

Create/edit `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {
        "CONTEXT7_API_KEY": "ctx7sk_your_actual_api_key_here"
      }
    }
  }
}
```

Then restart Cursor.

## ✨ How It Works Now

With Context7 configured, the AI will **automatically**:

1. **Use Context7 for library docs** - No need to ask "use context7"
2. **Resolve library IDs** - Automatically finds correct library identifiers
3. **Get up-to-date docs** - Fetches latest documentation from sources
4. **Provide accurate code** - Uses real examples from library docs

## 📝 Example Usage

**Before (manual):**
```
You: "How do I use ChromaDB?"
AI: [Uses training data, may be outdated]
```

**After (automatic):**
```
You: "How do I use ChromaDB?"
AI: [Automatically calls Context7, gets latest docs, provides accurate code]
```

## 🎯 Best Practices

### Specify Library IDs When Known
```
"Use library /chromadb/chromadb for vector storage"
"Use library /pydantic/pydantic for data validation"
```

### Request Specific Topics
```
"Get ChromaDB docs on persistent client setup"
"Get Pydantic v2 field validation examples"
```

### Use Version-Specific Requests
```
"Use library /vercel/next.js/v15.1.0"
```

## 🔍 Verification

Test that Context7 is working:

1. Ask: "How do I create a ChromaDB PersistentClient?"
2. AI should automatically:
   - Call `resolve-library-id` for "chromadb"
   - Call `get-library-docs` with resolved ID
   - Provide up-to-date documentation

## 📚 More Information

- Full setup guide: See `CONTEXT7_SETUP.md`
- Project guidelines: See `CLAUDE.md`
- Cursor configuration: See `.cursorrules`

## 🆘 Troubleshooting

**Context7 not being used?**
- Check MCP server is configured in Cursor
- Verify API key is set correctly
- Restart Cursor after configuration
- Check auto-invoke rules in `.cursorrules`

**API key issues?**
- Verify key starts with `ctx7sk_`
- Check key hasn't expired
- Get free key at https://context7.com/dashboard

**Rate limiting?**
- Get free API key for higher limits
- Check usage at https://context7.com/dashboard

## 🎉 Benefits

- ✅ Always up-to-date documentation
- ✅ No outdated code examples
- ✅ Accurate import paths
- ✅ Version-specific information
- ✅ Real library examples
- ✅ Automatic invocation (no manual requests needed)

