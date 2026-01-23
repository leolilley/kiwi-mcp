# Database Evolution: Scripts → Tools

**Date:** 2026-01-23  
**Status:** Draft  
**Related:** [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md), [TOOLS_EVOLUTION_PROPOSAL.md](./TOOLS_EVOLUTION_PROPOSAL.md), [DYNAMIC_TOOLS_ARCHITECTURE.md](./DYNAMIC_TOOLS_ARCHITECTURE.md)

---

## Executive Summary

The move from "scripts" to "tools" requires database evolution. Tools are a superset: Python (legacy scripts), Bash, API, Docker, and MCP proxies. This document outlines the schema changes needed for Supabase.

**Key Decision:** Create new `tools` tables, migrate existing data, and keep `scripts` as views for backward compatibility.

---

## Core Architectural Principle: Tools Are Data, Not Code

### The Key Insight

**Executors are primitives (code). Tools are definitions (data).**

| Layer         | What It Is                               | Where It Lives                                    | Who Creates It     |
| ------------- | ---------------------------------------- | ------------------------------------------------- | ------------------ |
| **Executors** | Runtime engines (Python, Bash, API, MCP) | Hard-coded in `kiwi_mcp/handlers/tool/executors/` | Developers         |
| **Tools**     | Declarative definitions + implementation | Registry (`tools` table) + files                  | LLMs or Developers |

This means:

- We have ~5 executor types (the primitives)
- We can have unlimited tools (data in registry)
- **LLMs can create new tools dynamically** by providing manifest + implementation
- No code changes needed to add a new tool

### How MCP Fits In

An MCP tool is just a **routing definition** stored in the registry:

```yaml
# Example: MCP tool stored in tools table
tool_id: supabase_execute_sql
tool_type: mcp # Routes to MCPExecutor
executor_config:
  mcp_server: supabase # Which MCP server to connect to
  mcp_tool: execute_sql # Which tool on that server
```

When called:

1. Look up tool in registry → `tool_type: mcp`
2. Route to `MCPExecutor`
3. MCPExecutor connects to Supabase MCP server
4. Proxies the call, returns result

**MCP server configs also become data** in an `mcp_servers` table, not hard-coded in Python.

### Dynamic Tool Creation Flow

```
LLM needs a new capability
         │
         ▼
┌─────────────────────────────┐
│ Search registry for tool    │──── Found? ──► Use it
└─────────────────────────────┘
         │ Not found
         ▼
┌─────────────────────────────┐
│ LLM creates tool:           │
│ - Writes manifest (YAML)    │
│ - Writes implementation     │
│   (Python/Bash/API config)  │
│ - Calls execute(create)     │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Tool saved to registry      │
│ - tools table (metadata)    │
│ - tool_versions (manifest)  │
│ - tool_version_files (code) │
└─────────────────────────────┘
         │
         ▼
   Any agent can now use it
```

### What's Static vs Dynamic

| Component            | Static (Code) |   Dynamic (Registry)    |
| -------------------- | :-----------: | :---------------------: |
| PythonExecutor       |      ✅       |                         |
| BashExecutor         |      ✅       |                         |
| APIExecutor          |      ✅       |                         |
| MCPExecutor          |      ✅       |                         |
| DockerExecutor       |      ✅       |                         |
| MCP server configs   |               | ✅ `mcp_servers` table  |
| Individual tools     |               |    ✅ `tools` table     |
| Tool implementations |               | ✅ `tool_version_files` |

### Example: Tool Type Matrix

| tool_type | Executor       | What's in Registry           | LLM Can Create? |
| --------- | -------------- | ---------------------------- | :-------------: |
| `python`  | PythonExecutor | Manifest + `.py` files       |       ✅        |
| `bash`    | BashExecutor   | Manifest + `.sh` files       |       ✅        |
| `api`     | APIExecutor    | Manifest only (API config)   |       ✅        |
| `docker`  | DockerExecutor | Manifest (image + config)    |       ✅        |
| `mcp`     | MCPExecutor    | Manifest (server + tool ref) |       ✅        |

---

## New Tables Summary

| Table                  | Purpose                                |
| ---------------------- | -------------------------------------- |
| `tools`                | Tool metadata (replaces `scripts`)     |
| `tool_versions`        | Versioned manifests (JSONB)            |
| `tool_version_files`   | Multi-file support (code, configs)     |
| `mcp_servers`          | Reusable MCP server connection configs |
| `directive_embeddings` | Vector + FTS for directives            |
| `tool_embeddings`      | Vector + FTS for tools                 |
| `knowledge_embeddings` | Vector + FTS for knowledge             |

