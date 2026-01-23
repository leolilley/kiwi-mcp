# Unified Tools Architecture: Everything Is A Tool

**Date:** 2026-01-23  
**Status:** Draft  
**Supersedes:** [DATABASE_EVOLUTION_DESIGN.md](./DATABASE_EVOLUTION_DESIGN.md), [DYNAMIC_TOOLS_ARCHITECTURE.md](./DYNAMIC_TOOLS_ARCHITECTURE.md)

---

## Executive Summary

Everything is a tool. Tools reference other tools. Only two irreducible primitives exist in code.

**Key Decisions:**

1. One unified `tools` table for everything
2. No separate `mcp_servers` table - MCP servers are tools with `tool_type: mcp_server`
3. Tools chain via an `executor` field referencing another tool
4. Only two hard-coded primitives: `subprocess` and `http_client`
5. Files live in `tool_version_files` table

---

## The Two Irreducible Primitives

At the absolute bottom, we need code that can:

| Primitive       | What It Does               | Used For                               |
| --------------- | -------------------------- | -------------------------------------- |
| **subprocess**  | Spawn and manage processes | Local MCPs, Python, Bash, Docker, Node |
| **http_client** | Make HTTP requests         | Remote MCPs, APIs, webhooks            |

These are the ONLY hard-coded components. Everything else is data in the registry.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HARD-CODED (in kiwi_mcp/)                        │
│                                                                         │
│     ┌──────────────────────┐          ┌──────────────────────┐         │
│     │     subprocess       │          │     http_client      │         │
│     │     (primitive)      │          │     (primitive)      │         │
│     └──────────┬───────────┘          └──────────┬───────────┘         │
│                │                                  │                     │
└────────────────┼──────────────────────────────────┼─────────────────────┘
                 │                                  │
                 ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                    DYNAMIC (all in `tools` table)                       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         RUNTIMES                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │   │
│  │  │python_runtime│  │ bash_runtime │  │ node_runtime │           │   │
│  │  │executor:     │  │executor:     │  │executor:     │           │   │
│  │  │ subprocess   │  │ subprocess   │  │ subprocess   │           │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │   │
│  └─────────┼─────────────────┼─────────────────┼───────────────────┘   │
│            │                 │                 │                        │
│  ┌─────────┼─────────────────┼─────────────────┼───────────────────┐   │
│  │         ▼                 ▼                 ▼     MCP SERVERS   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │   │
│  │  │ supabase_mcp │  │  github_mcp  │  │ remote_llm_mcp     │     │   │
│  │  │executor:     │  │executor:     │  │executor:           │     │   │
│  │  │ subprocess   │  │ subprocess   │  │ http_client        │     │   │
│  │  │(local spawn) │  │(local spawn) │  │(remote connect)    │     │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬─────────────┘     │   │
│  └─────────┼─────────────────┼─────────────────┼───────────────────┘   │
│            │                 │                 │                        │
│  ┌─────────┼─────────────────┼─────────────────┼───────────────────┐   │
│  │         ▼                 ▼                 ▼       TOOLS       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │supabase_     │  │github_       │  │email_enricher        │   │   │
│  │  │execute_sql   │  │create_pr     │  │(script)              │   │   │
│  │  │executor:     │  │executor:     │  │executor:             │   │   │
│  │  │ supabase_mcp │  │ github_mcp   │  │ python_runtime       │   │   │
│  │  │              │  │              │  │files: [main.py, ...]│   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tool Types

Everything in the registry is a tool. All tools inherit from the two primitives.

