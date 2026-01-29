# Lilux + RYE: Ship Roadmap

**Date:** 2026-01-29  
**Status:** In Progress (Phase 3, 4, 7 Complete)  
**Goal:** v0.1.0 Release
**Updated:** 2026-01-30

---

## Critical Clarifications

### Lilux is an MCP, NOT a CLI

Lilux exposes MCP tools. Users interact through an LLM that calls these tools:

```
WRONG (CLI thinking):
$ lilux search "my-directive"

CORRECT (MCP via LLM):
User: "search for lead generation directives"
LLM: [calls mcp__lilux__search(item_type="directive", query="lead generation")]
```

### Package Name: `rye-lilux`

Like "Arch Linux" - RYE running on Lilux.

```
pip install rye-lilux    # Gets lilux kernel + rye content
pip install lilux        # Kernel only (for building own harnesses)
```

---

## Key Decisions Summary

| Decision               | Resolution                                 | Rationale                                                       |
| ---------------------- | ------------------------------------------ | --------------------------------------------------------------- |
| Package naming         | `lilux` (kernel) + `rye-lilux` (content)   | Like "Arch Linux"                                               |
| Monorepo               | Yes, for dev simplicity                    | Easy to develop both together                                   |
| Help tool              | Kernel primitives + command dispatch table | Static, no RAG                                                  |
| System tool            | RYE core tool (protected)                  | Exposes env vars, RAG config, paths                             |
| Registry tool          | RYE core tool (protected)                  | Key management, publish, sync                                   |
| Protection enforcement | Handler-level checks                       | Core tools/knowledge readonly, directives shadowable            |
| Signing                | Compulsory verification on registry load   | User signs via registry tool, keys tied to registry account     |
| Model tiers            | Simple priority list + primary             | Not verbose, just what's needed                                 |
| Vector dimensions      | Auto-detected from first API call          | User provides EMBEDDING_DIMS env var if pre-downloading bundles |
| Dimension mismatch     | Needs error handling                       | Check stored dims vs query dims                                 |

---

## Kernel vs RYE Separation

### Lilux Kernel (pip install `lilux`)

**Contains ONLY primitives:**

```
lilux/
├── server.py              # MCP server
├── tools/
│   ├── search.py          # Find items
│   ├── load.py            # Get/copy items
│   ├── execute.py         # Run items
│   ├── sign.py            # Validate & sign
│   └── help.py            # Kernel primitives + command table
├── handlers/
│   ├── directive/         # Parse & return directive data
│   ├── tool/              # Parse & return tool data
│   └── knowledge/         # Parse & return knowledge data
├── primitives/
│   ├── http_client.py     # HTTP requests
│   └── subprocess.py      # Shell execution
├── storage/
│   └── vector/            # Vector store (uses env config)
└── utils/
```

### RYE Content Bundle (pip install `rye-lilux`)

**Contains all intelligence:**

```
rye/
├── .ai/
│   ├── directives/
│   │   └── core/                    # SHADOWABLE - user can override
│   │       ├── init.md
│   │       ├── bootstrap.md
│   │       ├── sync.md
│   │       └── ...
│   │
│   ├── tools/
│   │   ├── core/                    # PROTECTED - cannot override
│   │   │   ├── system.py            # Env vars, paths, RAG config
│   │   │   ├── rag.py               # Vector search
│   │   │   ├── registry.py          # Registry ops, auth, keys (TODO)
│   │   │   ├── telemetry/           # Telemetry subsystem
│   │   │   │   ├── lib.py           # TelemetryStore, TelemetryContext
│   │   │   │   ├── configure.py     # Toggle on/off
│   │   │   │   ├── status.py        # Show stats
│   │   │   │   ├── clear.py         # Clear stats
│   │   │   │   ├── export.py        # Export for publish
│   │   │   │   └── run_with.py      # Wrapper for tracking
│   │   │   ├── mcp/                 # Protected MCP execution
│   │   │   │   ├── call.py          # Call external MCPs
│   │   │   │   └── discover.py      # Discover MCP tools
│   │   │   ├── threads/             # Thread enforcement (protected)
│   │   │   │   ├── safety_harness.py
│   │   │   │   ├── spawn_thread.py
│   │   │   │   ├── thread_registry.py
│   │   │   │   └── expression_evaluator.py
│   │   │   └── _internal/           # Implementation libs (not tools)
│   │   │       ├── capabilities/    # fs, net, process, db, git, mcp
│   │   │       ├── extractors/      # directive/, tool/, knowledge/
│   │   │       └── parsers/         # markdown, yaml, python_ast
│   │   │
│   │   ├── llm/                     # USER-EXTENSIBLE - configs
│   │   │   ├── anthropic_messages.yaml
│   │   │   ├── openai_chat.yaml
│   │   │   └── pricing.yaml
│   │   │
│   │   ├── threads/                 # USER-EXTENSIBLE - templates
│   │   │   ├── thread_directive.py  # User-facing thread wrapper
│   │   │   ├── anthropic_thread.yaml
│   │   │   ├── openai_thread.yaml
│   │   │   ├── inject_message.py
│   │   │   ├── pause_thread.py
│   │   │   ├── resume_thread.py
│   │   │   └── read_transcript.py
│   │   │
│   │   └── mcp/                     # USER-EXTENSIBLE - server configs
│   │       ├── mcp_stdio.yaml
│   │       ├── mcp_http.yaml
│   │       └── mcp_tool_template.py
│   │
│   └── knowledge/
│       ├── lilux/                   # PROTECTED - kernel docs
│       ├── rye/                     # PROTECTED - rye docs
│       ├── concepts/                # USER-EXTENSIBLE
│       ├── patterns/                # USER-EXTENSIBLE
│       ├── procedures/              # USER-EXTENSIBLE
│       ├── templates/               # USER-EXTENSIBLE
│       └── troubleshooting/         # USER-EXTENSIBLE
```

---

## Help Tool (Kernel Only)

The help tool provides:

1. **Primitive documentation** - search, load, execute, sign, help
2. **Command dispatch table** - NL → MCP tool mapping (for AGENTS.md injection)

```python
# lilux/tools/help.py
class HelpTool(BaseTool):
    """Built-in kernel manual - primitives + command table."""

    TOPICS = {
        "overview": KERNEL_OVERVIEW,
        "search": SEARCH_DOCS,
        "load": LOAD_DOCS,
        "execute": EXECUTE_DOCS,
        "sign": SIGN_DOCS,
        "commands": COMMAND_DISPATCH_TABLE,  # NL → tool mapping for AGENTS.md
    }
```