---

## Current State

### Existing Tables

| Table                     | Purpose                                                         |
| ------------------------- | --------------------------------------------------------------- |
| `scripts`                 | Script metadata (name, category, description, tech_stack, tags) |
| `script_versions`         | Version content (version, content, content_hash)                |
| `directives`              | Directive metadata                                              |
| `directive_versions`      | Directive version content                                       |
| `knowledge_entries`       | Knowledge zettel entries                                        |
| `knowledge_relationships` | Graph relationships                                             |
| `item_embeddings`         | Vector embeddings (item_type: directive, script, knowledge)     |

### Current Limitations

1. **Single file per script** - No support for multi-file tools (Python + requirements.txt + tool.yaml)
2. **Python-only** - No `tool_type` to distinguish bash/api/docker/mcp
3. **No manifest storage** - tool.yaml manifests not versioned
4. **Blob in DB** - Large scripts stored as text in Postgres

---

## Proposed Schema

### New Tables

#### `tools` (replaces `scripts` as canonical entity)

```sql
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id TEXT NOT NULL,              -- stable identifier (e.g., "lint_python")
    namespace TEXT DEFAULT 'public',     -- for future multi-tenancy
    name TEXT,                           -- display name
    tool_type TEXT NOT NULL,             -- python | bash | api | docker | mcp
    description TEXT,
    category TEXT,
    subcategory TEXT,
    tags TEXT[],
    tech_stack TEXT[],
    is_official BOOLEAN DEFAULT false,
    visibility TEXT DEFAULT 'public',    -- public | unlisted | private
    download_count INTEGER DEFAULT 0,
    quality_score NUMERIC(3,2),
    success_rate NUMERIC(3,2),
    estimated_cost_usd NUMERIC(10,2),
    latest_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT tools_tool_type_check
        CHECK (tool_type IN ('python', 'bash', 'api', 'docker', 'mcp')),
    CONSTRAINT tools_visibility_check
        CHECK (visibility IN ('public', 'unlisted', 'private')),
    UNIQUE (namespace, tool_id)
);

CREATE INDEX idx_tools_tool_id ON tools (tool_id);
CREATE INDEX idx_tools_category ON tools (category);
CREATE INDEX idx_tools_tool_type ON tools (tool_type);
```

#### `tool_versions` (replaces `script_versions`)

```sql
CREATE TABLE tool_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    version TEXT NOT NULL,               -- semver string
    manifest JSONB NOT NULL,             -- parsed tool.yaml
    manifest_yaml TEXT,                  -- original YAML for round-trip fidelity
    content_hash TEXT NOT NULL,          -- hash of canonical artifact
    changelog TEXT,
    is_latest BOOLEAN DEFAULT false,
    published_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (tool_id, version)
);

CREATE INDEX idx_tool_versions_tool_id ON tool_versions (tool_id);
CREATE INDEX idx_tool_versions_is_latest ON tool_versions (is_latest) WHERE is_latest = true;
```

#### `tool_version_files` (supports multi-file tools)

```sql
CREATE TABLE tool_version_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_version_id UUID NOT NULL REFERENCES tool_versions(id) ON DELETE CASCADE,
    path TEXT NOT NULL,                  -- e.g., 'tool.yaml', 'main.py', 'requirements.txt'
    media_type TEXT,                     -- e.g., 'text/x-python', 'text/plain'
    sha256 TEXT NOT NULL,
    size_bytes INTEGER,
    is_executable BOOLEAN DEFAULT false,
    content_text TEXT,                   -- for small text files (< 64KB)
    storage_key TEXT,                    -- Supabase Storage key for larger files
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (tool_version_id, path)
);

CREATE INDEX idx_tool_version_files_version ON tool_version_files (tool_version_id);
```

### Updated `item_embeddings`

```sql
-- Add 'tool' to allowed item types
ALTER TABLE item_embeddings
DROP CONSTRAINT item_embeddings_item_type_check;

ALTER TABLE item_embeddings
ADD CONSTRAINT item_embeddings_item_type_check
CHECK (item_type IN ('directive', 'script', 'tool', 'knowledge'));
```

---

## Migration Strategy

### Phase 1: Create New Tables (Non-Breaking)