| tool_type    | Purpose                        | Executor Points To                             | Has Files? |
| ------------ | ------------------------------ | ---------------------------------------------- | :--------: |
| `primitive`  | Hard-coded capability          | `NULL` (it IS the bottom)                      |     ❌     |
| `runtime`    | Language/environment runner    | A primitive                                    |   Maybe    |
| `mcp_server` | MCP server connection config   | `subprocess` (local) or `http_client` (remote) |   Maybe    |
| `mcp_tool`   | Tool exposed by an MCP server  | An `mcp_server` tool                           |     ❌     |
| `script`     | Executable code                | A `runtime` tool                               |     ✅     |
| `api`        | Direct HTTP API call           | `http_client` primitive                        |     ❌     |
| `directive`  | Instructions for LLM execution | `llm_runtime`                                  |     ✅     |
| `thread`     | Running instance of directive  | `llm_runtime`                                  |     ❌     |
| `knowledge`  | Reference data/context         | `NULL` (pure data, no execution)               |     ✅     |
| `composite`  | Orchestrates multiple tools    | Special handling                               |   Maybe    |

### The Complete Inheritance Tree

```
                         ┌──────────────────────────────────────────┐
                         │              PRIMITIVES                   │
                         │     (only hard-coded components)          │
                         └──────────────────────────────────────────┘
                                    │                │
                         ┌──────────┴──────┐   ┌─────┴───────┐
                         ▼                 ▼   ▼             ▼
                  ┌────────────┐    ┌────────────┐    ┌────────────┐
                  │ subprocess │    │http_client │    │  (none)    │
                  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
                        │                 │                 │
         ┌──────────────┼──────────────┐  │                 │
         │              │              │  │                 │
         ▼              ▼              ▼  │                 ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐               ┌───────────┐
   │  python_  │ │  bash_    │ │  node_    │               │ knowledge │
   │  runtime  │ │  runtime  │ │  runtime  │               │  (data)   │
   └─────┬─────┘ └─────┬─────┘ └───────────┘               └───────────┘
         │             │              │
         ▼             ▼              │
   ┌───────────┐ ┌───────────┐        │
   │  script   │ │  script   │        │
   │ (Python)  │ │  (Bash)   │        │
   └───────────┘ └───────────┘        │
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
   ┌───────────┐               ┌───────────┐               ┌───────────┐
   │llm_runtime│               │mcp_server │               │    api    │
   │           │               │  (local)  │               │           │
   └─────┬─────┘               └─────┬─────┘               └───────────┘
         │                           │
    ┌────┴────┐                      ▼
    │         │                ┌───────────┐
    ▼         ▼                │ mcp_tool  │
┌─────────┐ ┌─────────┐        └───────────┘
│directive│ │ thread  │
│(program)│ │(running)│
└─────────┘ └─────────┘
```

### Directive vs Thread

- **`directive`**: The source code/instructions (like a `.py` file)
- **`thread`**: A running instance that executes a directive (like a process)

```yaml
# A directive (the program)
tool_id: research_topic
tool_type: directive
executor: llm_runtime
version: "1.0.0"
description: "Research a topic thoroughly"
config:
  model_tier: balanced
  max_tokens: 50000
  permissions:
    tools: [web_search, read_web_page]
# Content stored in tool_version_files as "directive.md"

# A thread (runs a directive)
tool_id: research_thread
tool_type: thread
executor: llm_runtime
version: "1.0.0"
config:
  directive: research_topic    # References the directive to execute
  inherit_permissions: true
parameters:
  - name: topic
    type: string
    required: true
```

### Knowledge as a Tool

Knowledge entries are tools with no executor - they're pure data:

```yaml
tool_id: api_design_patterns
tool_type: knowledge
executor: null # No execution, just retrieval
version: "1.0.0"
description: "Common REST API design patterns"
config:
  entry_type: pattern
  source_type: docs
  source_url: https://example.com/api-guide
# Content stored in tool_version_files as "content.md"
```

When a thread needs knowledge:

1. Thread requests knowledge via tool call
2. System loads content from `tool_version_files`
3. Returns content for LLM to use as context

This means **knowledge is searchable, versionable, and retrievable** through the same unified system.

---

## The Kernel Parallel

Kiwi MCP is essentially a **kernel for AI**:

