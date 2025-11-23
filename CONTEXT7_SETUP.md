# Context7 Setup Guide for Optimal Responses

This guide helps you configure Context7 for optimal AI responses when working with the queryable-slack project.

## What is Context7?

Context7 provides up-to-date, version-specific documentation and code examples directly from library sources. This prevents outdated information and hallucinations in AI responses.

## Setup Steps

### 1. Get Your Context7 API Key

1. Visit https://context7.com/dashboard
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key (starts with `ctx7sk_`)

### 2. Configure Environment Variables

Add your Context7 API key to your `.env` file:

```bash
# Add to .env file
CONTEXT7_API_KEY=ctx7sk_your_actual_api_key_here
```

Or export it in your shell:

```bash
export CONTEXT7_API_KEY=ctx7sk_your_actual_api_key_here
```

### 3. Configure Cursor MCP Server

If you're using Cursor, add Context7 MCP server configuration:

**Option A: Using Environment Variable (Recommended)**

Create or edit `~/.cursor/mcp.json` (or Cursor Settings > MCP Servers):

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

**Option B: Using Remote HTTP Server**

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "ctx7sk_your_actual_api_key_here"
      }
    }
  }
}
```

**Option C: Using Command Line Argument**

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp", "--api-key", "ctx7sk_your_actual_api_key_here"]
    }
  }
}
```

### 4. Configure Auto-Invoke Rules

Add auto-invoke rules to automatically use Context7. In Cursor, you can add this to your project's `.cursorrules` file or in Cursor Settings:

```text
Always use context7 when I need code generation, setup steps, or library documentation. 
Automatically use Context7 MCP tools without me having to ask. This means you should 
automatically use the Context7 MCP tools to resolve library id and get library docs 
without me having to explicitly ask.
```

Or add to `CLAUDE.md`:

```markdown
## Context7 Auto-Invoke Rule

Always use Context7 when I need code generation, setup steps, or library documentation. 
Automatically use Context7 MCP tools without me having to ask.
```

## Best Practices for Optimal Responses

### 1. Specify Library IDs Directly

When you know the library, specify it directly in your prompt:

```text
Implement JWT auth with Supabase. use library /supabase/supabase
```

```text
Build a rate limiter. use library /upstash/ratelimit
```

```text
Set up Next.js middleware. use library /vercel/next.js/v15.1.0
```

### 2. Use Specific Topics

Request specific topics rather than entire documentation:

```text
Good: "Get ChromaDB documentation on persistent client setup"
Bad: "Get all ChromaDB documentation"
```

### 3. Request Multiple Pages When Needed

If initial results aren't sufficient, request additional pages:

```text
"Get ChromaDB documentation on querying, page 2"
```

### 4. Control Token Limits

For API usage, you can limit tokens:

```bash
curl "https://context7.com/api/v1/vercel/next.js?tokens=2000&topic=routing" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Verification

To verify Context7 is working:

1. Ask a question about a library: "How do I use ChromaDB PersistentClient?"
2. The AI should automatically:
   - Call `resolve-library-id` for "chromadb"
   - Call `get-library-docs` with the resolved ID
   - Provide up-to-date documentation

## Troubleshooting

### Context7 Not Being Used Automatically

1. Check that auto-invoke rules are configured (see step 4)
2. Verify MCP server is configured correctly
3. Restart Cursor after configuration changes
4. Check MCP server logs in Cursor Settings

### API Key Issues

1. Verify API key is correct (starts with `ctx7sk_`)
2. Check API key hasn't expired
3. Verify API key is set in environment or MCP config
4. Check rate limits at https://context7.com/dashboard

### Rate Limiting

If you see rate limit errors:
1. Get a free API key at https://context7.com/dashboard
2. Free tier has higher rate limits than anonymous usage
3. Check your usage in the dashboard

## Project-Specific Context7 Usage

For this project, Context7 is especially important for:

- **ChromaDB**: Vector database setup and querying patterns
- **Pydantic**: v2 model validation and field validators
- **LangChain**: Document loader import paths and usage
- **Anthropic**: Claude SDK message creation and system prompts
- **Python Standard Library**: File operations, JSON parsing, etc.

## Example Usage in This Project

When working on this project, Context7 will automatically help with:

```text
User: "How do I create a ChromaDB collection?"
AI: [Auto-invokes Context7, gets latest ChromaDB docs, provides accurate code]
```

```text
User: "What's the correct Pydantic v2 syntax for field validation?"
AI: [Auto-invokes Context7, gets Pydantic v2 docs, shows correct syntax]
```

## Additional Resources

- Context7 Documentation: https://context7.com/docs
- Context7 Dashboard: https://context7.com/dashboard
- MCP Protocol: https://modelcontextprotocol.io
- Upstash Context7 GitHub: https://github.com/upstash/context7

## Security Notes

- Never commit API keys to version control
- Use environment variables or secure configuration files
- Rotate API keys regularly
- Monitor API usage in the dashboard