1. Create `tools`, `tool_versions`, `tool_version_files` tables
2. Create Supabase Storage bucket `tool-artifacts`
3. Update `item_embeddings` constraint to include `'tool'`

### Phase 2: Migrate Existing Data

```sql
-- Migrate scripts → tools
INSERT INTO tools (
    id, tool_id, namespace, name, tool_type, description, category,
    subcategory, tags, tech_stack, is_official, download_count,
    quality_score, success_rate, estimated_cost_usd, latest_version,
    created_at, updated_at
)
SELECT
    id,
    name AS tool_id,           -- use script name as tool_id
    'public' AS namespace,
    name,
    'python' AS tool_type,     -- all existing scripts are Python
    description,
    category,
    subcategory,
    tags,
    tech_stack,
    is_official,
    download_count,
    quality_score,
    success_rate,
    estimated_cost_usd,
    latest_version,
    created_at,
    updated_at
FROM scripts;

-- Migrate script_versions → tool_versions + tool_version_files
INSERT INTO tool_versions (
    id, tool_id, version, manifest, manifest_yaml, content_hash,
    changelog, is_latest, created_at
)
SELECT
    sv.id,
    sv.script_id AS tool_id,
    sv.version,
    jsonb_build_object(
        'tool_id', s.name,
        'tool_type', 'python',
        'version', sv.version,
        'description', s.description,
        'executor_config', jsonb_build_object('entrypoint', 'main.py')
    ) AS manifest,
    NULL AS manifest_yaml,     -- no original YAML for legacy scripts
    sv.content_hash,
    sv.changelog,
    sv.version = s.latest_version AS is_latest,
    sv.created_at
FROM script_versions sv
JOIN scripts s ON sv.script_id = s.id;

-- Create file entries for script content
INSERT INTO tool_version_files (
    tool_version_id, path, media_type, sha256, size_bytes,
    is_executable, content_text
)
SELECT
    tv.id AS tool_version_id,
    'main.py' AS path,
    'text/x-python' AS media_type,
    sv.content_hash AS sha256,
    LENGTH(sv.content) AS size_bytes,
    true AS is_executable,
    sv.content AS content_text
FROM script_versions sv
JOIN tool_versions tv ON sv.id = tv.id;
```

### Phase 3: Create Compatibility Views

```sql
-- Legacy scripts view (for backward compatibility)
CREATE OR REPLACE VIEW scripts_compat AS
SELECT
    id,
    tool_id AS name,
    category,
    subcategory,
    description,
    is_official,
    download_count,
    quality_score,
    tech_stack,
    tags,
    success_rate,
    estimated_cost_usd,
    latest_version,
    created_at,
    updated_at
FROM tools
WHERE tool_type = 'python';

-- Legacy script_versions view
CREATE OR REPLACE VIEW script_versions_compat AS
SELECT
    tv.id,
    tv.tool_id AS script_id,
    tv.version,
    tvf.content_text AS content,
    tv.content_hash,
    tv.changelog,
    tv.created_at
FROM tool_versions tv
LEFT JOIN tool_version_files tvf
    ON tv.id = tvf.tool_version_id
    AND tvf.path = 'main.py'
JOIN tools t ON tv.tool_id = t.id
WHERE t.tool_type = 'python';
```

### Phase 4: Update Registry Classes

1. Create `ToolRegistry` class (new)
2. Update `ScriptRegistry` to use views or proxy to `ToolRegistry`
3. Add `ToolResolver` for local `.ai/scripts/` (or `.ai/tools/`) resolution

---

## Local Storage Structure

### Current: `.ai/scripts/`

```
.ai/scripts/
├── category/
│   └── script_name.py       # Single Python file
```

### Proposed: Keep `.ai/scripts/` but support multi-file

```
.ai/scripts/
├── category/
│   ├── python_script.py     # Legacy single-file (virtual manifest)
│   ├── bash_tool/           # Directory for multi-file tools
│   │   ├── tool.yaml        # Tool manifest
│   │   └── script.sh        # Entrypoint
│   └── api_tool/
│       └── tool.yaml        # API tools are manifest-only
```

**Resolution Logic:**

1. If `name.py` exists → Python tool (virtual manifest)
2. If `name/tool.yaml` exists → Load manifest, use specified executor
3. If `name/` directory without manifest → Error

**Future Option:** Rename to `.ai/tools/` (Phase 2, breaking change with migration)

---

## Multi-File Tool Publishing

When publishing a multi-file tool to registry:

```python
async def publish_tool(tool_path: Path, version: str) -> Dict[str, Any]:
    # 1. Load and validate manifest
    manifest = ToolManifest.from_yaml(tool_path / "tool.yaml")

    # 2. Collect all files
    files = []
    for file in tool_path.rglob("*"):
        if file.is_file():
            files.append({
                "path": str(file.relative_to(tool_path)),
                "content": file.read_bytes(),
                "sha256": hash_file(file)
            })

    # 3. Create bundle (optional but recommended)
    bundle = create_zip_bundle(tool_path)
    bundle_key = f"tools/{manifest.tool_id}/{version}/bundle.zip"
    await storage.upload(bundle_key, bundle)

    # 4. Insert tool + version + files
    tool_id = await upsert_tool(manifest)
    version_id = await insert_version(tool_id, version, manifest)

    for file in files:
        if len(file["content"]) < 65536:  # < 64KB
            await insert_file(version_id, file["path"],
                              content_text=file["content"])
        else:
            storage_key = f"tools/{manifest.tool_id}/{version}/{file['path']}"
            await storage.upload(storage_key, file["content"])
            await insert_file(version_id, file["path"],
                              storage_key=storage_key)

    return {"tool_id": manifest.tool_id, "version": version}
```

---

## RAG/Embeddings Considerations

### What to Embed

For tools, embed a composite of:

- Description
- Parameter names and descriptions
- Tags and category
- Example usage (from manifest)

```python
def generate_tool_embedding_content(tool: Tool, manifest: ToolManifest) -> str:
    parts = [
        f"Tool: {tool.name}",
        f"Type: {manifest.tool_type}",
        f"Description: {tool.description or ''}",
        f"Category: {tool.category or ''}",
        f"Tags: {', '.join(tool.tags or [])}",
    ]

    # Add parameter info
    for param in manifest.parameters or []:
        parts.append(f"Parameter {param['name']}: {param.get('description', '')}")

    return "\n".join(parts)
```

### Embedding Strategy

**Embed latest version only** (initially):

- Avoids uniqueness constraint issues in `item_embeddings`
- `item_type = 'tool'`, `item_id = tool_id` or `tool:<namespace>/<tool_id>`
- Re-embed when new version published

**Future: Version-level embeddings** (if needed):

- Change `item_embeddings.item_id` to non-unique or composite
- `item_id = tool:<namespace>/<tool_id>@<version>`

---

## Migration Checklist

### Database Changes

- [ ] Create `tools` table with `tool_type` column
- [ ] Create `tool_versions` table with manifest JSONB
- [ ] Create `tool_version_files` table for multi-file support
- [ ] Create Supabase Storage bucket `tool-artifacts`
- [ ] Migrate existing scripts → tools (tool_type='python')
- [ ] Create compatibility views for `scripts` / `script_versions`
- [ ] Update `item_embeddings` check constraint

### Code Changes

- [ ] Create `ToolRegistry` class
- [ ] Update `ScriptRegistry` to use compat views or delegate
- [ ] Update `ToolHandler._publish_tool` to use new schema
- [ ] Update `RegistryVectorStore` to handle `item_type='tool'`
- [ ] Add multi-file bundle support to publish flow

### Local Storage

- [ ] Update `ToolResolver` to support directory-based tools
- [ ] Support `tool.yaml` manifest loading
- [ ] Virtual manifest generation for legacy `.py` files

---

## Open Questions

1. **Namespace Strategy**: Should we implement namespaces now (e.g., `user/tool_id`) or defer?

   - Recommendation: Add column now, default to `'public'`, implement later

2. **Directory Rename**: Should `.ai/scripts/` become `.ai/tools/`?

   - Recommendation: Keep `scripts` for now, support both in resolver

3. **Bundle Format**: ZIP vs tarball for multi-file tools?

   - Recommendation: ZIP (universal support, Supabase Storage friendly)

4. **Content Storage Threshold**: At what size should files go to Storage vs DB?
   - Recommendation: 64KB (matches typical script sizes, keeps small tools fast)

---

## RAG & Vector Search Schema (Supabase Best Practices)

This section extends the schema to support semantic search following Supabase's recommended patterns for pgvector.

### Key Design Decisions

1. **HNSW over IVFFlat** - Better performance for our scale, no training required
2. **Hybrid Search (RRF)** - Combine semantic + full-text for best results
3. **Generated FTS columns** - Auto-maintained tsvector for keyword search
4. **Per-type tables** - Separate embedding tables for directives, tools, knowledge (better indexing)