| OS Concept        | Kiwi Equivalent              |
| ----------------- | ---------------------------- |
| Kernel            | Kiwi MCP harness             |
| Thread            | LLM executing a directive    |
| Process           | Session/execution context    |
| Syscall           | Tool call via KiwiProxy      |
| File descriptor   | MCP connection in pool       |
| Permissions (rwx) | `<permissions>` in directive |
| Scheduler         | Cost tracking, rate limiting |
| IPC               | Tools calling other tools    |
| Fork              | Thread spawning sub-thread   |

---

## The `thread` Tool Type (Phase 7 - Future)

A `thread` spawns an LLM to execute a directive with scoped permissions:

```yaml
tool_id: research_thread
tool_type: thread
executor: llm_runtime
version: "1.0.0"
description: "Spawn a research sub-thread"
config:
  directive: research_topic # Which directive to execute
  model_tier: fast # Model selection
  max_tokens: 50000 # Budget limit
  timeout: 300 # Seconds
  inherit_permissions: true # Scope down from parent
parameters:
  - name: topic
    type: string
    required: true
  - name: depth
    type: string
    enum: [shallow, deep]
    default: shallow
```

### Thread Hierarchy & Permission Scoping

```
Parent Thread (full permissions)
    │
    ├─► spawn_thread("research_thread", {topic: "..."})
    │       │
    │       └─► Child Thread (scoped permissions)
    │               - Can only use tools parent allowed
    │               - Can only access paths parent allowed
    │               - Cannot escalate privileges
    │
    └─► spawn_thread("code_review_thread", {...})
            │
            └─► Another Child Thread
                    - Different permission scope
                    - Isolated from sibling
```

### The `llm_runtime`

The `llm_runtime` is a runtime (not a new primitive) that uses `http_client`:

```yaml
tool_id: llm_runtime
tool_type: runtime
executor: http_client
version: "1.0.0"
description: "Runtime for spawning LLM threads"
config:
  providers:
    anthropic:
      url: https://api.anthropic.com/v1/messages
      auth: "Bearer ${ANTHROPIC_API_KEY}"
    openai:
      url: https://api.openai.com/v1/chat/completions
      auth: "Bearer ${OPENAI_API_KEY}"
  model_tiers:
    fast: { provider: anthropic, model: claude-3-haiku-20240307 }
    balanced: { provider: anthropic, model: claude-sonnet-4-20250514 }
    powerful: { provider: anthropic, model: claude-sonnet-4-20250514 }
  defaults:
    max_tokens: 4096
    temperature: 0
```

This keeps the model pure: **only two primitives** (`subprocess`, `http_client`). LLM calling is just HTTP requests managed by a specialized runtime.

---

## The Executor Chain

Every tool (except primitives) has an `executor` field pointing to another tool:

```
email_enricher (script)
    └─► executor: python_runtime (runtime)
            └─► executor: subprocess (primitive)
                    └─► [HARD-CODED: spawns Python process]
```

```
supabase_execute_sql (mcp_tool)
    └─► executor: supabase_mcp (mcp_server)
            └─► executor: subprocess (primitive)
                    └─► [HARD-CODED: spawns npx process, connects stdio]
```

```
stripe_charge (api)
    └─► executor: http_client (primitive)
            └─► [HARD-CODED: makes HTTP POST request]
```

```
remote_analysis (mcp_tool)
    └─► executor: remote_llm_mcp (mcp_server)
            └─► executor: http_client (primitive)
                    └─► [HARD-CODED: connects via SSE]
```

---

## Database Schema

### `tools` - One Table For Everything

