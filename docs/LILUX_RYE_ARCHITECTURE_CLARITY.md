# Lilux/RYE Architecture: Repository & Packaging Clarity

**Date:** 2026-01-29  
**Status:** Aligned with Ship Roadmap  
**Purpose:** Clear explanation of how lilux kernel and rye content are organized and shipped

---

## Critical Clarification: Lilux is an MCP, NOT a CLI

Lilux exposes MCP tools. Users interact through an LLM that calls these tools:

```
WRONG (CLI thinking):
$ lilux search "my-directive"

CORRECT (MCP via LLM):
User: "search for lead generation directives"
LLM: [calls mcp__lilux__search(item_type="directive", query="lead generation")]
```

There is no CLI. The MCP server starts via `python -m lilux.server` and communicates over stdio.

---

## Monorepo Structure

**Single repository for development simplicity:**

```
github.com/leolilley/lilux-rye/
├── lilux/                          # Kernel package (pip install lilux)
│   ├── __init__.py
│   ├── server.py                   # MCP server
│   ├── tools/                      # 5 primitive tools
│   │   ├── search.py               # Find items
│   │   ├── load.py                 # Get/copy items
│   │   ├── execute.py              # Run items
│   │   ├── sign.py                 # Validate & sign
│   │   └── help.py                 # Kernel manual + command table
│   ├── primitives/                 # Low-level execution
│   │   ├── http_client.py          # HTTP requests
│   │   └── subprocess.py           # Shell execution
│   ├── handlers/                   # Item type handlers
│   │   ├── directive/              # Parse & return directive data
│   │   ├── tool/                   # Parse & return tool data
│   │   └── knowledge/              # Parse & return knowledge data
│   ├── storage/
│   │   └── vector/                 # Vector store (uses env config)
│   └── utils/
│
├── rye/                            # Content package (pip install rye-lilux)
│   ├── __init__.py
│   └── .ai/                        # RYE content bundle
│       ├── directives/
│       │   └── core/               # Can be shadowed by user
│       ├── tools/
│       │   ├── core/               # PROTECTED - cannot override
│       │   ├── llm/                # LLM configs
│       │   └── threads/            # Threading tools
│       └── knowledge/
│           └── kernel/             # PROTECTED - cannot override
│
├── tests/                          # Tests for both
├── pyproject.toml                  # Monorepo config
└── README.md
```

---

## Two PyPI Packages

### Package 1: `lilux` (Kernel)

**Contains ONLY primitives:**

- MCP server infrastructure
- 5 unified MCP tools: search, load, execute, sign, help
- Handlers for directives/tools/knowledge
- Vector store infrastructure
- No content included (just infrastructure)

**Install:** `pip install lilux`

### Package 2: `rye-lilux` (Content Bundle)

Like "Arch Linux" - RYE running on Lilux.

**Contains all intelligence:**

- Core directives (init, bootstrap, sync, etc.)
- Core tools (system, registry, rag, threads, etc.)
- Core knowledge base
- Depends on `lilux>=0.1.0`

**Install:** `pip install rye-lilux` (gets both lilux kernel + rye content)

---

## Package Dependency

### `rye-lilux` Depends on `lilux`

**`rye/pyproject.toml`:**

```toml
[project]
name = "rye-lilux"
version = "0.1.0"
description = "RYE content layer for Lilux MCP"

dependencies = [
    "lilux>=0.1.0",        # ← Depends on kernel
    "pydantic>=2.0",
    "pyyaml>=6.0",
]

[tool.setuptools.package-data]
"" = [".ai/**/*"]          # Bundle the .ai/ folder
```

### What Happens When You `pip install rye-lilux`

```
$ pip install rye-lilux

1. Fetch 'rye-lilux' package from PyPI
2. Dependencies:
   └── lilux>=0.1.0

3. Install lilux package (first)
   ├── Installs site-packages/lilux/
   │   ├── server.py
   │   ├── tools/
   │   ├── primitives/
   │   ├── handlers/
   │   └── (all kernel code)
   └── Entry point: python -m lilux.server

4. Install rye-lilux package (second)
   ├── Installs site-packages/rye/
   │   ├── __init__.py
   │   └── .ai/                ← Content bundle
   │       ├── directives/
   │       ├── tools/
   │       └── knowledge/

5. Result: Full system available via MCP
```

---

## How `lilux` Finds the `.ai/` Content

**In `lilux/config.py`:**

```python
from pathlib import Path

def get_content_root():
    """Get path to bundled .ai/ content from rye package"""
    try:
        import rye
        rye_path = Path(rye.__file__).parent
        ai_path = rye_path / ".ai"
        if ai_path.exists():
            return ai_path
    except ImportError:
        pass

    # Fallback: no content available (kernel-only install)
    return None

CONTENT_ROOT = get_content_root()
```