### Current vs Proposed

| Aspect       | Current (`item_embeddings`) | Proposed                        |
| ------------ | --------------------------- | ------------------------------- |
| Single table | All item types mixed        | Per-type tables (better perf)   |
| Index type   | IVFFlat (lists=100)         | HNSW (m=16, ef=64)              |
| Full-text    | None                        | Generated tsvector + GIN        |
| Search       | Vector-only                 | Hybrid RRF (semantic + keyword) |
| Dimension    | 384 (MiniLM)                | 384 or 512 (configurable)       |

### New Embedding Tables

#### `directive_embeddings`

```sql
-- Drop old generic table (after migration)
-- DROP TABLE item_embeddings;

CREATE TABLE directive_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    directive_id UUID NOT NULL REFERENCES directives(id) ON DELETE CASCADE,
    version TEXT,                        -- NULL = latest, or specific version

    -- Vector embedding
    embedding vector(384) NOT NULL,

    -- Full-text search (generated column)
    content TEXT NOT NULL,               -- Combined searchable text
    fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED,

    -- Metadata for filtering
    name TEXT,
    description TEXT,
    category TEXT,
    tags TEXT[],

    -- Audit fields
    signature TEXT,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (directive_id, version)
);

-- HNSW index for semantic search (inner product for normalized embeddings)
CREATE INDEX directive_embeddings_hnsw
ON directive_embeddings
USING hnsw (embedding vector_ip_ops)
WITH (m = 16, ef_construction = 64);

-- GIN index for full-text search
CREATE INDEX directive_embeddings_fts
ON directive_embeddings
USING gin(fts);

-- Category filter index
CREATE INDEX directive_embeddings_category
ON directive_embeddings (category);
```

#### `tool_embeddings`

```sql
CREATE TABLE tool_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    version TEXT,                        -- NULL = latest

    -- Vector embedding
    embedding vector(384) NOT NULL,

    -- Full-text search
    content TEXT NOT NULL,
    fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED,

    -- Metadata
    name TEXT,
    description TEXT,
    tool_type TEXT,                      -- python, bash, api, docker, mcp
    category TEXT,
    tags TEXT[],
    parameters JSONB,                    -- For parameter-based search

    -- Audit
    signature TEXT,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (tool_id, version)
);

-- Indexes
CREATE INDEX tool_embeddings_hnsw
ON tool_embeddings
USING hnsw (embedding vector_ip_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX tool_embeddings_fts
ON tool_embeddings
USING gin(fts);

CREATE INDEX tool_embeddings_category
ON tool_embeddings (category);

CREATE INDEX tool_embeddings_tool_type
ON tool_embeddings (tool_type);
```

#### `knowledge_embeddings`

```sql
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_id UUID NOT NULL REFERENCES knowledge_entries(id) ON DELETE CASCADE,

    -- Vector embedding
    embedding vector(384) NOT NULL,

    -- Full-text search
    content TEXT NOT NULL,
    fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'B')
    ) STORED,

    -- Metadata
    title TEXT,
    entry_type TEXT,                     -- concept, pattern, learning, etc.
    tags TEXT[],

    -- Audit
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (knowledge_id)
);

-- Indexes
CREATE INDEX knowledge_embeddings_hnsw
ON knowledge_embeddings
USING hnsw (embedding vector_ip_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX knowledge_embeddings_fts
ON knowledge_embeddings
USING gin(fts);

CREATE INDEX knowledge_embeddings_entry_type
ON knowledge_embeddings (entry_type);
```

### Hybrid Search Functions (RRF)

#### Search Directives