```sql
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    tool_id TEXT NOT NULL,                 -- unique identifier (e.g., "python_runtime")
    namespace TEXT DEFAULT 'public',        -- for multi-tenancy
    name TEXT,                              -- display name
    description TEXT,

    -- Type & Execution Chain
    tool_type TEXT NOT NULL,                -- primitive | runtime | mcp_server | mcp_tool | script | api
    executor_id TEXT,                       -- references another tool's tool_id (NULL only for primitives)

    -- Classification
    category TEXT,
    subcategory TEXT,
    tags TEXT[],

    -- Registry metadata
    is_official BOOLEAN DEFAULT false,
    is_builtin BOOLEAN DEFAULT false,       -- true for primitives and core runtimes
    visibility TEXT DEFAULT 'public',       -- public | unlisted | private
    download_count INTEGER DEFAULT 0,
    quality_score NUMERIC(3,2),
    latest_version TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT tools_type_check
        CHECK (tool_type IN ('primitive', 'runtime', 'mcp_server', 'mcp_tool', 'script', 'api', 'composite')),
    CONSTRAINT tools_executor_required
        CHECK (tool_type = 'primitive' OR executor_id IS NOT NULL),
    UNIQUE (namespace, tool_id)
);

CREATE INDEX idx_tools_tool_id ON tools (tool_id);
CREATE INDEX idx_tools_tool_type ON tools (tool_type);
CREATE INDEX idx_tools_executor ON tools (executor_id);
CREATE INDEX idx_tools_category ON tools (category);
```

### `tool_versions` - Versioned Manifests

```sql
CREATE TABLE tool_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    version TEXT NOT NULL,                  -- semver string

    -- The manifest (all config lives here as JSONB)
    manifest JSONB NOT NULL,
    manifest_yaml TEXT,                     -- original YAML for round-trip fidelity

    -- Integrity
    content_hash TEXT NOT NULL,             -- hash of manifest + files
    changelog TEXT,
    is_latest BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (tool_id, version)
);

CREATE INDEX idx_tool_versions_tool_id ON tool_versions (tool_id);
CREATE INDEX idx_tool_versions_latest ON tool_versions (is_latest) WHERE is_latest = true;
```

### `tool_version_files` - Implementation Files

```sql
CREATE TABLE tool_version_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_version_id UUID NOT NULL REFERENCES tool_versions(id) ON DELETE CASCADE,

    -- File identity
    path TEXT NOT NULL,                     -- relative path: 'main.py', 'lib/utils.py', 'Dockerfile'

    -- File metadata
    media_type TEXT,                        -- MIME type: 'text/x-python', 'application/x-sh'
    sha256 TEXT NOT NULL,
    size_bytes INTEGER,
    is_entrypoint BOOLEAN DEFAULT false,    -- marks the main file to execute

    -- Content storage (one of these, not both)
    content_text TEXT,                      -- inline for small files (< 64KB)
    storage_key TEXT,                       -- Supabase Storage key for larger files

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (tool_version_id, path)
);

CREATE INDEX idx_tool_files_version ON tool_version_files (tool_version_id);
CREATE INDEX idx_tool_files_entrypoint ON tool_version_files (is_entrypoint) WHERE is_entrypoint = true;
```

---

## Manifest Examples

### Primitives (seeded, hard-coded behavior)

```yaml
# subprocess primitive
tool_id: subprocess
tool_type: primitive
version: "1.0.0"
description: "Spawns and manages subprocesses"
capabilities:
  - spawn
  - stdio
  - signals
  - timeout
```

```yaml
# http_client primitive
tool_id: http_client
tool_type: primitive
version: "1.0.0"
description: "Makes HTTP/HTTPS requests"
capabilities:
  - request
  - streaming
  - websocket
  - sse
```

### Runtimes (use subprocess primitive)

```yaml
tool_id: python_runtime
tool_type: runtime
executor: subprocess
version: "1.0.0"
description: "Executes Python scripts in isolated venv"
config:
  command: python3
  venv:
    enabled: true
    cache_dir: ~/.cache/kiwi/venvs
  default_packages: []
```

```yaml
tool_id: bash_runtime
tool_type: runtime
executor: subprocess
version: "1.0.0"
description: "Executes Bash scripts"
config:
  command: bash
  shell: /bin/bash
  timeout_default: 300
```