### AGENTS.md Injection

The `init` and `bootstrap` directives should create/update the user's AGENTS.md with the command dispatch table. This teaches LLMs how to translate natural language into Lilux MCP calls.

```
User: "init my workspace"
LLM: [calls init directive]
     → Creates $USER_PATH/ structure
     → Creates/updates ~/.ai/AGENTS.md with command table
     → "Workspace initialized with Lilux command mappings"

User: "bootstrap this project"
LLM: [calls bootstrap directive]
     → Creates .ai/ in project
     → Creates/updates .ai/AGENTS.md with command table
     → "Project bootstrapped with Lilux integration"
```

The AGENTS.md content includes:

- Command dispatch table (NL → MCP tool mapping)
- Modifier reference (to user, to project, from registry, etc.)
- Does NOT need a brief description of the 5 primitives here. That is picked up by the built in tool descriptions and other help commands if needed

### Command Dispatch Table

**Note:** `project_path` is ALWAYS required for all operations (except `help`).

```markdown
## Natural Language → MCP Tool Mapping

| User Says             | MCP Tool Call                                                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| "search for X"        | `mcp__lilux__search(item_type="directive", query="X", project_path="/path/to/project")`                                             |
| "find tools about X"  | `mcp__lilux__search(item_type="tool", query="X", project_path="/path/to/project")`                                                  |
| "load directive X"    | `mcp__lilux__load(item_type="directive", item_id="X", source="project", project_path="/path/to/project")`                           |
| "get X from registry" | `mcp__lilux__load(item_type="directive", item_id="X", source="registry", project_path="/path/to/project")`                          |
| "run directive X"     | `mcp__lilux__execute(item_type="directive", item_id="X", project_path="/path/to/project")`                                          |
| "execute tool X"      | `mcp__lilux__execute(item_type="tool", item_id="X", parameters={...}, project_path="/path/to/project")`                             |
| "create tool X"       | `mcp__lilux__execute(item_type="directive", item_id="create_tool", parameters={"tool_name": "X"}, project_path="/path/to/project")` |
| "sign directive X"    | `mcp__lilux__sign(item_type="directive", item_id="X", project_path="/path/to/project")`                                             |
| "init workspace"      | `mcp__lilux__execute(item_type="directive", item_id="init", project_path="/path/to/project")`                                       |
| "sync from registry"  | `mcp__lilux__execute(item_type="directive", item_id="sync", project_path="/path/to/project")`                                       |
| "help with search"    | `mcp__lilux__help(topic="search")`                                                                                                  |
| "show commands"       | `mcp__lilux__help(topic="commands")`                                                                                                |

## Modifiers

| Modifier        | Effect                         |
| --------------- | ------------------------------ |
| "to user space" | `destination="user"`           |
| "to project"    | `destination="project"`        |
| "from registry" | `source="registry"`            |
| "dry run"       | `parameters={"dry_run": true}` |
```

---

## System Tool (RYE Core - Protected)

Exposes environment configuration to LLMs:

```python
# .ai/tools/core/system.py
"""System information tool - exposes safe env vars and paths."""

ITEMS = {
    "paths": "Userspace, home, cwd, project paths",
    "rag": "Embedding config from env vars",
    "runtime": "Platform, arch, Python version",
}

async def execute(item_id: str, project_path: str) -> dict:
    if item_id == "paths":
        return {
            "userspace_dir": os.environ.get("USER_PATH", str(Path.home() / ".ai")),
            "home_dir": str(Path.home()),
            "cwd": os.getcwd(),
            "project_path": project_path,
            "userspace_exists": (Path.home() / ".ai").exists(),
        }

    if item_id == "rag":
        return {
            "embedding_url": os.environ.get("EMBEDDING_URL"),
            "embedding_model": os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
            "embedding_dims": int(os.environ.get("EMBEDDING_DIMS", "0")),  # 0 = auto-detect
            "vector_db_url": os.environ.get("VECTOR_DB_URL"),
            "configured": bool(os.environ.get("EMBEDDING_URL")),
        }

    if item_id == "runtime":
        return {
            "platform": sys.platform,
            "arch": platform.machine(),
            "python_version": sys.version,
        }

    return {"error": f"Unknown system item: {item_id}"}
```

---

## Registry Tool (RYE Core - Protected)

Handles registry operations including authentication and key management:

```python
# .ai/tools/core/registry.py
"""Registry operations - auth, sync, publish, key management."""

ACTIONS = {
    # Authentication (device authorization flow)
    "login": "Authenticate with registry (opens browser)",
    "logout": "Clear local auth session",
    "whoami": "Show current authenticated user",

    # Registry operations (require auth)
    "sync": "Download/update items from registry",
    "publish": "Upload signed items to registry",

    # Key management (require auth)
    "keys_generate": "Generate new signing keypair",
    "keys_list": "List trusted public keys",
    "keys_trust": "Manually add a public key to trusted list",
    "keys_revoke": "Remove a public key from trusted list",
}
```

### Authentication Flow (No Custom UI)

Uses Supabase CLI pattern - browser-based auth with ECDH key exchange:

```
User: "login to registry"
LLM: [calls registry tool with action="login"]

1. Tool generates session ID + ECDH keypair
2. Opens browser: https://registry.lilux.dev/auth?session_id=xxx&public_key=yyy
3. User authenticates via Supabase Auth (GitHub, Google, email)
4. Server encrypts access token with shared secret
5. Tool polls for encrypted token, decrypts locally
6. Stores session in ~/.local/share/lilux/auth/session.json

User: "who am I?"
LLM: [calls registry tool with action="whoami"]
     "leo@github (authenticated since 2026-01-29)"
```

**No UI needed** - uses existing Supabase dashboard for signup/login.

**CI override:** Set `LILUX_REGISTRY_TOKEN` env var to skip interactive auth.

### Key Management

- Users get keypair when they create registry account
- Private key downloaded and stored locally in system space
- Public key stored in registry with namespace claim
- Signing/verification happens via registry tool
- **Auto-trust on download:** When downloading a signed item, the signer's public key is automatically fetched from registry and added to local trusted keys

---

## Protection Enforcement

