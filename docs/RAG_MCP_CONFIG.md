# RAG MCP Client Configuration

**Generated:** 2026-01-23  
**Database:** Agent Kiwi (mrecfyfjpwzrzxoiooew.supabase.co)

---

## Configuration Required

Add this to your MCP client configuration (Cursor/Claude settings):

```json
{
  "mcpServers": {
    "kiwi": {
      "command": "python",
      "args": ["-m", "kiwi_mcp"],
      "env": {
        "EMBEDDING_URL": "https://api.openai.com/v1/embeddings",
        "EMBEDDING_API_KEY": "${YOUR_OPENAI_API_KEY}",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "VECTOR_DB_URL": "postgresql://postgres.mrecfyfjpwzrzxoiooew.supabase.co:5432/postgres",
        "SUPABASE_URL": "https://mrecfyfjpwzrzxoiooew.supabase.co",
        "SUPABASE_KEY": "${YOUR_SUPABASE_ANON_KEY}"
      }
    }
  }
}
```

---

## Required Values to Replace

1. **`${YOUR_OPENAI_API_KEY}`** - Your OpenAI API key (starts with `sk-`)
   - Get from: https://platform.openai.com/api-keys

2. **`${YOUR_SUPABASE_ANON_KEY}`** - Your Supabase anon/public key
   - Get from: Supabase Dashboard → Project Settings → API → anon/public key

---

## OpenRouter Configuration (Alternative)

Prefer using OpenRouter? Here's the complete configuration:

```json
{
  "mcpServers": {
    "kiwi": {
      "command": "python",
      "args": ["-m", "kiwi_mcp"],
      "env": {
        "EMBEDDING_URL": "https://openrouter.ai/api/v1/embeddings",
        "EMBEDDING_API_KEY": "${YOUR_OPENROUTER_API_KEY}",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "EMBEDDING_AUTH_HEADER": "Authorization",
        "EMBEDDING_AUTH_FORMAT": "Bearer {key}",
        "VECTOR_DB_URL": "postgresql://postgres.mrecfyfjpwzrzxoiooew.supabase.co:5432/postgres",
        "SUPABASE_URL": "https://mrecfyfjpwzrzxoiooew.supabase.co",
        "SUPABASE_KEY": "${YOUR_SUPABASE_ANON_KEY}"
      }
    }
  }
}
```

**Get OpenRouter API key:** https://openrouter.ai/keys

---

## Environment Variables Explained

### Embedding Configuration (Mandatory)

- **`EMBEDDING_URL`**: OpenAI embeddings endpoint
- **`EMBEDDING_API_KEY`**: Your OpenAI API key
- **`EMBEDDING_MODEL`**: Embedding model to use (text-embedding-3-small is recommended)

### Vector Database (Mandatory)

- **`VECTOR_DB_URL`**: PostgreSQL connection string for pgvector
  - Format: `postgresql://postgres.<ref>.supabase.co:5432/postgres`
  - Your database ref: `mrecfyfjpwzrzxoiooew`

### Supabase Registry (Optional but Recommended)

- **`SUPABASE_URL`**: Your Supabase project URL
- **`SUPABASE_KEY`**: Anon/public key for registry access

---

## Alternative Embedding Providers

### OpenRouter

```json
{
  "EMBEDDING_URL": "https://openrouter.ai/api/v1/embeddings",
  "EMBEDDING_API_KEY": "${YOUR_OPENROUTER_API_KEY}",
  "EMBEDDING_MODEL": "text-embedding-3-small",
  "EMBEDDING_AUTH_HEADER": "Authorization",
  "EMBEDDING_AUTH_FORMAT": "Bearer {key}"
}
```

**Supported models:**
- `text-embedding-3-small` (OpenAI via OpenRouter)
- `text-embedding-3-large` (OpenAI via OpenRouter)
- `text-embedding-ada-002` (OpenAI via OpenRouter)

**Get API key:** https://openrouter.ai/keys

**Pricing:** Same as OpenAI but with unified billing across providers

### Ollama (Local)

```json
{
  "EMBEDDING_URL": "http://localhost:11434/api/embeddings",
  "EMBEDDING_API_KEY": "not-needed",
  "EMBEDDING_MODEL": "nomic-embed-text",
  "EMBEDDING_FORMAT": "ollama"
}
```

### Azure OpenAI

```json
{
  "EMBEDDING_URL": "https://<your-resource>.openai.azure.com/openai/deployments/<deployment-name>/embeddings?api-version=2023-05-15",
  "EMBEDDING_API_KEY": "${YOUR_AZURE_KEY}",
  "EMBEDDING_MODEL": "text-embedding-ada-002",
  "EMBEDDING_AUTH_HEADER": "api-key",
  "EMBEDDING_AUTH_FORMAT": "{key}"
}
```

---

## Verification

After adding the configuration, verify it works:

```bash
# The MCP server should start without errors
python -m kiwi_mcp

# Expected: Server starts successfully
# If RAG config is missing, you'll see an error with instructions
```

---

## What Happens Next

Once configured, the Kiwi MCP will:

1. ✅ **Validate RAG config** at startup (fails fast if missing)
2. ✅ **Automatically embed** all validated content (directives, tools, knowledge)
3. ✅ **Enable semantic search** across all content types
4. ✅ **Use hybrid search** (vector + keyword) for better results

---

## Database Tables Created

Your database now has:

| Table | Purpose | Rows |
|-------|---------|------|
| `item_embeddings` | Vector embeddings for all content | 0 (ready) |
| `knowledge` | Knowledge metadata | 159 |
| `knowledge_versions` | Knowledge content versions | 159 |
| `directives` | Directive metadata | 141 |
| `directive_versions` | Directive content versions | 351 |
| `tools` | Tool metadata | 15 |
| `tool_versions` | Tool content versions | 15 |

---

## Cost Estimation

**OpenAI text-embedding-3-small pricing:**
- ~$0.02 per 1M tokens
- Average knowledge entry: ~500 tokens
- Your 159 entries: ~79,500 tokens
- **Estimated cost**: ~$0.002 (less than a penny!)

**Ongoing costs:**
- Each new/updated item: ~$0.00001
- Queries are free (just retrieval)

---

## Troubleshooting

### "RAG configuration missing" error

If you see this error, the environment variables aren't being passed to the MCP server.

**Solution**: Make sure your MCP client configuration is in the correct location:
- **Cursor**: Settings → MCP → Add server configuration
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

### Connection errors

If you see database connection errors:

1. Check your Supabase database is **active** (not paused)
2. Verify the connection string is correct
3. Test the connection:
   ```bash
   psql postgresql://postgres.mrecfyfjpwzrzxoiooew.supabase.co:5432/postgres
   ```

### Embedding errors

If embeddings fail:

1. Verify your OpenAI API key is valid
2. Check you have credits available
3. Try the embedding endpoint manually:
   ```bash
   curl https://api.openai.com/v1/embeddings \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"input": "test", "model": "text-embedding-3-small"}'
   ```

---

## Related Documentation

- [RAG_INTEGRATION_COMPLETE.md](./RAG_INTEGRATION_COMPLETE.md) - Complete RAG implementation
- [RAG_IMPLEMENTATION_SUMMARY.md](./RAG_IMPLEMENTATION_SUMMARY.md) - Technical summary
- [DATABASE_SCHEMA_ALIGNMENT.md](./DATABASE_SCHEMA_ALIGNMENT.md) - Database structure