```yaml
tool_id: node_runtime
tool_type: runtime
executor: subprocess
version: "1.0.0"
description: "Executes Node.js scripts"
config:
  command: node
  npm_install: true
```

```yaml
tool_id: deno_runtime
tool_type: runtime
executor: subprocess
version: "1.0.0"
description: "Executes Deno TypeScript/JavaScript"
config:
  command: deno
  args: ["run", "--allow-all"]
```

### MCP Servers - Local (spawned via subprocess)

```yaml
tool_id: supabase_mcp
tool_type: mcp_server
executor: subprocess
version: "1.0.0"
description: "Supabase MCP server for database operations"
config:
  transport: stdio
  command: npx
  args: ["-y", "@supabase/mcp-server-supabase@latest"]
  env:
    SUPABASE_ACCESS_TOKEN: "${SUPABASE_ACCESS_TOKEN}"
  startup_timeout: 10
# schema_cache: populated after first connection
```

```yaml
tool_id: github_mcp
tool_type: mcp_server
executor: subprocess
version: "1.0.0"
description: "GitHub MCP server for repository operations"
config:
  transport: stdio
  command: npx
  args: ["-y", "@modelcontextprotocol/server-github"]
  env:
    GITHUB_TOKEN: "${GITHUB_TOKEN}"
```

```yaml
tool_id: filesystem_mcp
tool_type: mcp_server
executor: subprocess
version: "1.0.0"
description: "Filesystem MCP for file operations"
config:
  transport: stdio
  command: npx
  args: ["-y", "@modelcontextprotocol/server-filesystem", "${ALLOWED_PATH}"]
```

### MCP Servers - Remote (connected via http_client)

```yaml
tool_id: remote_llm_mcp
tool_type: mcp_server
executor: http_client
version: "1.0.0"
description: "Remote LLM provider via MCP"
config:
  transport: sse
  url: "https://api.example.com/mcp/sse"
  headers:
    Authorization: "Bearer ${REMOTE_API_KEY}"
  reconnect: true
  reconnect_delay: 5
```

```yaml
tool_id: hosted_tools_mcp
tool_type: mcp_server
executor: http_client
version: "1.0.0"
description: "Hosted tool execution service"
config:
  transport: websocket
  url: "wss://tools.example.com/mcp"
  auth:
    type: bearer
    token: "${HOSTED_TOOLS_TOKEN}"
```

### MCP Tools (use an mcp_server)

```yaml
tool_id: supabase_execute_sql
tool_type: mcp_tool
executor: supabase_mcp
version: "1.0.0"
description: "Execute SQL queries on Supabase"
config:
  mcp_tool_name: execute_sql
parameters:
  - name: project_id
    type: string
    required: true
    description: "Supabase project ID"
  - name: query
    type: string
    required: true
    description: "SQL query to execute"
```

```yaml
tool_id: github_create_pr
tool_type: mcp_tool
executor: github_mcp
version: "1.0.0"
description: "Create a pull request"
config:
  mcp_tool_name: create_pull_request
parameters:
  - name: repo
    type: string
    required: true
  - name: title
    type: string
    required: true
  - name: head
    type: string
    required: true
  - name: base
    type: string
    required: true
    default: "main"
```

### Script Tools (use a runtime, HAVE FILES)

```yaml
tool_id: email_enricher
tool_type: script
executor: python_runtime
version: "1.2.0"
description: "Enrich email addresses with company data from Clearbit"
config:
  entrypoint: main.py
  requires:
    - httpx>=0.24.0
    - pydantic>=2.0
parameters:
  - name: email
    type: string
    required: true
    description: "Email address to enrich"
outputs:
  type: object
  properties:
    company_name: { type: string }
    domain: { type: string }
    industry: { type: string }
```

**Files in `tool_version_files`:**

| path               | is_entrypoint | content                                               |
| ------------------ | :-----------: | ----------------------------------------------------- |
| `main.py`          |      ✅       | `import httpx\n\nasync def run(email: str):\n    ...` |
| `requirements.txt` |      ❌       | `httpx>=0.24.0\npydantic>=2.0`                        |
| `lib/clearbit.py`  |      ❌       | `class ClearbitClient:\n    ...`                      |