---

## User Spaces

The userspace location is configurable via the `USER_PATH` environment variable. Default is `~/.ai/`.

When a user runs the `init` directive, it creates:

### User Space ($USER_PATH)

Everything lives in one location - content, config, and cache:

```
$USER_PATH/                         # Default: ~/.ai/
├── directives/                     # User's custom directives
├── tools/                          # User's custom tools
├── knowledge/                      # User's knowledge entries
├── keys/
│   └── trusted/*.pub               # Trusted author public keys
├── cache/
│   └── vectors/                    # Pre-computed embeddings
├── config.yaml                     # User settings (telemetry, etc.)
├── telemetry.yaml                  # Execution stats (v0.2.0)
├── .env                            # CI secrets (fallback)
└── AGENTS.md                       # Command dispatch table
```

Single location for everything. Simpler mental model than XDG split.

### Secrets (System Keyring)

Secrets stored in system keyring (not filesystem):

- Registry session token → `keyring.set_password("rye", "registry-token", ...)`
- Private signing key → `keyring.set_password("rye", "signing-key", ...)`

Uses macOS Keychain, Windows Credential Manager, or Linux Secret Service via Python `keyring` library.

### Kernel vs RYE Responsibilities

| Data          | Location              | Managed By       |
| ------------- | --------------------- | ---------------- |
| All user data | `$USER_PATH` (~/.ai/) | User + RYE tools |
| Secrets       | System keyring        | RYE tools        |

Kernel knows about `$USER_PATH`. RYE tools manage keys, cache, and config within it.

Project-level content goes in `.ai/` within the project directory.

---

## Registry Authentication

Registry operations (publish, sync from private items) require authentication. The auth flow works like the Supabase CLI - browser-based, no custom UI needed.

### Auth Flow (Device Authorization Pattern)

```
User: "login to registry"
LLM: [calls mcp__lilux__execute(item_type="tool", item_id="core/registry",
      parameters={"action": "login"})]

1. Registry tool generates:
   - Random session ID (UUID)
   - ECDH keypair (P-256)
   - Token name: "{username}@{machine}-{timestamp}"

2. Opens browser to:
   https://registry.lilux.dev/auth?session_id=xxx&public_key=yyy&token_name=zzz

3. User authenticates via Supabase Auth (existing dashboard):
   - Sign up with email/password, magic link, or OAuth (GitHub, Google)
   - Existing users just log in

4. Server encrypts access token:
   - Generates server ECDH keypair
   - Computes shared secret via ECDH
   - Encrypts token, stores in DB with session ID

5. Registry tool polls for completion:
   - Fetches encrypted token by session ID
   - Decrypts using local private key
   - Stores in system keyring (key: `lilux-registry-token`)

6. Done - user is logged in
```

### Auth Tool Actions

```python
# .ai/tools/core/registry.py

ACTIONS = {
    # Authentication
    "login": "Authenticate with registry (opens browser)",
    "logout": "Clear local auth session",
    "whoami": "Show current authenticated user",

    # Registry operations (require auth)
    "sync": "Download/update items from registry",
    "publish": "Upload signed items to registry",

    # Key management (require auth)
    "keys_generate": "Generate new signing keypair",
    "keys_list": "List trusted public keys",
    "keys_trust": "Add a public key to trusted list",
    "keys_revoke": "Remove a public key from trusted list",
}
```

### User Experience

```
User: "login to registry"
LLM: "Opening browser for authentication..."
     [browser opens to registry.lilux.dev/auth]
     [user logs in or signs up]
LLM: "Authenticated as leo@github. You can now publish and sync."

User: "publish my-directive to registry"
LLM: [calls registry tool with action="publish"]
     "Published my-directive v1.0.0 to registry under leo/my-directive"

User: "who am I logged in as?"
LLM: [calls registry tool with action="whoami"]
     "leo@github (authenticated since 2026-01-29)"
```

### No UI Required

- **Signup/Login**: Uses existing Supabase Auth dashboard UI
- **No custom frontend**: Just a simple redirect page at `registry.lilux.dev/auth`
- **Same pattern as**: `gh auth login`, `supabase login`, `vercel login`

### Secure Credential Storage

**Primary: System Keyring** (via Python `keyring` library)

| Secret              | Keyring Service | Keyring Key      |
| ------------------- | --------------- | ---------------- |
| Registry token      | `rye`           | `registry-token` |
| Private signing key | `rye`           | `signing-key`    |

Works with:

- macOS Keychain
- Windows Credential Manager
- Linux Secret Service (GNOME Keyring, KWallet)

**Fallback: .env file** (for CI/headless)