```sql
CREATE OR REPLACE FUNCTION search_directives_hybrid(
    query_text TEXT,
    query_embedding vector(384),
    match_count INT DEFAULT 20,
    full_text_weight FLOAT DEFAULT 1.0,
    semantic_weight FLOAT DEFAULT 1.0,
    rrf_k INT DEFAULT 60,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    directive_id UUID,
    name TEXT,
    description TEXT,
    category TEXT,
    score FLOAT,
    match_type TEXT  -- 'semantic', 'keyword', or 'both'
)
LANGUAGE sql
AS $$
WITH semantic AS (
    SELECT
        de.directive_id,
        de.name,
        de.description,
        de.category,
        ROW_NUMBER() OVER (ORDER BY de.embedding <#> query_embedding) AS rank_ix
    FROM directive_embeddings de
    WHERE (filter_category IS NULL OR de.category = filter_category)
    ORDER BY de.embedding <#> query_embedding
    LIMIT match_count * 2
),
full_text AS (
    SELECT
        de.directive_id,
        de.name,
        de.description,
        de.category,
        ROW_NUMBER() OVER (ORDER BY ts_rank_cd(de.fts, websearch_to_tsquery('english', query_text)) DESC) AS rank_ix
    FROM directive_embeddings de
    WHERE de.fts @@ websearch_to_tsquery('english', query_text)
      AND (filter_category IS NULL OR de.category = filter_category)
    ORDER BY rank_ix
    LIMIT match_count * 2
)
SELECT
    COALESCE(s.directive_id, f.directive_id) AS directive_id,
    COALESCE(s.name, f.name) AS name,
    COALESCE(s.description, f.description) AS description,
    COALESCE(s.category, f.category) AS category,
    (
        COALESCE(1.0 / (rrf_k + f.rank_ix), 0.0) * full_text_weight +
        COALESCE(1.0 / (rrf_k + s.rank_ix), 0.0) * semantic_weight
    ) AS score,
    CASE
        WHEN s.directive_id IS NOT NULL AND f.directive_id IS NOT NULL THEN 'both'
        WHEN f.directive_id IS NOT NULL THEN 'keyword'
        ELSE 'semantic'
    END AS match_type
FROM semantic s
FULL OUTER JOIN full_text f ON s.directive_id = f.directive_id
ORDER BY score DESC
LIMIT match_count;
$$;
```

#### Search Tools

```sql
CREATE OR REPLACE FUNCTION search_tools_hybrid(
    query_text TEXT,
    query_embedding vector(384),
    match_count INT DEFAULT 20,
    full_text_weight FLOAT DEFAULT 1.0,
    semantic_weight FLOAT DEFAULT 1.0,
    rrf_k INT DEFAULT 60,
    filter_category TEXT DEFAULT NULL,
    filter_tool_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    tool_id UUID,
    name TEXT,
    description TEXT,
    tool_type TEXT,
    category TEXT,
    score FLOAT,
    match_type TEXT
)
LANGUAGE sql
AS $$
WITH semantic AS (
    SELECT
        te.tool_id,
        te.name,
        te.description,
        te.tool_type,
        te.category,
        ROW_NUMBER() OVER (ORDER BY te.embedding <#> query_embedding) AS rank_ix
    FROM tool_embeddings te
    WHERE (filter_category IS NULL OR te.category = filter_category)
      AND (filter_tool_type IS NULL OR te.tool_type = filter_tool_type)
    ORDER BY te.embedding <#> query_embedding
    LIMIT match_count * 2
),
full_text AS (
    SELECT
        te.tool_id,
        te.name,
        te.description,
        te.tool_type,
        te.category,
        ROW_NUMBER() OVER (ORDER BY ts_rank_cd(te.fts, websearch_to_tsquery('english', query_text)) DESC) AS rank_ix
    FROM tool_embeddings te
    WHERE te.fts @@ websearch_to_tsquery('english', query_text)
      AND (filter_category IS NULL OR te.category = filter_category)
      AND (filter_tool_type IS NULL OR te.tool_type = filter_tool_type)
    ORDER BY rank_ix
    LIMIT match_count * 2
)
SELECT
    COALESCE(s.tool_id, f.tool_id) AS tool_id,
    COALESCE(s.name, f.name) AS name,
    COALESCE(s.description, f.description) AS description,
    COALESCE(s.tool_type, f.tool_type) AS tool_type,
    COALESCE(s.category, f.category) AS category,
    (
        COALESCE(1.0 / (rrf_k + f.rank_ix), 0.0) * full_text_weight +
        COALESCE(1.0 / (rrf_k + s.rank_ix), 0.0) * semantic_weight
    ) AS score,
    CASE
        WHEN s.tool_id IS NOT NULL AND f.tool_id IS NOT NULL THEN 'both'
        WHEN f.tool_id IS NOT NULL THEN 'keyword'
        ELSE 'semantic'
    END AS match_type
FROM semantic s
FULL OUTER JOIN full_text f ON s.tool_id = f.tool_id
ORDER BY score DESC
LIMIT match_count;
$$;
```

#### Search Knowledge