### API Tools (use http_client directly)

```yaml
tool_id: weather_forecast
tool_type: api
executor: http_client
version: "1.0.0"
description: "Get weather forecast for coordinates"
config:
  method: GET
  url_template: "https://api.weather.com/v1/forecast?lat={lat}&lon={lon}&units=metric"
  headers:
    X-API-Key: "${WEATHER_API_KEY}"
  response_transform: "$.forecast.daily[0:7]"
parameters:
  - name: lat
    type: number
    required: true
  - name: lon
    type: number
    required: true
```

```yaml
tool_id: slack_webhook
tool_type: api
executor: http_client
version: "1.0.0"
description: "Send message to Slack webhook"
config:
  method: POST
  url: "${SLACK_WEBHOOK_URL}"
  headers:
    Content-Type: application/json
  body_template:
    text: "{message}"
    channel: "{channel}"
parameters:
  - name: message
    type: string
    required: true
  - name: channel
    type: string
    default: "#general"
```

---

## Execution Flow

### 1. Resolve Tool

```python
async def resolve_tool(tool_id: str) -> Tool:
    """Load tool and its executor chain."""
    tool = await db.query("SELECT * FROM tools WHERE tool_id = $1", tool_id)
    tool.version = await db.query(
        "SELECT * FROM tool_versions WHERE tool_id = $1 AND is_latest = true",
        tool.id
    )
    tool.files = await db.query(
        "SELECT * FROM tool_version_files WHERE tool_version_id = $1",
        tool.version.id
    )
    return tool
```

### 2. Build Executor Chain

```python
async def build_executor_chain(tool: Tool) -> list[Tool]:
    """Recursively resolve executor chain until primitive."""
    chain = [tool]
    current = tool

    while current.executor_id:
        executor = await resolve_tool(current.executor_id)
        chain.append(executor)
        current = executor

    # Chain is now [tool, ..., runtime, primitive]
    return chain
```

### 3. Execute

```python
async def execute_tool(tool_id: str, params: dict) -> Result:
    tool = await resolve_tool(tool_id)
    chain = await build_executor_chain(tool)

    # Primitive is at the end of chain
    primitive = chain[-1]

    if primitive.tool_id == "subprocess":
        return await execute_via_subprocess(chain, params)
    elif primitive.tool_id == "http_client":
        return await execute_via_http(chain, params)
    else:
        raise ValueError(f"Unknown primitive: {primitive.tool_id}")
```

### Example: Executing `email_enricher`

```
1. resolve_tool("email_enricher")
   → tool_type: script, executor: python_runtime
   → files: [main.py, requirements.txt, lib/clearbit.py]

2. build_executor_chain()
   → [email_enricher, python_runtime, subprocess]

3. execute_via_subprocess(chain, {email: "test@acme.com"})
   → Create temp directory
   → Write files from tool_version_files
   → Create venv (python_runtime config)
   → pip install -r requirements.txt
   → Run: python main.py --email="test@acme.com"
   → Capture stdout → parse as JSON
   → Return result
```

### Example: Executing `supabase_execute_sql`

```
1. resolve_tool("supabase_execute_sql")
   → tool_type: mcp_tool, executor: supabase_mcp
   → config: {mcp_tool_name: "execute_sql"}

2. build_executor_chain()
   → [supabase_execute_sql, supabase_mcp, subprocess]

3. execute_via_subprocess(chain, {project_id: "xxx", query: "SELECT ..."})
   → Get/create MCP connection from pool for supabase_mcp
   → Pool spawns: npx -y @supabase/mcp-server-supabase@latest
   → Send MCP request: {tool: "execute_sql", params: {...}}
   → Receive MCP response
   → Return result
```

---

## Seeded Tools (On First Run)