**Handler-level checks in execute/load:**

```python
# In execute tool or handler routing
PROTECTED_PREFIXES = {
    "tool": ["core/"],           # core tools readonly
    "knowledge": ["kernel/"],     # kernel docs readonly
}

# Directives can be shadowed - check priority order
SHADOWABLE_TYPES = ["directive"]

async def resolve_item(item_type: str, item_id: str, source: str):
    # Check if protected
    if item_type in PROTECTED_PREFIXES:
        for prefix in PROTECTED_PREFIXES[item_type]:
            if item_id.startswith(prefix):
                # ONLY load from rye bundle, never project/user
                return load_from_rye_bundle(item_type, item_id)

    # Directives: priority resolution (project > user > rye)
    if item_type in SHADOWABLE_TYPES:
        # Try project first
        item = await try_load_from_project(item_type, item_id)
        if item:
            return item

        # Try user space
        item = await try_load_from_user(item_type, item_id)
        if item:
            return item

    # Fall back to rye bundle
    return load_from_rye_bundle(item_type, item_id)
```

---

## Signing & Verification

### Compulsory Verification on Registry Load

```python
async def load_from_registry(item_type: str, item_id: str) -> dict:
    item = await fetch_from_supabase(item_type, item_id)

    # ALWAYS verify signature - compulsory
    if not verify_signature(item.content, item.signature, item.signer_namespace):
        raise IntegrityError(
            f"Item '{item_id}' signature verification failed. "
            f"Content may have been tampered with."
        )

    return item
```

### User Signing via Registry Tool

```python
# User publishes an item
async def publish(item_type: str, item_id: str, content: str):
    # Load user's private key (from system space)
    private_key = load_private_key()
    if not private_key:
        raise AuthError(
            "No private key found. Generate keys with: "
            "execute(item_type='tool', item_id='core/registry', "
            "parameters={'action': 'keys_generate'})"
        )

    # Sign content
    signature = sign_content(content, private_key)

    # Upload with signature + namespace
    await upload_to_registry(
        item_type=item_type,
        item_id=item_id,
        content=content,
        signature=signature,
        namespace=get_user_namespace(),
    )
```

### Key Storage

```
~/.local/share/lilux/         # System space (protected)
├── keys/
│   ├── private.pem           # User's private key
│   ├── public.pem            # User's public key
│   └── trusted/              # Trusted public keys
│       ├── core.pub          # RYE team (bundled)
│       └── {namespace}.pub   # Other trusted authors
```

---

## Model Tiers (Simplified)

```yaml
# ~/.ai/config/models.yaml
tiers:
  reasoning:
    priority:
      - anthropic/claude-sonnet-4-20250514
      - openai/o1
      - google/gemini-2.5-pro
    primary: anthropic/claude-sonnet-4-20250514

  balanced:
    priority:
      - anthropic/claude-sonnet-4-20250514
      - openai/gpt-4o
    primary: anthropic/claude-sonnet-4-20250514

  fast:
    priority:
      - anthropic/claude-3-5-haiku-20241022
      - openai/gpt-4o-mini
    primary: anthropic/claude-3-5-haiku-20241022

on_unavailable: fallback # Use next in priority, or "error" to fail
```

### Tier Resolution with Error Handling

```python
def get_model_for_tier(tier: str) -> str:
    config = load_models_config()

    if tier not in config.get("tiers", {}):
        available = list(config.get("tiers", {}).keys())
        raise TierNotFoundError(
            f"Unknown tier '{tier}'. Available tiers: {available}"
        )

    tier_config = config["tiers"][tier]
    primary = tier_config.get("primary")
    priority = tier_config.get("priority", [])

    if primary not in priority:
        raise ModelNotInTierError(
            f"Primary model '{primary}' not in tier '{tier}' priority list. "
            f"Priority list: {priority}"
        )

    return primary
```

---

## Vector Dimensions

### Current State

- `EmbeddingService._dimension` is auto-detected from first API call
- `SimpleVectorStore` stores `dimension` per embedding
- **No mismatch check exists** when querying with different dimension embeddings

### Required Fix

```python
# In simple_store.py search method
async def search(self, query: str, ...):
    query_embedding = await self.embedder.embed(query)
    query_dim = len(query_embedding)

    # Get stored dimension from meta or first embedding
    stored_dim = self._get_stored_dimension()

    if stored_dim and query_dim != stored_dim:
        raise DimensionMismatchError(
            f"Query embedding dimension ({query_dim}) does not match "
            f"stored embeddings ({stored_dim}). "
            f"Check EMBEDDING_MODEL and EMBEDDING_DIMS configuration."
        )

    # ... rest of search
```

### User Configuration

```bash
# User sets embedding config in environment
export EMBEDDING_URL="https://api.openai.com/v1/embeddings"
export EMBEDDING_API_KEY="sk-..."
export EMBEDDING_MODEL="text-embedding-3-small"
export EMBEDDING_DIMS="1536"  # For pre-downloading matching vector bundle

# Or for local Ollama
export EMBEDDING_URL="http://localhost:11434/api/embeddings"
export EMBEDDING_MODEL="nomic-embed-text"
export EMBEDDING_DIMS="768"
```

### Init Auto-Detection

```xml
<step name="setup_vectors">
  <action>
    Query system tool for RAG config:
    rag = execute(item_type="tool", item_id="core/system", parameters={"item": "rag"})

    If rag.configured:
      dims = rag.embedding_dims
      If dims > 0:
        Download pre-computed vectors: rye-core-vectors-{dims}.tar.gz
      Else:
        Skip pre-download (will embed on demand, auto-detect dims)
    Else:
      Log: "RAG not configured - semantic search unavailable"
  </action>
</step>
```

---

## Monorepo Structure

```
lilux-project/
├── packages/
│   ├── lilux/                    # Kernel package
│   │   ├── lilux/
│   │   │   ├── server.py
│   │   │   ├── tools/
│   │   │   ├── handlers/
│   │   │   ├── primitives/
│   │   │   └── storage/
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── rye-lilux/                # Content package
│       ├── rye/
│       │   └── .ai/
│       │       ├── directives/
│       │       ├── tools/
│       │       └── knowledge/
│       ├── pyproject.toml        # depends: lilux>=0.1.0
│       └── README.md
│
├── tests/                        # Shared tests
├── pyproject.toml                # Workspace config
├── Makefile                      # dev, test, publish
└── README.md
```