```sql
CREATE OR REPLACE FUNCTION search_knowledge_hybrid(
    query_text TEXT,
    query_embedding vector(384),
    match_count INT DEFAULT 20,
    full_text_weight FLOAT DEFAULT 1.0,
    semantic_weight FLOAT DEFAULT 1.0,
    rrf_k INT DEFAULT 60,
    filter_entry_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    knowledge_id UUID,
    title TEXT,
    entry_type TEXT,
    score FLOAT,
    match_type TEXT
)
LANGUAGE sql
AS $$
WITH semantic AS (
    SELECT
        ke.knowledge_id,
        ke.title,
        ke.entry_type,
        ROW_NUMBER() OVER (ORDER BY ke.embedding <#> query_embedding) AS rank_ix
    FROM knowledge_embeddings ke
    WHERE (filter_entry_type IS NULL OR ke.entry_type = filter_entry_type)
    ORDER BY ke.embedding <#> query_embedding
    LIMIT match_count * 2
),
full_text AS (
    SELECT
        ke.knowledge_id,
        ke.title,
        ke.entry_type,
        ROW_NUMBER() OVER (ORDER BY ts_rank_cd(ke.fts, websearch_to_tsquery('english', query_text)) DESC) AS rank_ix
    FROM knowledge_embeddings ke
    WHERE ke.fts @@ websearch_to_tsquery('english', query_text)
      AND (filter_entry_type IS NULL OR ke.entry_type = filter_entry_type)
    ORDER BY rank_ix
    LIMIT match_count * 2
)
SELECT
    COALESCE(s.knowledge_id, f.knowledge_id) AS knowledge_id,
    COALESCE(s.title, f.title) AS title,
    COALESCE(s.entry_type, f.entry_type) AS entry_type,
    (
        COALESCE(1.0 / (rrf_k + f.rank_ix), 0.0) * full_text_weight +
        COALESCE(1.0 / (rrf_k + s.rank_ix), 0.0) * semantic_weight
    ) AS score,
    CASE
        WHEN s.knowledge_id IS NOT NULL AND f.knowledge_id IS NOT NULL THEN 'both'
        WHEN f.knowledge_id IS NOT NULL THEN 'keyword'
        ELSE 'semantic'
    END AS match_type
FROM semantic s
FULL OUTER JOIN full_text f ON s.knowledge_id = f.knowledge_id
ORDER BY score DESC
LIMIT match_count;
$$;
```

### Unified Search Function

For convenience, a single function that searches across all types:

```sql
CREATE OR REPLACE FUNCTION search_all_hybrid(
    query_text TEXT,
    query_embedding vector(384),
    match_count INT DEFAULT 20,
    filter_item_type TEXT DEFAULT NULL  -- 'directive', 'tool', 'knowledge', or NULL for all
)
RETURNS TABLE (
    item_id UUID,
    item_type TEXT,
    name TEXT,
    description TEXT,
    category TEXT,
    score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH directive_results AS (
        SELECT
            directive_id AS item_id,
            'directive'::TEXT AS item_type,
            name,
            description,
            category,
            score
        FROM search_directives_hybrid(query_text, query_embedding, match_count / 3)
        WHERE filter_item_type IS NULL OR filter_item_type = 'directive'
    ),
    tool_results AS (
        SELECT
            tool_id AS item_id,
            'tool'::TEXT AS item_type,
            name,
            description,
            category,
            score
        FROM search_tools_hybrid(query_text, query_embedding, match_count / 3)
        WHERE filter_item_type IS NULL OR filter_item_type = 'tool'
    ),
    knowledge_results AS (
        SELECT
            knowledge_id AS item_id,
            'knowledge'::TEXT AS item_type,
            title AS name,
            NULL::TEXT AS description,
            entry_type AS category,
            score
        FROM search_knowledge_hybrid(query_text, query_embedding, match_count / 3)
        WHERE filter_item_type IS NULL OR filter_item_type = 'knowledge'
    )
    SELECT * FROM directive_results
    UNION ALL
    SELECT * FROM tool_results
    UNION ALL
    SELECT * FROM knowledge_results
    ORDER BY score DESC
    LIMIT match_count;
END;
$$;
```

### Index Tuning Parameters

| Parameter         | Value       | Rationale                            |
| ----------------- | ----------- | ------------------------------------ |
| `m` (HNSW)        | 16          | Good balance for < 1M vectors        |
| `ef_construction` | 64          | Higher = better recall, slower build |
| `rrf_k`           | 60          | Standard RRF smoothing constant      |
| FTS weight A      | Name        | Exact name matches ranked highest    |
| FTS weight B      | Description | Good description matches next        |
| FTS weight C      | Content     | Full content matches last            |