```sql
-- Primitives (hard-coded behavior, registered in DB)
INSERT INTO tools (tool_id, tool_type, executor_id, name, description, is_official, is_builtin) VALUES
('subprocess', 'primitive', NULL, 'Subprocess', 'Spawns and manages processes', true, true),
('http_client', 'primitive', NULL, 'HTTP Client', 'Makes HTTP/HTTPS requests', true, true);

-- Runtimes
INSERT INTO tools (tool_id, tool_type, executor_id, name, description, is_official, is_builtin) VALUES
('python_runtime', 'runtime', 'subprocess', 'Python Runtime', 'Executes Python in isolated venv', true, true),
('bash_runtime', 'runtime', 'subprocess', 'Bash Runtime', 'Executes Bash scripts', true, true),
('node_runtime', 'runtime', 'subprocess', 'Node.js Runtime', 'Executes Node.js scripts', true, true);

-- Official MCP Servers
INSERT INTO tools (tool_id, tool_type, executor_id, name, description, is_official) VALUES
('supabase_mcp', 'mcp_server', 'subprocess', 'Supabase MCP', 'Database operations', true),
('github_mcp', 'mcp_server', 'subprocess', 'GitHub MCP', 'Repository operations', true),
('filesystem_mcp', 'mcp_server', 'subprocess', 'Filesystem MCP', 'File operations', true),
('postgres_mcp', 'mcp_server', 'subprocess', 'Postgres MCP', 'Direct Postgres access', true);

-- Insert corresponding tool_versions with manifests...
```

---

## LLM Can Create Any Tool

### Create a New Runtime

```python
await execute(item_type="tool", action="create", parameters={
    "tool_id": "rust_runtime",
    "tool_type": "runtime",
    "executor": "subprocess",
    "manifest": {
        "version": "1.0.0",
        "description": "Compiles and runs Rust code",
        "config": {
            "compile_command": "rustc",
            "run_command": "./{binary}"
        }
    }
})
```

### Create a New MCP Server

```python
await execute(item_type="tool", action="create", parameters={
    "tool_id": "notion_mcp",
    "tool_type": "mcp_server",
    "executor": "subprocess",
    "manifest": {
        "version": "1.0.0",
        "description": "Notion API via MCP",
        "config": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@notionhq/mcp-server"],
            "env": {"NOTION_API_KEY": "${NOTION_API_KEY}"}
        }
    }
})
```

### Create a Script Tool

```python
await execute(item_type="tool", action="create", parameters={
    "tool_id": "analyze_sentiment",
    "tool_type": "script",
    "executor": "python_runtime",
    "manifest": {
        "version": "1.0.0",
        "description": "Analyze text sentiment",
        "config": {
            "entrypoint": "main.py",
            "requires": ["textblob"]
        },
        "parameters": [
            {"name": "text", "type": "string", "required": True}
        ]
    },
    "files": {
        "main.py": """
from textblob import TextBlob
import json
import sys

def run(text):
    blob = TextBlob(text)
    return {"polarity": blob.sentiment.polarity, "subjectivity": blob.sentiment.subjectivity}

if __name__ == "__main__":
    result = run(sys.argv[1])
    print(json.dumps(result))
"""
    }
})
```

### Create an API Tool

```python
await execute(item_type="tool", action="create", parameters={
    "tool_id": "translate_text",
    "tool_type": "api",
    "executor": "http_client",
    "manifest": {
        "version": "1.0.0",
        "description": "Translate text via DeepL",
        "config": {
            "method": "POST",
            "url": "https://api.deepl.com/v2/translate",
            "headers": {
                "Authorization": "DeepL-Auth-Key ${DEEPL_API_KEY}",
                "Content-Type": "application/json"
            },
            "body_template": {
                "text": ["{text}"],
                "target_lang": "{target_lang}"
            }
        },
        "parameters": [
            {"name": "text", "type": "string", "required": True},
            {"name": "target_lang", "type": "string", "required": True}
        ]
    }
})
```

---

