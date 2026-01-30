**Source:** Original implementation: `kiwi_mcp/` package structure in kiwi-mcp

# Lilux Package Structure

## Overview

The Lilux microkernel is organized into 9 core directories, each serving a specific role in the execution pipeline:

```
lilux/
├── primitives/          # Execution primitives (dumb executors)
├── runtime/             # Runtime services (auth, env, locks)
├── handlers/            # Dumb routing (no content intelligence)
├── schemas/             # JSON Schema definitions
├── config/              # Configuration objects
├── storage/             # Vector storage and RAG
├── tools/               # Legacy MCP tools (deprecated)
├── utils/               # Minimal utilities
├── safety_harness/      # Execution safety and capabilities
└── telemetry/           # Observability and logging
```

## Directory Details

### 1. Primitives (`lilux/primitives/`)

**Purpose:** Core execution primitives that provide generic execution capabilities.

**Key Files:**
- **`executor.py`** - Base executor framework for all primitives
- **`subprocess.py`** - Execute shell commands in isolated environments
- **`http_client.py`** - Make HTTP requests with retry logic, authentication, and cert handling
- **`lockfile.py`** - Manage file-based locks for concurrency control
- **`chain_validator.py`** - Validate execution chains and dependencies
- **`integrity.py`** - Hash and integrity verification
- **`integrity_verifier.py`** - Verification implementation details

**Architecture Role:**
Primitives are the **core microkernel layer**. Each primitive:
- Extends `BaseExecutor`
- Has `__executor_id__ = None` (no content routing)
- Defines a `CONFIG_SCHEMA` for configuration
- Implements `execute()` method

**RYE Relationship:**
RYE's universal executor calls primitives directly. See `[[rye/categories/primitives]]` for how RYE schemas map to these primitives.

### 2. Runtime Services (`lilux/runtime/`)

**Purpose:** Shared services that primitives and executors depend on.

**Key Files:**
- **`auth_store.py`** - Keychain integration for credential management
- **`env_resolver.py`** - Template variable resolution (ENV_CONFIG handling)
- **`lockfile_store.py`** - Concurrency lock management

**Architecture Role:**
Runtime services provide **infrastructure for safe execution**:
- `AuthStore`: Secure credential storage and retrieval
- `EnvResolver`: Variable templating for configuration
- `LockfileStore`: Prevent concurrent conflicts

**RYE Relationship:**
RYE's universal executor uses these services when executing tools. See `[[rye/categories/runtimes]]` for ENV_CONFIG patterns.

### 3. Handlers (`lilux/handlers/`)

**Purpose:** Dumb routing based on file paths and types (no content intelligence).

**Key Files:**
- **`directive_handler.py`** - Route directive files
- **`tool_handler.py`** - Route tool files
- **`knowledge_handler.py`** - Route knowledge files

**Architecture Role:**
Handlers are **stateless routers**:
- Receive file paths
- Return handler for that path
- **NO parsing or understanding** of content
- Just file system navigation

**RYE Relationship:**
RYE's content handlers provide the **intelligent routing**. Lilux handlers are fallback path-based routing. See `[[rye/content-handlers/overview]]`.

### 4. Schemas (`lilux/schemas/`)

**Purpose:** JSON Schema definitions for tool configuration and validation.

**Key Files:**
- **`tool_schema.py`** - JSON Schema for tools (parameters, inputs, outputs)
- Other schema helpers

**Architecture Role:**
Schemas define the **shape of configuration data**:
- What parameters a tool accepts
- What types and constraints
- Used for validation before execution

**RYE Relationship:**
RYE uses schemas to validate tool calls and generate schemas for the MCP interface. See `[[rye/categories/primitives]]`.

### 5. Config (`lilux/config/`)

**Purpose:** Configuration objects for search and vector storage.

**Key Files:**
- **`search_config.py`** - Configuration for search/RAG functionality
- **`vector_config.py`** - Configuration for vector embeddings

**Architecture Role:**
Config objects support **optional RAG features**:
- Vector search setup
- Embedding configuration
- Search index parameters

**RYE Relationship:**
RYE uses these for knowledge base search and tool discovery. See `[[rye/universal-executor/overview]]`.

### 6. Storage (`lilux/storage/`)

**Purpose:** Vector storage and RAG support.

**Key Files:**
- **`vector/`** - Vector database integration
  - Embedding support
  - Similarity search
  - Knowledge base indexing

**Architecture Role:**
Storage provides **optional retrieval-augmented generation**:
- Index knowledge entries
- Search by similarity
- Support context expansion

**RYE Relationship:**
RYE's universal executor uses storage for knowledge-enhanced execution.

### 7. Tools (`lilux/tools/`) - **LEGACY**

**Purpose:** Legacy MCP tool implementations (deprecated).

⚠️ **Status:** LEGACY - Do NOT use for new implementations

**Key Files:**
- **`base.py`** - Old tool base class
- **`mcp_tools.py`** - Legacy MCP tool adapters

**Migration:** Use RYE's MCP server instead. See `[[rye/mcp-server]]`.

### 8. Utils (`lilux/utils/`)

**Purpose:** Minimal utility functions (no content intelligence).

**Key Files:**
- **`resolver.py`** - Path resolution helpers
- **`logger.py`** - Logging utilities
- **`extensions.py`** - Minimal extensions support

**Architecture Role:**
Utils are **minimal only**:
- No parsing or content understanding
- No schema validation
- No configuration loading
- Just basic helpers

**Contrast with RYE:**
RYE has rich utils for content handling. See `[[rye/content-handlers/overview]]`.

### 9. Safety Harness (`lilux/safety_harness/`)

**Purpose:** Execution safety and capability management.

**Key Files:**
- **`capabilities.py`** - Define allowed capabilities for execution
- Safety sandboxing

**Architecture Role:**
Safety harness ensures **controlled execution**:
- Define what primitives can do
- Prevent unauthorized operations
- Audit execution

### 10. Telemetry (`lilux/telemetry/`)

**Purpose:** Observability, metrics, and logging.

**Key Files:**
- Logging infrastructure
- Metrics collection
- Trace support

**Architecture Role:**
Telemetry provides **visibility into execution**:
- Log all operations
- Measure performance
- Track errors

## Design Principles

### 1. **Dumb Microkernel**
Each component in Lilux is intentionally simple:
- Subprocess just runs commands
- HTTP client just makes requests
- Handlers just route files
- **No intelligence**

### 2. **Clear Separation**
- Lilux = execution primitives
- RYE = content understanding
- No overlap, no duplication

### 3. **Library-First**
Lilux is installable as a library:
```bash
pip install lilux
```
Not a standalone application—used by RYE and other systems.

### 4. **Security-First**
- Credentials stored securely (keychain)
- Locks prevent concurrent conflicts
- Safety harness limits capabilities
- Integrity verification supported

## Dependencies

```
lilux/
├── No external dependencies for core primitives
├── Optional: vector storage (numpy, sklearn, etc.)
└── Optional: keychain integration (keyring)
```

## Cross-References

- **RYE Universal Executor:** `[[rye/universal-executor/overview]]`
- **RYE Primitive Schemas:** `[[rye/categories/primitives]]`
- **RYE Content Handlers:** `[[rye/content-handlers/overview]]`
- **RYE Runtime Schemas:** `[[rye/categories/runtimes]]`