For larger scale (> 1M items), consider:

- Increase `m` to 32
- Increase `ef_construction` to 128
- Add partitioning by category

### RLS Policies

```sql
-- Enable RLS
ALTER TABLE directive_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_embeddings ENABLE ROW LEVEL SECURITY;

-- Public read access (adjust based on your auth model)
CREATE POLICY "Public read access" ON directive_embeddings
    FOR SELECT USING (true);

CREATE POLICY "Public read access" ON tool_embeddings
    FOR SELECT USING (true);

CREATE POLICY "Public read access" ON knowledge_embeddings
    FOR SELECT USING (true);

-- Authenticated write access
CREATE POLICY "Authenticated users can insert" ON directive_embeddings
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can insert" ON tool_embeddings
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can insert" ON knowledge_embeddings
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Grant permissions
GRANT SELECT ON directive_embeddings TO anon, authenticated;
GRANT SELECT ON tool_embeddings TO anon, authenticated;
GRANT SELECT ON knowledge_embeddings TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON directive_embeddings TO authenticated;
GRANT INSERT, UPDATE, DELETE ON tool_embeddings TO authenticated;
GRANT INSERT, UPDATE, DELETE ON knowledge_embeddings TO authenticated;

-- Grant execute on search functions
GRANT EXECUTE ON FUNCTION search_directives_hybrid TO anon, authenticated;
GRANT EXECUTE ON FUNCTION search_tools_hybrid TO anon, authenticated;
GRANT EXECUTE ON FUNCTION search_knowledge_hybrid TO anon, authenticated;
GRANT EXECUTE ON FUNCTION search_all_hybrid TO anon, authenticated;
```

### Migration from `item_embeddings`

```sql
-- 1. Create new tables (above)

-- 2. Migrate existing embeddings
INSERT INTO directive_embeddings (directive_id, embedding, content, name, description, category, validated_at)
SELECT
    d.id AS directive_id,
    ie.embedding,
    ie.content,
    d.name,
    d.description,
    d.category,
    ie.validated_at
FROM item_embeddings ie
JOIN directives d ON ie.item_id = d.id::text OR ie.item_id = d.name
WHERE ie.item_type = 'directive';

INSERT INTO tool_embeddings (tool_id, embedding, content, name, description, tool_type, category, validated_at)
SELECT
    t.id AS tool_id,
    ie.embedding,
    ie.content,
    t.name,
    t.description,
    t.tool_type,
    t.category,
    ie.validated_at
FROM item_embeddings ie
JOIN tools t ON ie.item_id = t.id::text OR ie.item_id = t.tool_id
WHERE ie.item_type IN ('script', 'tool');

INSERT INTO knowledge_embeddings (knowledge_id, embedding, content, title, entry_type, validated_at)
SELECT
    k.id AS knowledge_id,
    ie.embedding,
    ie.content,
    k.title,
    k.entry_type,
    ie.validated_at
FROM item_embeddings ie
JOIN knowledge_entries k ON ie.item_id = k.id::text OR ie.item_id = k.zettel_id
WHERE ie.item_type = 'knowledge';

-- 3. Verify migration
-- SELECT COUNT(*) FROM directive_embeddings;
-- SELECT COUNT(*) FROM tool_embeddings;
-- SELECT COUNT(*) FROM knowledge_embeddings;

-- 4. Drop old table (after verification)
-- DROP TABLE item_embeddings;
```

---

## Summary

| Aspect           | Current                    | Proposed                              |
| ---------------- | -------------------------- | ------------------------------------- |
| Canonical table  | `scripts`                  | `tools`                               |
| Tool types       | Python only                | python, bash, api, docker, mcp        |
| File storage     | Single `content` column    | `tool_version_files` + Storage        |
| Manifest         | None                       | `tool_versions.manifest` (JSONB)      |
| Multi-file       | Not supported              | Supported via `tool_version_files`    |
| Embeddings table | `item_embeddings` (single) | Per-type tables                       |
| Vector index     | IVFFlat                    | HNSW (better perf)                    |
| Full-text search | None                       | Generated tsvector + GIN              |
| Search method    | Vector-only                | Hybrid RRF (semantic + keyword)       |
| Backward compat  | N/A                        | Views for `scripts`/`script_versions` |

This evolution enables the full tool system vision with best-practice RAG/vector search while maintaining backward compatibility.