## Embedding Tables (For Semantic Search)

Same as before - per-type tables with HNSW + FTS:

| Table                  | Purpose                     |
| ---------------------- | --------------------------- |
| `directive_embeddings` | Vector + FTS for directives |
| `tool_embeddings`      | Vector + FTS for tools      |
| `knowledge_embeddings` | Vector + FTS for knowledge  |

The `tool_embeddings` table indexes all tool types together (scripts, MCP tools, API tools, etc.)

---

## Summary

### Storage Model (Everything Is Versioned)

**Everything is a tool.** Directives, knowledge, scripts, MCP tools - all stored in the same three tables.

| Layer           | Examples                                        | Stored In                                        | Has Files? |
| --------------- | ----------------------------------------------- | ------------------------------------------------ | :--------: |
| **Primitives**  | `subprocess`, `http_client`                     | `tools` + `tool_versions` (hard-coded behavior)  |     ❌     |
| **Runtimes**    | `python_runtime`, `bash_runtime`, `llm_runtime` | `tools` + `tool_versions`                        |   Maybe    |
| **MCP Servers** | `supabase_mcp`, `github_mcp`                    | `tools` + `tool_versions`                        |   Maybe    |
| **MCP Tools**   | `supabase_execute_sql`, `github_create_pr`      | `tools` + `tool_versions`                        |     ❌     |
| **Scripts**     | `email_enricher`, `deploy_script`               | `tools` + `tool_versions` + `tool_version_files` |     ✅     |
| **APIs**        | `weather_forecast`, `slack_webhook`             | `tools` + `tool_versions`                        |     ❌     |
| **Directives**  | `research_topic`, `code_review`                 | `tools` + `tool_versions` + `tool_version_files` |     ✅     |
| **Threads**     | `research_thread`, `review_thread`              | `tools` + `tool_versions`                        |     ❌     |
| **Knowledge**   | `api_patterns`, `project_context`               | `tools` + `tool_versions` + `tool_version_files` |     ✅     |

### The Three Tables

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              tools                                       │
│  (stable identity: tool_id, tool_type, executor_id, metadata)           │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ 1:N
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           tool_versions                                  │
│  (versioned config: version, manifest JSONB, content_hash)              │
│  ALL tool types have versions here                                       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ 1:N (optional)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        tool_version_files                                │
│  (implementation files: path, content, sha256)                          │
│  Only for tools that HAVE files (scripts, some runtimes)                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Executor Chain

| Tool Type    | Executor Points To                                             |
| ------------ | -------------------------------------------------------------- |
| `primitive`  | `NULL` (bottom of chain)                                       |
| `runtime`    | A primitive (`subprocess` or `http_client`)                    |
| `mcp_server` | A primitive (`subprocess` for local, `http_client` for remote) |
| `mcp_tool`   | An `mcp_server` tool                                           |
| `script`     | A `runtime` tool                                               |
| `api`        | `http_client` primitive                                        |
| `directive`  | `llm_runtime` (when executed, spawns LLM)                      |
| `thread`     | `llm_runtime` (running instance, references a directive)       |
| `knowledge`  | `NULL` (pure data, retrieved not executed)                     |

**Everything is a tool. No separate tables for directives, knowledge, or MCP servers. All inherit from two primitives. All versioned in the same schema.**

---

## Appendix: The Kernel Vision

With this architecture, Kiwi MCP becomes an **AI kernel** that:

1. **Manages threads** - LLMs executing directives with scoped permissions
2. **Provides syscalls** - Tool calls proxied through KiwiProxy
3. **Enforces permissions** - No privilege escalation between threads
4. **Schedules resources** - Cost tracking, rate limiting, timeouts
5. **Handles IPC** - Tools calling other tools, threads spawning threads
6. **Abstracts hardware** - Two primitives (`subprocess`, `http_client`) abstract all I/O

The only things that touch the "metal" are the two primitives. Everything else is declarative data that can be created, versioned, and shared by LLMs themselves.