### Development Workflow

```bash
# Clone monorepo
git clone github.com/leolilley/lilux-project
cd lilux-project

# Install both packages in editable mode
pip install -e packages/lilux -e packages/rye-lilux

# Or with uv
uv pip install -e packages/lilux -e packages/rye-lilux

# Run tests
pytest

# Publish (lilux first, then rye-lilux)
make publish
```

---

## Ship Phases

### Phase 0: Monorepo Setup (1 day) ✅ COMPLETE

- [x] Create `rye-lilux` monorepo structure (in kiwi-mcp/rye-lilux/)
- [x] Migrate kernel code to `lilux/` package
- [x] Migrate .ai content to `rye/.ai/`
- [x] Rename all "kiwi" → "lilux"
- [ ] Update all signatures (deferred)
- [ ] Set up dev workflow (deferred - using .venv currently)

### Phase 1: Help Tool + Command Table (0.5 day) ✅ COMPLETE

- [x] help.py exists in lilux/tools/
- [x] Command dispatch table in AGENTS.md
- [x] No RAG dependencies in kernel help
- [x] Test passes for help import

### Phase 2: System Tool (0.5 day) ✅ COMPLETE

- [x] Created `rye/.ai/tools/core/system.py`
- [x] Exposes: paths, rag, runtime
- [x] Reads from env vars
- [x] Added to core (protected) folder

### Phase 3: Registry Tool + Auth (1.5 days) ✅ COMPLETE

- [x] Create `.ai/tools/core/registry.py` (12 actions)
- [x] Implement auth actions: signup, login, login_poll, logout, whoami
- [x] Device auth flow: session ID + ECDH keypair generation
- [x] Browser launch with webbrowser module
- [x] Poll for encrypted token, decrypt with ECDH
- [x] **Secure credential storage** (keyring via AuthStore):
  - [x] Primary: System keyring via `keyring` library (service: `rye`)
  - [x] AuthStore runtime in `rye/.ai/tools/runtimes/auth.py`
  - [x] Token refresh support with scopes
- [x] Implement item actions: pull, push, set_visibility (replaced sync)
- [x] Implement key actions: keys_generate, keys_list, keys_trust, keys_revoke
- [x] **Signing key storage** (PEM files in ~/.rye/keys/):
  - [x] Private keys: ~/.rye/keys/{id}.private.pem (mode 0600)
  - [x] Public keys: ~/.rye/keys/{id}.public.pem
  - [x] Primary symlink: ~/.rye/keys/primary.pem
  - [x] Trusted keys: ~/.rye/keys/trusted/
- [x] **"Dumb kernel" restructuring**:
  - [x] Moved primitives to `rye/.ai/tools/primitives/` (http_client, subprocess, errors)
  - [x] Moved runtimes to `rye/.ai/tools/runtimes/` (auth, env_resolver)
  - [x] Moved capabilities to `rye/.ai/tools/capabilities/` (capability_tokens)
- [x] **Supabase Edge Functions** (3 deployed):
  - [x] device-auth: Start auth flow, store ECDH public key
  - [x] device-auth-callback: Handle OAuth callback, encrypt token
  - [x] device-auth-poll: Return encrypted token for CLI decryption