```bash
# ~/.ai/.env (or project .env)
REGISTRY_TOKEN=sb-xxx...
SIGNING_KEY=base64-encoded-pem...
# or
SIGNING_KEY_FILE=/path/to/private.pem
```

**Never stored as plaintext outside .env.** RYE tools check:

1. System keyring first (for interactive)
2. .env file second (for CI)
3. Error if neither available

---

## MCP Configuration

Users configure their LLM client to connect to Lilux:

**Claude Desktop / Cursor config:**

```json
{
  "mcpServers": {
    "lilux": {
      "command": "python",
      "args": ["-m", "lilux.server"],
      "env": {
        "EMBEDDING_URL": "https://api.openai.com/v1/embeddings",
        "EMBEDDING_API_KEY": "sk-...",
        "VECTOR_DB_URL": "sqlite:///~/.local/share/lilux/vectors.db"
      }
    }
  }
}
```

---

## Version Compatibility

### Independent Versioning

- **lilux 0.1.0**: Kernel stability, API contracts
- **rye-lilux 0.1.0**: Content stability, directive/tool versions

### Compatibility Matrix

```
rye-lilux 0.1.0 requires lilux >=0.1.0
rye-lilux 0.2.0 requires lilux >=0.1.0
rye-lilux 1.0.0 requires lilux >=0.2.0

lilux 0.2.0 compatible with rye-lilux >=0.1.0
lilux 1.0.0 not compatible with rye-lilux <1.0.0
```

### Release Cycle

- **lilux**: Slower releases (kernel stability)
- **rye-lilux**: Faster releases (content improvements)
- **Coordinated releases**: Only when breaking changes

---

## Development & Contribution

### Working in the Monorepo

```bash
git clone github.com/leolilley/lilux-rye
cd lilux-rye
pip install -e .
# Both lilux/ and rye/ are editable
pytest
```

### Testing

```bash
# Test kernel
pytest tests/kernel/

# Test content
pytest tests/content/

# Integration tests
pytest tests/integration/
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
│  │ PROTECTED (readonly - all core tools):                      │ │
│  │   .ai/tools/core/system.py    ← env vars, paths, rag       │ │
│  │   .ai/tools/core/registry.py  ← auth, sync, publish, keys  │ │
│  │   .ai/tools/core/rag.py       ← vector search              │ │
│  │   .ai/tools/core/llm/*        ← LLM provider configs       │ │
│  │   .ai/tools/core/threads/*    ← threading infrastructure   │ │
│  │   .ai/knowledge/kernel/*      ← kernel documentation       │ │
│  │                                                              │ │
│  │ SHADOWABLE (user can override):                             │ │
│  │   .ai/directives/core/*       ← init, bootstrap, sync      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      USER SPACES                                  │
│                                                                   │
│  User Space ($USER_PATH, default ~/.ai/):                         │
│  ├── directives/               ← user's custom directives        │
│  ├── tools/                    ← user's custom tools             │
│  ├── knowledge/                ← user's knowledge entries        │
│  ├── keys/trusted/*.pub        ← trusted author public keys      │
│  ├── cache/vectors/            ← embeddings cache                │
│  ├── config.yaml               ← user settings                   │
│  └── AGENTS.md                 ← command dispatch table          │
│                                                                   │
│  System Keyring (secrets - not on filesystem):                   │
│  └── rye/registry-token, rye/signing-key                         │
│                                                                   │
│  Project (.ai/):                                                  │
│  ├── directives/               ← project-specific directives     │
│  ├── tools/                    ← project-specific tools          │
│  └── knowledge/                ← project-specific knowledge      │
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

## Summary

| Aspect            | Lilux                        | RYE                                                |
| ----------------- | ---------------------------- | -------------------------------------------------- |
| **What**          | Kernel (execution engine)    | Content (directives, tools, knowledge)             |
| **Repository**    | Monorepo: `lilux-rye/lilux/` | Monorepo: `lilux-rye/rye/`                         |
| **PyPI Package**  | `lilux`                      | `rye-lilux`                                        |
| **Dependency**    | None (standalone)            | Depends on `lilux>=0.1.0`                          |
| **Versioning**    | Kernel semver                | Content semver                                     |
| **Release Cycle** | Stable, infrequent           | Dynamic, frequent                                  |
| **User Install**  | `pip install lilux`          | `pip install rye-lilux` (gets both)                |
| **Interaction**   | MCP tools via LLM            | MCP tools via LLM                                  |
| **Content**       | None                         | `.ai/` folder with core directives/tools/knowledge |

**Bottom line:**

- User installs: `pip install rye-lilux`
- Gets: lilux kernel + rye content
- Interacts via LLM → MCP tools (no CLI)
- Both work together seamlessly

---

_Document Status: Aligned with Ship Roadmap_  
_Last Updated: 2026-01-29_