- [x] Database trigger: auto-create public.users on auth.users insert
- [x] Telemetry integration: all registry actions tracked
- [x] Add to protected list (# PROTECTED comment)
- [x] **User data consolidation** (See docs/DIRECTORY_ARCHITECTURE.md):
  - [x] ~/.ai/ for user content (directives, tools, knowledge)
  - [x] $XDG_STATE_HOME/rye/ for RYE state (signing-keys, sessions, telemetry.yaml)
  - [x] $XDG_CACHE_HOME/lilux/ for kernel cache (http, vectors)
  - [x] Cross-platform: Linux XDG, macOS ~/Library/, Windows %LOCALAPPDATA%

### Phase 4: Protection Enforcement (0.5 day) ✅ COMPLETE

**Note:** Protection is enforced in RYE harness (directives/tools), NOT in lilux kernel.
The kernel is "dumb" - RYE provides the intelligence.

- [x] Create `rye/.ai/tools/core/protection.py` - protection checking tool
- [x] Protected prefixes: tools (core/, primitives/, runtimes/, capabilities/), knowledge (lilux/, rye/)
- [x] Directives always shadowable
- [x] Actions: check (is_protected), validate (file_path allowed)
- [x] Test core tools cannot be shadowed (24 tests pass)
- [x] Test core knowledge cannot be shadowed
- [x] Test directives CAN be shadowed

### Phase 5: Dimension Mismatch Check (0.5 day)

- [ ] Add dimension tracking to vector store
- [ ] Add mismatch error on search
- [ ] Clear error message with config guidance
- [ ] Test with mismatched dimensions

### Phase 6: Init & Bootstrap Directives (1 day)

- [ ] Update init to use system tool
- [ ] Auto-detect RAG config from env
- [ ] Download matching vector bundle if dims provided
- [ ] Create userspace structure ($USER_PATH/)
- [ ] Create/update AGENTS.md with command dispatch table
- [ ] Get AGENTS.md template from help tool (agents_md topic)
- [ ] Update bootstrap directive for project-level setup
- [ ] Bootstrap creates .ai/AGENTS.md with command table

### Phase 7: Registry Setup (1 day) ✅ COMPLETE

- [x] Supabase tables with namespacing (Rye Registry project: jvdgicalhvhaqtcalseq)
- [x] 17 tables created: users, user_stats, user_activity, directives, directive_versions, tools, tool_versions, tool_version_files, knowledge, knowledge_versions, item_embeddings, favorites, ratings, reports, follows, signing_keys, bundles
- [x] Telemetry sync functions: update_user_stats, upsert_user_activity, increment_execution_count, batch_increment_executions
- [x] Search functions: search_embeddings, search_tools, get_knowledge_with_content
- [x] Trust score function: get_user_trust_score
- [x] Executor chain resolution: resolve_executor_chain
- [ ] Signature verification on load (TODO)
- [ ] Public key storage (table exists, verification TODO)
- [ ] Upload core RYE content (TODO after Phase 3)

### Phase 8: Model Tier Error Handling (0.5 day)

- [ ] Implement tier resolution with errors
- [ ] Error when tier not found
- [ ] Error when primary not in priority list
- [ ] Test harness uses tiers correctly

### Phase 9: Package & Publish (1 day)

- [ ] lilux package builds and tests
- [ ] rye-lilux package builds with bundled .ai/
- [ ] Publish lilux to PyPI first
- [ ] Publish rye-lilux to PyPI
- [ ] Test `pip install rye-lilux` end-to-end

---

## Success Criteria

```
# User connects MCP to their LLM client
MCP Config: python -m lilux.server

# First interaction (via LLM)
User: "init my workspace"
LLM: [calls mcp__lilux__execute(item_type="directive", item_id="init")]
     → Init queries system tool for env vars
     → Creates $USER_PATH/ structure (default ~/.ai/)
     → Downloads vectors if EMBEDDING_DIMS set

# Search
User: "search for lead generation tools"
LLM: [calls mcp__lilux__search(item_type="tool", query="lead generation")]

# Create (via directive)
User: "create a new directive for email outreach"
LLM: [calls mcp__lilux__execute(item_type="directive", item_id="create_directive", ...)]

# Login (device auth flow - opens browser)
User: "login to registry"
LLM: [calls mcp__lilux__execute(item_type="tool", item_id="core/registry",
      parameters={"action": "login"})]
     → Opens browser to registry.lilux.dev/auth
     → User logs in via Supabase (GitHub, Google, email)
     → Tool polls for token, stores locally
     → "Authenticated as leo@github"

# Publish (requires auth)
User: "publish my-directive to registry"
LLM: [calls mcp__lilux__execute(item_type="tool", item_id="core/registry",
      parameters={"action": "publish", "item_id": "my-directive"})]

# Help
User: "show me the command reference"
LLM: [calls mcp__lilux__help(topic="commands")]
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      USER'S LLM CLIENT                            │
│              (Claude Desktop, Cursor, etc.)                       │
│                                                                   │
│  User: "init my workspace"                                       │
│  LLM: [calls mcp__lilux__execute(...)]                           │
└───────────────────────────────────────────────────────────────────┘
                            │ MCP Protocol (stdio)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    LILUX MCP SERVER                               │
│                                                                   │
│  Kernel (pip install lilux):                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 5 Primitive Tools:                                          │ │
│  │   search │ load │ execute │ sign │ help                     │ │
│  │                                                              │ │
│  │ help includes: primitive docs + command dispatch table      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  RYE Content (pip install rye-lilux):                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ PROTECTED (core/):                                          │ │
│  │   .ai/tools/core/system.py     ← env vars, paths           │ │
│  │   .ai/tools/core/registry.py   ← sync, publish, keys       │ │
│  │   .ai/tools/core/rag.py        ← vector search             │ │
│  │   .ai/tools/core/telemetry/    ← usage tracking            │ │
│  │   .ai/tools/core/mcp/          ← call/discover (protected) │ │
│  │   .ai/tools/core/threads/      ← enforcement (harness)     │ │
│  │   .ai/tools/core/_internal/    ← capabilities, parsers     │ │
│  │   .ai/knowledge/lilux/*        ← kernel documentation      │ │
│  │   .ai/knowledge/rye/*          ← rye documentation         │ │
│  │                                                              │ │
│  │ SHADOWABLE (user can override):                             │ │
│  │   .ai/directives/core/*        ← init, bootstrap, sync     │ │
│  │                                                              │ │
│  │ USER-EXTENSIBLE:                                            │ │
│  │   .ai/tools/llm/*              ← LLM configs               │ │
│  │   .ai/tools/threads/*          ← thread templates          │ │
│  │   .ai/tools/mcp/*              ← server configs            │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      USER SPACES                                  │
│                                                                   │
│  User (~/.ai/):                Project (.ai/):                   │
│  ├── directives/               ├── directives/                   │
│  ├── tools/                    ├── tools/                        │
│  ├── knowledge/                ├── knowledge/                    │
│  └── config/                   └── config/                       │
│      └── models.yaml               └── vector.yaml               │
│                                                                   │
│  System (~/.local/share/lilux/):                                 │
│  ├── keys/private.pem          ← user's signing key             │
│  ├── keys/trusted/*.pub        ← trusted author keys            │
│  ├── cache/vectors/            ← pre-computed embeddings        │
│  └── logs/                     ← execution logs                 │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    REGISTRY (Supabase)                            │
│                                                                   │
│  items:                         user_keys:                       │
│  ├── core/init (official)       ├── core → RYE team key         │
│  ├── leo/my-tool (signed)       ├── leo → leo's public key      │
│  └── jane/workflow (signed)     └── jane → jane's public key    │
│                                                                   │
│  vector_bundles:                                                 │
│  ├── rye-core-384.tar.gz                                         │
│  ├── rye-core-768.tar.gz                                         │
│  ├── rye-core-1536.tar.gz                                        │
│  └── rye-core-3072.tar.gz                                        │
└──────────────────────────────────────────────────────────────────┘
```

---

---

## RYE Core Content Inventory

### Tools Structure (Split by Override Semantics)

**Principle:** Split by protection level, not by domain. Protected enforcement pieces go in `core/`, extensible configs/templates stay at top-level.

```
.ai/tools/
├── core/                           # PROTECTED - cannot override
│   │                               # Security-critical, auth, enforcement
│   ├── system.py                   # Env vars, paths, RAG config
│   ├── registry.py                 # Sync, publish, key management (TODO)
│   ├── rag.py                      # Vector search
│   │
│   ├── telemetry/                  # Telemetry subsystem
│   │   ├── lib.py                  # TelemetryStore, TelemetryContext
│   │   ├── configure.py            # Toggle on/off
│   │   ├── status.py               # Show stats
│   │   ├── clear.py                # Clear stats
│   │   ├── export.py               # Export for publish
│   │   └── run_with.py             # Wrapper for tracking
│   │
│   ├── mcp/                        # Protected MCP execution
│   │   ├── call.py                 # Call external MCPs
│   │   └── discover.py             # Discover MCP tools
│   │
│   ├── threads/                    # Thread enforcement (protected)
│   │   ├── safety_harness.py       # Harness with limits, permissions, hooks
│   │   ├── spawn_thread.py         # Low-level thread spawning
│   │   ├── thread_registry.py      # SQLite persistence for state
│   │   └── expression_evaluator.py # Evaluate hook conditions
│   │
│   └── _internal/                  # Implementation libs (not user-facing tools)
│       ├── capabilities/           # fs, net, process, db, git, mcp
│       ├── extractors/             # directive/, tool/, knowledge/
│       └── parsers/                # markdown, yaml, python_ast
│
├── llm/                            # USER-EXTENSIBLE - LLM configs
│   ├── anthropic_messages.yaml     # Anthropic API config
│   ├── openai_chat.yaml            # OpenAI API config
│   └── pricing.yaml                # Token pricing per model
│
├── threads/                        # USER-EXTENSIBLE - templates, non-enforcement
│   ├── thread_directive.py         # User-facing thread wrapper
│   ├── anthropic_thread.yaml       # Anthropic-specific config
│   ├── openai_thread.yaml          # OpenAI-specific config
│   ├── inject_message.py           # Add messages to running threads
│   ├── pause_thread.py             # Pause thread execution
│   ├── resume_thread.py            # Resume paused threads
│   └── read_transcript.py          # Read thread transcript/history
│
└── mcp/                            # USER-EXTENSIBLE - server configs
    ├── mcp_stdio.yaml              # Stdio transport config
    ├── mcp_http.yaml               # HTTP transport config
    └── mcp_tool_template.py        # Template for new MCP tools
```

**Protection Rules:**

- `core/**` = PROTECTED (cannot be shadowed by user/project)
- `llm/**`, `threads/**`, `mcp/**` = USER-EXTENSIBLE (can shadow with ~/.ai/ or .ai/)

### Core Directives (Shadowable - User Can Override)

**Primary Tool Wrappers (dumb, just call the primitive):**

```
.ai/directives/core/
├── search_directives.md    # Search for directives
├── search_tools.md         # Search for tools
├── search_knowledge.md     # Search for knowledge
├── load_directive.md       # Load a directive (view/copy)
├── load_tool.md            # Load a tool
├── load_knowledge.md       # Load knowledge entry
├── create_directive.md     # Create new directive
├── create_tool.md          # Create new tool
├── create_knowledge.md     # Create knowledge entry
├── execute_directive.md    # Execute a directive
├── execute_tool.md         # Execute a tool
├── execute_knowledge.md    # Execute knowledge (no metadata included)
├── sign_directive.md       # Sign a directive
├── sign_tool.md            # Sign a tool
├── sign_knowledge.md       # Sign knowledge
├── delete_directive.md     # Delete a directive
├── delete_tool.md          # Delete a tool
├── delete_knowledge.md     # Delete knowledge
├── edit_directive.md       # Edit existing directive
├── edit_tool.md            # Edit existing tool
├── edit_knowledge.md       # Edit knowledge
```

**Setup & Sync:**

```
├── init.md                 # Initialize userspace
├── bootstrap.md            # Bootstrap project .ai/
├── context.md              # Generate project context
```

**Registry & Sync:**

```
├── sync.md                 # Sync all (directives, tools, knowledge)
├── sync_directives.md      # Sync directives: project → registry → user
├── sync_tools.md           # Sync tools: project → registry → user
├── sync_knowledge.md       # Sync knowledge: project → registry → user
├── sync_config.md          # Sync agent/model config
```

**Publishing:**

```
├── publish.md              # Publish single item to registry
├── publish_directive.md    # Publish directive (validates first)
├── publish_tool.md         # Publish tool (validates first)
├── publish_knowledge.md    # Publish knowledge entry
```

**Bundles (Collections):**

```
├── bundle_create.md        # Create collection from .ai/
├── bundle_install.md       # Install collection from registry
├── bundle_publish.md       # Publish collection to registry
├── bundle_list.md          # List installed collections
├── bundle_update.md        # Update installed collections
├── bundle_remove.md        # Remove installed collection
```

**Registry Management:**

```
├── registry_status.md      # Check registry connection & account
├── registry_search.md      # Search registry for items/bundles
├── registry_info.md        # Get info about registry item
```

**Key Management:**

```
├── keys_generate.md        # Generate new keypair (requires account)
├── keys_list.md            # List trusted public keys
├── keys_trust.md           # Manually trust a public key
├── keys_revoke.md          # Revoke a trusted key
├── keys_export.md          # Export public key for sharing
```

**Telemetry:**

```
├── telemetry_enable.md     # Enable telemetry tracking (calls configure_telemetry tool)
├── telemetry_disable.md    # Disable telemetry tracking
├── telemetry_status.md     # Show current telemetry config
├── telemetry_clear.md      # Clear telemetry from item(s) (calls clear_telemetry tool)
```

**Threading (user-friendly wrappers - NOT raw spawn_thread):**

```
├── thread_directive.md     # Run a directive in fresh context (primary entry point)
├── thread_parallel.md      # Run multiple directives in parallel threads
├── thread_status.md        # Check thread status
├── thread_cancel.md        # Cancel running thread
├── thread_list.md          # List all threads with filters
├── thread_read.md          # Read thread transcript/history
├── thread_inject.md        # Inject message into running thread
├── thread_pause.md         # Pause a running thread
├── thread_resume.md        # Resume a paused thread
├── thread_cost.md          # Get cost breakdown (tokens, USD, turns)
├── thread_wait.md          # Block until thread completes
├── thread_result.md        # Get final result from completed thread
```

**Discovery & Exploration:**

```
├── discover_llm.md         # Discover models from LLM provider
├── discover_mcp.md         # Discover tools from external MCP
├── add_mcp.md              # Add external MCP to config
├── list_mcps.md            # List configured MCPs
```

**Self-Improvement:**

```
├── anneal_directive.md     # Improve directive from failure
├── anneal_tool.md          # Improve tool from failure
```

### Core Knowledge (PROTECTED - Cannot Override)

**Kernel Documentation** - How to use the 5 primitives:

```
.ai/knowledge/kernel/
├── overview.md             # Lilux kernel overview - what it is, philosophy
├── primitives.md           # The 5 tools: search, load, execute, sign, help
├── search.md               # Search tool - parameters, examples, tips
├── load.md                 # Load tool - sources, destinations, copying
├── execute.md              # Execute tool - running directives/tools
├── sign.md                 # Sign tool - validation, signatures, integrity
├── help.md                 # Help tool - topics, command table
├── item_types.md           # Directive vs Tool vs Knowledge - when to use each
├── command_table.md        # NL → MCP tool mapping (full reference)
├── project_path.md         # Why project_path is always required
└── error_handling.md       # Common errors and how to resolve
```

**RYE Core Features** - Threading, harness, discovery:

```
.ai/knowledge/rye/
├── overview.md             # RYE content layer - what ships with it
├── threading.md            # Why threading matters, fresh contexts
├── harness.md              # Safety harness - limits, cost tracking
├── permissions.md          # Permission model - capabilities, enforcement
├── capabilities.md         # Capability tokens - attenuation, inheritance
├── hooks.md                # Hook system - error recovery, deviation handling
├── limits.md               # Cost limits - turns, tokens, USD, duration
├── discovery.md            # MCP discovery - adding external MCPs
├── registry.md             # Registry - sync, publish, bundles
├── signing.md              # Signing & verification - keys, trust
├── model_tiers.md          # Model tiers - reasoning, balanced, fast
└── init.md                 # Initialization - first-time setup flow
```

**Concepts** - Core ideas that underpin the system:

```
.ai/knowledge/concepts/
├── doe_framework.md        # Directive-Orchestration-Execution pattern
├── everything_to_something.md  # Restriction vs empowerment philosophy
├── context_rot.md          # Why long contexts degrade quality
├── deterministic_execution.md  # LLM decides, code executes
├── self_annealing.md       # Learning from failures
├── subagent_isolation.md   # Fresh context principle
└── mcp_ecosystem.md        # How MCPs work together
```

**Patterns** - Reusable solutions for common problems:

```
.ai/knowledge/patterns/
├── orchestration/
│   ├── parallel_execution.md   # Running tasks in parallel threads
│   ├── sequential_chain.md     # Step-by-step directive chains
│   ├── fan_out_fan_in.md       # Distribute work, aggregate results
│   └── recursive_refinement.md # Iterative improvement loops
│
├── agent_design/
│   ├── reasoning_loop.md       # Think → Act → Observe cycle
│   ├── tool_selection.md       # How to pick the right tool
│   ├── context_engineering.md  # Keeping context focused
│   └── graceful_degradation.md # Handling failures gracefully
│
├── verification/
│   ├── checkpoint_pattern.md   # Save progress, resume later
│   ├── proof_carrying.md       # Attach verification to results
│   └── deviation_handling.md   # What to do when things go wrong
│
└── resource_management/
    ├── cost_budgeting.md       # Managing token/USD spend
    ├── context_window_mgmt.md  # Staying under limits
    └── parallel_efficiency.md  # Optimal thread count
```

**Procedures** - Step-by-step guides:

```
.ai/knowledge/procedures/
├── first_directive.md      # Create your first directive
├── first_tool.md           # Create your first tool
├── first_knowledge.md      # Create your first knowledge entry
├── add_llm_provider.md     # Connect a new LLM provider
├── add_external_mcp.md     # Add an external MCP
├── publish_to_registry.md  # Publish your work
├── create_bundle.md        # Bundle for sharing
├── setup_rag.md            # Configure vector search
├── thread_long_task.md     # Run long tasks in threads
├── debug_directive.md      # Debug a failing directive
└── anneal_from_failure.md  # Improve from errors
```

**Templates** - Starting points for new items:

```
.ai/knowledge/templates/
├── directive_simple.md     # Basic directive template
├── directive_threaded.md   # Directive with threading
├── directive_parallel.md   # Parallel execution template
├── tool_python.md          # Python tool template
├── tool_yaml.md            # YAML tool config template
├── knowledge_concept.md    # Concept entry template
├── knowledge_pattern.md    # Pattern entry template
├── knowledge_procedure.md  # Procedure entry template
└── collection.toml         # Collection manifest template
```

**Troubleshooting** - Common issues and solutions:

```
.ai/knowledge/troubleshooting/
├── signature_mismatch.md   # "Signature invalid" errors
├── dimension_mismatch.md   # Vector dimension errors
├── permission_denied.md    # Capability token issues
├── thread_timeout.md       # Thread exceeded limits
├── registry_connection.md  # Can't connect to registry
├── mcp_discovery_failed.md # External MCP issues
└── model_unavailable.md    # LLM provider errors
```

---

## Demo Content (Registry - Not Core RYE)

Demos ship to registry under `core/demos/` namespace, not bundled in rye-lilux:

### Level 1: Primary (Basic MCP Usage)

```
demos/level-1-primary/
├── 01_demo_create_sign.md      # Create and sign items
├── 02_demo_load_move.md        # Load and move between locations
├── 03_demo_search.md           # Search all item types
├── 04_demo_primitives.md       # Execute tools with primitives
├── 05_demo_other_mcps.md       # Integrate external MCPs
└── 06_demo_registry.md         # Registry operations
```

### Level 2: Harness (Threading & Safety)

```
demos/level-2-harness/
├── 01_demo_thread_directive.md # Thread your first directive
├── 02_demo_permissions.md      # Permission enforcement
├── 03_demo_limits.md           # Cost and resource limits
├── 04_demo_thread_tools.md     # Pause, resume, inject
└── 05_demo_hooks.md            # Error handling hooks
```

### Level 3: Orchestration (Advanced Patterns)

```
demos/level-3-orchestration/
├── 01_demo_parallel.md         # Parallel thread execution
├── 02_demo_recursion.md        # Recursive directive calls
├── 03_demo_tight_context.md    # Context window management
├── 04_demo_annealing.md        # Self-improvement from failure
├── 05_demo_knowledge_evolution.md  # Knowledge base growth
└── 06_demo_self_evolving.md    # Self-modifying directives
```

### Level 4: Autonomous (Research/Experimental)

```
demos/level-4-autonomous/
├── 01_demo_multi_agent.md      # Multi-agent coordination
├── 02_demo_state_branching.md  # Branching execution paths
├── 03_demo_proof_verification.md # Proof-carrying code
├── 04_demo_genome_evolution.md # Directive evolution
├── 05_demo_emergent_specialization.md # Agent specialization
└── 06_demo_self_governing.md   # Self-governing systems
```

**Install demos:**

```
User: "get the demos"
LLM: [calls execute(directive, "bundle_install", {bundle: "core/demos"})]
```

---

## Design Decisions: Threading

### No Raw `spawn_thread` Exposure

**Problem:** `spawn_thread.py` is a low-level tool with complex parameters.

**Solution:** The `thread_directive` directive wraps the complexity:

```xml
<!-- thread_directive.md - User-friendly entry point for threading -->
<directive name="thread_directive" version="1.0.0">
  <inputs>
    <input name="directive_name" required="true">Directive to run in fresh context</input>
    <input name="inputs" required="false">Directive inputs</input>
    <input name="wait" default="true">Wait for completion</input>
  </inputs>

  <process>
    <step name="execute">
      Uses thread_directive.py tool internally.
      Handles all the harness setup automatically.
      Returns clean result to user.
    </step>
  </process>
</directive>
```

**Users say:** "thread the lead_gen directive"  
**LLM calls:** `execute(directive, "thread_directive", {directive_name: "lead_gen"})`  
**Not:** Direct `spawn_thread` with complex params

### Thread Directive Tool (`thread_directive.py`)

This is the actual threading tool that:

- Creates SafetyHarness with limits
- Enforces permissions via CapabilityToken
- Tracks cost (tokens, turns, USD)
- Handles hooks for error recovery
- Returns clean results

The `thread_directive` directive wraps this for users.

---

## Excitement Features (What Gets Users Hooked)

### 1. Discovery Directives

```
User: "discover what models are available on together.ai"
LLM: [runs discover_llm directive with endpoint]
     → Auto-creates tool configs for all discovered models
     → Updates model tier config
     → "Found 47 models. Added to your tiers."
```

### 2. MCP Integration

```
User: "add the supabase mcp"
LLM: [runs add_mcp directive]
     → Discovers tools from Supabase MCP
     → Adds to config
     → "Supabase MCP added. 15 tools available."
```

### 3. Threading for Long Tasks

```
User: "run that research task in the background"
LLM: [runs run_in_thread directive]
     → Spawns fresh context
     → "Thread started. I'll notify you when done."
     → (Later) "Thread complete. Here's the summary..."
```

### 4. Parallel Execution

```
User: "analyze these 5 codebases in parallel"
LLM: [runs run_parallel directive]
     → Spawns 5 threads
     → Each with isolated context
     → Aggregates results
     → "All 5 analyses complete."
```

### 5. Self-Annealing

```
User: "that directive failed, improve it"
LLM: [runs anneal_directive]
     → Analyzes failure
     → Modifies directive
     → Re-signs
     → "Directive improved. Try again."
```

### 6. Knowledge Evolution

```
User: "remember this pattern for next time"
LLM: [creates knowledge entry]
     → Links to related knowledge
     → Indexes for search
     → "Stored. I'll use this pattern in future."
```

---

## Summary: What Ships in rye-lilux

### Bundled (in package):

| Category             | Items                                                                                                                                                                         | Count | Protection      |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | --------------- |
| **Core Tools**       | system, registry, rag, telemetry_lib, run_with_telemetry, configure_telemetry, telemetry_status, clear_telemetry, export_telemetry                                            | 9     | READONLY        |
| **Thread Tools**     | harness, thread_directive, thread_registry, spawn, inject, pause, resume, cancel, read_transcript, get_status, list, get_cost, expression_evaluator, anthropic/openai configs | 15    | User-extensible |
| **LLM Tools**        | anthropic, openai configs, pricing                                                                                                                                            | 3     | User-extensible |
| **MCP Tools**        | discover, call, configs                                                                                                                                                       | 4     | User-extensible |
| **Capability Tools** | fs, net, process, db, git, mcp                                                                                                                                                | 6     | READONLY        |
| **Core Directives**  | Primitives (21) + Setup (3) + Sync (5) + Publish (4) + Bundles (6) + Registry (3) + Keys (5) + Threading (12) + Discovery (4) + Annealing (2)                                 | ~65   | Shadowable      |

### Knowledge Base:

| Category            | Items                                                                                                                                                                                   | Count | Protection      |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | --------------- |
| **Kernel Docs**     | overview, primitives, search, load, execute, sign, help, item_types, command_table, project_path, error_handling                                                                        | 11    | READONLY        |
| **RYE Docs**        | overview, threading, harness, permissions, capabilities, hooks, limits, discovery, registry, signing, model_tiers, init                                                                 | 12    | READONLY        |
| **Concepts**        | doe_framework, everything_to_something, context_rot, deterministic_execution, self_annealing, subagent_isolation, mcp_ecosystem                                                         | 7     | User-extensible |
| **Patterns**        | orchestration (4), agent_design (4), verification (3), resource_management (3)                                                                                                          | 14    | User-extensible |
| **Procedures**      | first_directive, first_tool, first_knowledge, add_llm_provider, add_external_mcp, publish_to_registry, create_bundle, setup_rag, thread_long_task, debug_directive, anneal_from_failure | 11    | User-extensible |
| **Templates**       | directive (3), tool (2), knowledge (3), collection.toml                                                                                                                                 | 9     | User-extensible |
| **Troubleshooting** | signature_mismatch, dimension_mismatch, permission_denied, thread_timeout, registry_connection, mcp_discovery_failed, model_unavailable                                                 | 7     | User-extensible |

**Total Knowledge Entries: 71**

### Registry (downloadable):

| Category          | Items                     |
| ----------------- | ------------------------- |
| **Demos Level 1** | 6 primary tutorials       |
| **Demos Level 2** | 5 harness tutorials       |
| **Demos Level 3** | 6 orchestration tutorials |
| **Demos Level 4** | 6 autonomous experiments  |

**Total Demos: 23**

---

## Timeline

| Day | Phase | Deliverable                                   |
| --- | ----- | --------------------------------------------- |
| 1   | 0     | Monorepo setup, all renames                   |
| 2   | 1-2   | Help tool (+ AGENTS.md template), System tool |
| 3-4 | 3     | Registry tool + auth + keyring storage        |
| 5   | 4-5   | Protection, Dimension check                   |
| 6   | 6     | Init & Bootstrap (AGENTS.md injection)        |
| 7   | 7-8   | Registry backend setup, Model tiers           |
| 8   | 9     | Package & publish                             |

**Total: 8 days to v0.1.0**

---

_Document Status: Ship Planning v11_  
_Last Updated: 2026-01-30_  
_Current: Phase 5 - Dimension Mismatch Check (next)_  
_Note: Phase 3 complete with registry tool (12 actions), device auth flow (3 edge functions), and "dumb kernel" restructuring (primitives/runtimes/capabilities moved to rye/.ai/tools/)._
