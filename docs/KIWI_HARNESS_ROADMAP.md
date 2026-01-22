# Kiwi Agent Harness: Implementation Roadmap

**Date:** 2026-01-21  
**Status:** Approved  
**Author:** Kiwi Team

---

## Vision

Transform Kiwi MCP from a directive/script/knowledge manager into a **full agent harness** that:

1. **Scripts → Tools**: Multi-executor tool system (Python, Bash, API, MCP)
2. **MCP Orchestration**: Directives declare and route to external MCPs
3. **Agent Spawning**: Directives execute in purpose-built, isolated executors
4. **Full Control**: All tool calls proxied through Kiwi for audit, permissions, rate limiting

**End State**: Agents only talk to Kiwi. Kiwi controls everything else.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         KIWI AGENT HARNESS                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                         Meta-Tools                              │ │
│  │      search   │   load   │   execute   │   help                │ │
│  └───────┬───────┴────┬─────┴──────┬──────┴───────────────────────┘ │
│          │            │            │                                 │
│  ┌───────▼────────────▼────────────▼───────────────────────────────┐│
│  │                    Type Handler Registry                         ││
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────┐  ││
│  │  │Directive │  │  Tool    │  │ Knowledge │  │ MCP (virtual)  │  ││
│  │  │ Handler  │  │ Handler  │  │  Handler  │  │   Handler      │  ││
│  │  └────┬─────┘  └────┬─────┘  └───────────┘  └───────┬────────┘  ││
│  │       │             │                               │            ││
│  │       │     ┌───────▼────────┐                      │            ││
│  │       │     │ Executor       │                      │            ││
│  │       │     │ Registry       │                      │            ││
│  │       │     │ ┌────────────┐ │                      │            ││
│  │       │     │ │ Python     │ │                      │            ││
│  │       │     │ │ Bash       │ │                      │            ││
│  │       │     │ │ API        │ │                      │            ││
│  │       │     │ │ Docker     │ │                      │            ││
│  │       │     │ └────────────┘ │                      │            ││
│  │       │     └────────────────┘                      │            ││
│  └───────┼─────────────────────────────────────────────┼────────────┘│
│          │                                             │             │
│  ┌───────▼─────────────────────────────────────────────▼───────────┐│
│  │                     Directive Runtime                            ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  ││
│  │  │  Executor   │  │   Kiwi      │  │    MCP Client           │  ││
│  │  │  Builder    │  │   Proxy     │  │    Pool                 │  ││
│  │  └─────────────┘  └──────┬──────┘  └───────────┬─────────────┘  ││
│  │                          │                     │                 ││
│  │  ┌───────────────────────▼─────────────────────▼───────────────┐││
│  │  │                    Audit & Permission Layer                  │││
│  │  │  • Permission enforcement    • Rate limiting                 │││
│  │  │  • Audit logging             • Checkpoint management         │││
│  │  └──────────────────────────────────────────────────────────────┘││
│  └──────────────────────────────────────────────────────────────────┘│
│                                    │                                 │
└────────────────────────────────────┼─────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
    ┌───────────┐            ┌───────────────┐          ┌───────────────┐
    │ Filesystem│            │ External MCPs │          │ Shell/Git     │
    │ (proxied) │            │ (supabase,    │          │ (proxied)     │
    │           │            │  github, etc) │          │               │
    └───────────┘            └───────────────┘          └───────────────┘
```

---

## Phase 0: Current State Baseline

**What exists today:**

- ✅ 4 meta-tools: search, load, execute, help
- ✅ 3 item types: directive, script, knowledge
- ✅ TypeHandlerRegistry for routing
- ✅ ValidationManager for content validation
- ✅ MetadataManager for signatures
- ✅ Permission enforcement on directives
- ✅ Python script execution with venv isolation

**What's missing:**

- ❌ Multi-executor tools (bash, API, etc.)
- ❌ MCP routing/proxy
- ❌ Directive executor spawning
- ❌ Unified audit layer
- ❌ `<tools>` tag support

---

## Phase 1: Tool Foundation (Weeks 1-2)

**Goal:** Rename scripts to tools, add executor abstraction without breaking existing functionality.

### Deliverables

1. **ToolManifest dataclass** (`kiwi_mcp/handlers/tool/manifest.py`)

   ```python
   @dataclass
   class ToolManifest:
       tool_id: str
       tool_type: str  # python | bash | api | docker | mcp
       version: str
       description: str
       executor_config: dict
       parameters: list[dict]
       mutates_state: bool = False
   ```

2. **ToolHandler** (rename from ScriptHandler)

   - Keep all existing script logic
   - Add `tool_type` field detection
   - Route to executor based on type

3. **PythonExecutor** (extract from current handler)

   - Current venv logic
   - Current output management
   - Current lib imports

4. **Backward compatibility**
   - `item_type="script"` aliases to `item_type="tool"`
   - Legacy `.py` files work without manifest
   - Virtual manifest generation for legacy scripts

### Files Changed/Created

```
kiwi_mcp/handlers/
├── registry.py          # Add "tool" type, alias "script"
└── tool/                # Renamed from script/
    ├── __init__.py
    ├── handler.py       # Renamed ScriptHandler → ToolHandler
    ├── manifest.py      # NEW: ToolManifest dataclass
    └── executors/       # NEW: Executor framework
        ├── __init__.py  # ExecutorRegistry
        ├── base.py      # ToolExecutor ABC
        └── python.py    # PythonExecutor (extracted)
```

### Success Criteria

- [ ] All existing tests pass
- [ ] `execute(item_type="script", ...)` still works
- [ ] `execute(item_type="tool", ...)` works identically
- [ ] New tool with `tool.yaml` manifest can be created and run

### Effort: 5 days

---

## Phase 2: Bash & API Executors (Weeks 3-4)

**Goal:** Add bash and API tool types, proving the multi-executor pattern.

### Deliverables

1. **BashExecutor**

   ```python
   class BashExecutor(ToolExecutor):
       async def execute(self, manifest: ToolManifest, params: dict):
           # Validate allowed commands
           # Inject parameters as environment
           # Run with timeout
           # Capture output
   ```

2. **APIExecutor**

   ```python
   class APIExecutor(ToolExecutor):
       async def execute(self, manifest: ToolManifest, params: dict):
           # Build request from manifest config
           # Handle auth (bearer, api key, etc.)
           # Make HTTP request
           # Parse response
   ```

3. **Tool manifest examples**

   ```yaml
   # .ai/scripts/deployment/deploy_staging/tool.yaml
   tool_id: deploy_staging
   tool_type: bash
   executor:
     entrypoint: deploy.sh
     requires:
       commands: [kubectl, docker]
       environment: [KUBECONFIG]
   ```

4. **Validation updates**
   - BashValidator: Check shebang, syntax
   - APIValidator: Check endpoint, auth config

### Files Changed/Created

```
kiwi_mcp/handlers/tool/executors/
├── bash.py      # NEW: BashExecutor
└── api.py       # NEW: APIExecutor

kiwi_mcp/utils/validators.py  # Add BashValidator, APIValidator
```

### Success Criteria

- [ ] Bash script tool runs with parameter injection
- [ ] API tool makes authenticated request
- [ ] Tools with missing requirements fail gracefully
- [ ] Unit tests for both executors

### Effort: 5 days

---

## Phase 3: Kiwi Proxy Layer & Permission Enforcement (Weeks 5-7)

**Goal:** Route all tool calls through a proxy that enforces permissions, logs actions, and provides agent control signals.

**Design Document:** [RUNTIME_PERMISSION_DESIGN.md](./RUNTIME_PERMISSION_DESIGN.md)

### Core Concept: Runtime Permission Enforcement

Permissions declared in directives are **hard-enforced** at the proxy layer, not just "suggested" to the LLM:

```
Agent Request → KiwiProxy → Permission Check → IF allowed → Execute
                                             │
                                             └─ IF denied → Error + Optional Annealing
```

This prevents:
- Subagents escalating privileges beyond parent's scope
- Model hallucinations causing unauthorized actions
- Recursive agents going rogue

### Deliverables

1. **KiwiProxy class** with permission enforcement

   ```python
   class KiwiProxy:
       def __init__(self, permission_context: PermissionContext):
           self.permissions = permission_context  # From directive <permissions>
           self.audit = AuditLogger()
       
       async def call_tool(self, tool_id: str, params: dict) -> Any:
           # 1. Audit log (always, even for denied)
           self.audit.log_request(tool_id, params)
           
           # 2. Permission check (hard enforcement)
           if not self._check_permission(tool_id, params):
               return self._deny(tool_id, params)
           
           # 3. Rate limit check
           if not self._check_rate_limit(tool_id):
               return self._rate_limited(tool_id)
           
           # 4. Route to executor
           result = await self.executor_registry.execute(tool_id, params)
           
           # 5. Log result
           self.audit.log_result(tool_id, result)
           
           return result
   ```

2. **PermissionContext** from directive parsing

   ```python
   @dataclass
   class PermissionContext:
       filesystem_read: list[str]   # Glob patterns: ["src/**", "tests/**"]
       filesystem_write: list[str]  # Glob patterns: ["tests/**"]
       tools_allowed: list[str]     # Tool IDs: ["pytest", "search"]
       shell_commands: list[str]    # Commands: ["git", "npm"]
       mcp_actions: dict[str, list[str]]  # {"supabase": ["query", "migrate"]}
       
       def can_read(self, path: str) -> bool:
           return any(fnmatch(path, pat) for pat in self.filesystem_read)
       
       def can_execute(self, tool_id: str) -> bool:
           return tool_id in self.tools_allowed
   ```

3. **Help Tool Redesign: "Call for Help" Signal**

   The help tool is extended to serve as an **agent control signal**:
   
   ```python
   class HelpTool(BaseTool):
       # Existing: Get guidance
       # NEW: Signal for human attention
       
       async def execute(self, arguments: dict) -> str:
           action = arguments.get("action", "guidance")
           
           if action == "stuck":
               # Agent signals it's caught in a loop or confused
               return await self._signal_stuck(arguments)
           elif action == "escalate":
               # Agent needs human decision
               return await self._signal_escalate(arguments)
           elif action == "checkpoint":
               # Agent wants to save state before risky operation
               return await self._request_checkpoint(arguments)
           else:
               # Original guidance behavior
               return self._get_guidance(arguments.get("topic"))
       
       async def _signal_stuck(self, arguments: dict) -> str:
           """Signal that agent is stuck and needs intervention."""
           session_id = arguments.get("session_id")
           reason = arguments.get("reason", "Unknown")
           attempts = arguments.get("attempts", 0)
           
           # Log to monitoring system
           await self.monitor.signal_stuck(
               session_id=session_id,
               reason=reason,
               attempts=attempts,
               context=arguments.get("context")
           )
           
           # Trigger annealing review if configured
           if attempts > 3:
               await self.annealing.queue_for_review(session_id)
           
           return {
               "status": "stuck_acknowledged",
               "action": "awaiting_intervention",
               "session_id": session_id
           }
   ```

4. **FilesystemExecutor** with path enforcement

   - `filesystem.read`, `filesystem.write`, `filesystem.list`
   - Path validation against `permission_context.filesystem_read/write`

5. **ShellExecutor** with command allowlist

   - `shell.run` validates against `permission_context.shell_commands`
   - Timeout and output capture

6. **Audit logging**

   - `.ai/logs/audit/{date}/{session}.jsonl`
   - Every tool call: request, permission check result, execution result, timing
   - Denial reasons logged for annealing analysis

7. **Loop Detection & Stuck Signaling**

   ```python
   class LoopDetector:
       """Detects when agents are stuck in repetitive patterns."""
       
       def __init__(self, window_size: int = 10, similarity_threshold: float = 0.9):
           self.recent_calls: list[dict] = []
           self.window = window_size
           self.threshold = similarity_threshold
       
       def record_call(self, tool_id: str, params: dict) -> Optional[StuckSignal]:
           self.recent_calls.append({"tool": tool_id, "params": params})
           if len(self.recent_calls) > self.window:
               self.recent_calls.pop(0)
           
           # Check for repetitive patterns
           if self._detect_loop():
               return StuckSignal(
                   reason="repetitive_calls",
                   pattern=self._extract_pattern(),
                   suggestion="Consider using help(action='stuck') to signal for intervention"
               )
           return None
   ```

### Permission Inheritance in Recursion

When a directive spawns a subagent, permissions are **scoped down, never up**:

```python
def spawn_subagent(self, child_directive: str, inputs: dict):
    child_permissions = self._load_child_permissions(child_directive)
    
    # Intersection: child can only have what parent has AND what child declares
    scoped_permissions = self.permissions.intersect(child_permissions)
    
    # Verify no escalation
    if child_permissions.exceeds(self.permissions):
        return {"error": "Permission escalation denied"}
    
    return Executor(permissions=scoped_permissions, ...)
```

### Files Changed/Created

```
kiwi_mcp/
├── runtime/             # NEW directory
│   ├── __init__.py
│   ├── proxy.py         # KiwiProxy with permission enforcement
│   ├── permissions.py   # PermissionContext, PermissionChecker
│   ├── audit.py         # AuditLogger
│   └── loop_detector.py # LoopDetector for stuck detection
├── tools/
│   └── help.py          # Extended with call-for-help signals
└── handlers/tool/executors/
    ├── filesystem.py    # FilesystemExecutor with path checks
    └── shell.py         # ShellExecutor with command allowlist
```

### Success Criteria

- [ ] All tool calls logged to audit file
- [ ] Permission denied when tool not in directive scope
- [ ] Filesystem paths enforced via glob matching
- [ ] Shell commands filtered against allowlist
- [ ] Subagents cannot exceed parent permissions
- [ ] `help(action="stuck")` signals for intervention
- [ ] Loop detection suggests help signal when stuck

### Effort: 8 days (increased from 6 due to help redesign)

---

## Phase 4: Git Checkpoint Integration (Weeks 8-9)

**Goal:** Audit trail via git commits for state-mutating operations at the proxy layer.

### Deliverables

1. **git_checkpoint directive**

   - Show diff
   - Generate commit message
   - Commit or rollback

2. **`mutates_state` handling**

   - Tool manifests declare mutation
   - Proxy layer recommends checkpoint after mutating tools
   - Integrated with permission enforcement

3. **Rollback support**

   - `execute(action="rollback", item_id="{session_id}")`
   - Revert to pre-execution state

4. **Git helper utilities**
   - `GitHelper.status()`, `GitHelper.commit()`, `GitHelper.reset()`
   - Integrated with AuditLogger for traceability

### Files Changed/Created

```
kiwi_mcp/handlers/git/
├── __init__.py
├── checkpoint.py    # GitCheckpoint helper
└── helper.py        # Git operations

kiwi_mcp/runtime/
└── git_integration.py  # Git proxy layer integration

.ai/directives/core/
└── git_checkpoint.md  # Checkpoint directive
```

### Success Criteria

- [ ] Mutating tool triggers checkpoint recommendation at proxy layer
- [ ] Checkpoint creates commit with directive reference and audit trail
- [ ] Rollback reverts changes and updates git history
- [ ] Git operations logged in audit trail
- [ ] Integration with permission enforcement working

### Effort: 6 days

---

## Phase 5: MCP Client Pool (Weeks 10-11)

**Goal:** Connect to external MCPs, fetch schemas, route calls.

### Deliverables

1. **MCPClientPool**

   ```python
   class MCPClientPool:
       async def get_tool_schemas(self, mcp_name: str) -> list[Tool]
       async def call_tool(self, mcp_name: str, tool_name: str, params: dict)
   ```

2. **MCP registry config**

   ```yaml
   # .ai/config/mcp_registry.yaml
   mcps:
     supabase:
       type: stdio
       command: npx
       args: ["-y", "@supabase/mcp-server"]
       env:
         SUPABASE_ACCESS_TOKEN: ${SUPABASE_ACCESS_TOKEN}
   ```

3. **Schema caching**

   - TTL-based cache (1 hour default)
   - Force refresh option

4. **`<tools>` tag parsing**
   - Extract MCP declarations from directive
   - Validate required MCPs available

### Files Changed/Created

```
kiwi_mcp/
├── mcp/                 # NEW directory
│   ├── __init__.py
│   ├── client_pool.py   # MCPClientPool
│   ├── config.py        # MCP registry loader
│   └── schema_cache.py  # SchemaCache
└── utils/parsers.py     # Add <tools> parsing
```

### Success Criteria

- [ ] Connect to supabase MCP, fetch tool schemas
- [ ] Call supabase tool through Kiwi
- [ ] Schema caching works with TTL
- [ ] Directive with `<tools><mcp name="supabase">` loads schemas

### Effort: 6 days

---

## Phase 6: RAG & Vector Search (Weeks 12-14)

**Goal:** Implement vector database storage for directives, scripts, and knowledge to enable semantic search at scale (1M+ items).

**Design Document:** [RAG_VECTOR_SEARCH_DESIGN.md](./RAG_VECTOR_SEARCH_DESIGN.md)

### The Problem

Current keyword-based search doesn't scale:

- Registry could grow to millions of directives/scripts
- Keyword matching misses semantic intent
- Can't discover "similar" directives for reuse
- No learning from usage patterns

### The Solution: Validation-Gated Vector Storage

When items are **validated** (signature verified, structure checked), they're eligible for vector storage. This creates a security layer—only trusted content enters the vector DB.

```
┌────────────────────────────────────────────────────────────────────┐
│                      RAG Pipeline                                   │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  Validation  │───►│  Embedding   │───►│  Vector Storage      │  │
│  │  (existing)  │    │  Generation  │    │  (ChromaDB/Qdrant)   │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│         │                                          │               │
│         │                                          ▼               │
│         │                              ┌──────────────────────┐    │
│         │                              │  Semantic Search     │    │
│         │                              │  (replaces keyword)  │    │
│         │                              └──────────────────────┘    │
│         │                                                          │
│  Security: Only validated content is embedded                      │
└────────────────────────────────────────────────────────────────────┘
```

### Three-Tier Vector Storage

| Tier         | Location            | Content                            | Use Case                       |
| ------------ | ------------------- | ---------------------------------- | ------------------------------ |
| **Project**  | `.ai/vectors/`      | Local directives/scripts/knowledge | Project-specific search        |
| **User**     | `~/.ai/vectors/`    | User's shared items                | Cross-project personal library |
| **Registry** | Supabase + pgvector | Global published items             | Discovery across all users     |

### Deliverables

1. **VectorStore abstraction**

   ```python
   class VectorStore(ABC):
       async def embed_and_store(self, item_id: str, content: str, metadata: dict)
       async def search(self, query: str, limit: int, filters: dict) -> list[SearchResult]
       async def delete(self, item_id: str)

   class LocalVectorStore(VectorStore):
       """ChromaDB for project/user level"""

   class RegistryVectorStore(VectorStore):
       """pgvector via Supabase for registry"""
   ```

2. **Embedding pipeline**

   - Embed on validation success (hook into ValidationManager)
   - Use lightweight model (all-MiniLM-L6-v2 or similar)
   - Batch embedding for bulk imports
   - Incremental updates on edit

3. **Enhanced search handler**

   ```python
   async def search(self, query: str, source: str = "local"):
       # Semantic search with optional keyword fallback
       results = await self.vector_store.search(query, limit=20)
       # Merge with keyword results for hybrid approach
       return self._rank_hybrid(results, keyword_results)
   ```

4. **Validation-to-Vector hook**

   ```python
   # In ValidationManager
   async def validate(self, content: str, item_type: str):
       result = await self._validate_structure(content)
       if result.valid:
           # Security gate: only valid content gets embedded
           await self.vector_store.embed_and_store(
               item_id=result.item_id,
               content=self._extract_searchable(content),
               metadata={"type": item_type, "validated_at": now()}
           )
       return result
   ```

### Files Changed/Created

```
kiwi_mcp/storage/
├── __init__.py
├── vector/
│   ├── __init__.py
│   ├── base.py          # VectorStore ABC
│   ├── local.py         # ChromaDB implementation
│   ├── registry.py      # pgvector/Supabase implementation
│   └── embeddings.py    # Embedding model wrapper

kiwi_mcp/utils/
└── validation.py        # Add embed_on_validate hook

kiwi_mcp/handlers/
└── search.py            # Upgrade to hybrid search
```

### Success Criteria

- [ ] Validated directives automatically embedded
- [ ] Semantic search returns relevant results
- [ ] Three-tier storage (project/user/registry) working
- [ ] Hybrid search outperforms keyword-only
- [ ] Vector DB syncs with registry publishes

### Effort: 7 days

---

## Phase 7: Directive Executor Runtime (Weeks 15-17)

**Goal:** Spawn purpose-built executors for directives instead of returning content.

### Deliverables

1. **DirectiveExecutor**

   ```python
   class DirectiveExecutor:
       async def execute(self) -> dict:
           # LLM loop
           # Tool calls via proxy
           # Return result
   ```

2. **ExecutorBuilder**

   - Parse directive
   - Build tool manifest from `<tools>`
   - Create system prompt
   - Configure model from `<model tier>`

3. **Modified `_run_directive`**

   - Add `spawn_executor` mode (default for automation)
   - Keep legacy mode for interactive use

4. **Session management**

   - `.ai/sessions/{id}.json`
   - Status tracking
   - Cleanup policy

5. **Cost tracking**
   - Token counting per execution
   - Budget limits

### Files Changed/Created

```
kiwi_mcp/runtime/
├── executor.py      # DirectiveExecutor
├── builder.py       # ExecutorBuilder
├── session.py       # SessionManager
└── cost.py          # CostTracker

kiwi_mcp/handlers/directive/handler.py  # Modified _run_directive
```

### Success Criteria

- [ ] Directive spawns executor with only declared tools
- [ ] Executor completes directive and returns result
- [ ] Token usage tracked
- [ ] Session persisted and retrievable

### Effort: 8 days

---

## Phase 8: Annealing Integration (Weeks 18-19)

**Goal:** Auto-improve directives on failure.

### Deliverables

1. **Failure detection**

   - Analyze executor result
   - Classify annealable errors

2. **Annealing trigger**

   - Call `anneal_directive` on failure
   - Pass failure context and audit log

3. **Retry logic**

   - Reload improved directive
   - Retry once with updated version
   - Return both original and retry results

4. **Annealing metrics**
   - Track annealing frequency
   - Track success rate post-anneal

### Files Changed/Created

```
kiwi_mcp/runtime/
└── annealing.py     # AnnealingManager

.ai/directives/core/
└── anneal_directive.md  # Improve if needed
```

### Success Criteria

- [ ] Failed directive triggers annealing
- [ ] Improved directive retried successfully
- [ ] Annealing attempts logged

### Effort: 4 days

---

## Phase 9: Human Approval (Weeks 20-21)

**Goal:** Pause execution for human approval on sensitive operations.

### Deliverables

1. **Checkpoint persistence**

   - Save executor state to file
   - Resume from checkpoint

2. **Approval flow**

   - `require_approval` tools pause execution
   - Notification system (webhook/CLI)
   - `kiwi approve {session_id}` command

3. **Timeout handling**

   - Configurable approval timeout
   - Fail gracefully on timeout

4. **CLI commands**
   - `kiwi sessions` - List active sessions
   - `kiwi status {id}` - Get session status
   - `kiwi approve {id}` - Approve pending
   - `kiwi reject {id}` - Reject pending

### Files Changed/Created

```
kiwi_mcp/runtime/
├── checkpoint.py    # CheckpointManager
└── approval.py      # ApprovalManager

kiwi_mcp/cli/
├── __init__.py      # NEW: CLI module
├── main.py          # CLI entry point
└── commands/
    ├── sessions.py
    ├── approve.py
    └── reject.py
```

### Success Criteria

- [ ] Sensitive tool pauses for approval
- [ ] Human can approve via CLI
- [ ] Execution resumes after approval
- [ ] Timeout fails execution cleanly

### Effort: 6 days

---

## Phase 10: Pre-Loading & Environments (Weeks 22-23)

**Goal:** Pre-load directives and tools for batch/pipeline execution.

### Deliverables

1. **ExecutorEnvironment**

   - Pre-load directives
   - Pre-load MCP tools
   - Pre-load knowledge
   - Spawn executors from environment

2. **Pipeline execution**

   - Run multiple directives in sequence
   - Pass results between stages
   - Parallel execution support

3. **Environment persistence**
   - Save environment config
   - Reload for repeated runs

### Files Changed/Created

```
kiwi_mcp/runtime/
├── environment.py   # ExecutorEnvironment
└── pipeline.py      # PipelineRunner
```

### Success Criteria

- [ ] Environment pre-loads directive + tools
- [ ] Multiple directives run from same environment
- [ ] Pipeline passes data between stages

### Effort: 5 days

---

## Phase 11: Docker Executor & Advanced Isolation (Weeks 24-25)

**Goal:** Run untrusted tools in Docker containers.

### Deliverables

1. **DockerExecutor**

   - Build/pull container image
   - Mount volumes for I/O
   - Resource limits (CPU, memory)
   - Network isolation options

2. **Isolation levels**

   - `trusted`: No isolation
   - `standard`: Subprocess
   - `sandboxed`: Docker
   - `restricted`: Docker + no network

3. **Container management**
   - Image caching
   - Container cleanup
   - Volume management

### Files Changed/Created

```
kiwi_mcp/handlers/tool/executors/
└── docker.py        # DockerExecutor

kiwi_mcp/runtime/
└── containers.py    # ContainerManager
```

### Success Criteria

- [ ] Docker tool runs in container
- [ ] Resource limits enforced
- [ ] Container cleaned up after execution

### Effort: 6 days

---

## Phase 12: MCP 2.0 - Intent-Based Tool Calling (Weeks 26-28)

**Goal:** Abstract tool calling from syntax to intent. Agents express what they want; FunctionGemma resolves to actual tool calls.

**Design Document:** [MCP_2_INTENT_DESIGN.md](./MCP_2_INTENT_DESIGN.md)

### The Problem

As directives/tools scale to 1M+:
- Can't front-load all tool schemas into agent context
- Agents hallucinate tool args/syntax
- Context bloat limits recursion depth
- Every agent must "know" every tool

### The Solution: Intent Abstraction

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MCP 2.0 Architecture                            │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Front-End Agent (Any LLM)                   │  │
│  │  "To find leads, I need [TOOL: search for email scripts]"     │  │
│  └───────────────────────────────────┬───────────────────────────┘  │
│                                      │                               │
│                                      ▼                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Intent Parser                               │  │
│  │  Regex: \[TOOL:\s*(.+?)\]  →  intent_string                   │  │
│  └───────────────────────────────────┬───────────────────────────┘  │
│                                      │                               │
│                                      ▼                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    FunctionGemma (Tool Resolver)               │  │
│  │  Input: intent + context + relevant schemas (from RAG)         │  │
│  │  Output: <tool_call name="search"><arg>...</arg></tool_call>  │  │
│  └───────────────────────────────────┬───────────────────────────┘  │
│                                      │                               │
│                                      ▼                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Executor (Existing)                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Agent expresses intent** (not syntax):
   ```
   "To enrich leads, I need [TOOL: search for enrichment scripts that use Apollo API]"
   ```

2. **Intent Parser extracts**:
   ```python
   intent = "search for enrichment scripts that use Apollo API"
   context = conversation_history[-5:]
   ```

3. **FunctionGemma resolves** (with RAG-fetched schemas):
   ```xml
   <tool_call name="search">
     <arg name="query">enrichment scripts Apollo API</arg>
     <arg name="item_type">script</arg>
     <arg name="source">registry</arg>
   </tool_call>
   ```

4. **Executor runs** the resolved call.

### Deliverables

1. **Intent Parser**

   ```python
   class IntentParser:
       INTENT_PATTERN = r'\[TOOL:\s*(.+?)\]'
       
       def parse(self, agent_output: str) -> list[Intent]:
           matches = re.findall(self.INTENT_PATTERN, agent_output)
           return [Intent(text=m) for m in matches]
   ```

2. **FunctionGemma Resolver**

   ```python
   class ToolResolver:
       def __init__(self, model: str = "google/gemma-2-2b"):
           self.model = load_model(model)
           self.vector_store = VectorStore()  # From Phase 11
       
       async def resolve(self, intent: Intent, context: list[Message]) -> ToolCall:
           # RAG: Find relevant tool schemas
           schemas = await self.vector_store.search(
               intent.text, 
               item_type="tool",
               limit=10
           )
           
           # Prompt FunctionGemma
           prompt = self._build_prompt(intent, context, schemas)
           response = await self.model.generate(prompt)
           
           return self._parse_tool_call(response)
   ```

3. **Updated Agent Prompt** (in AGENTS.md):

   ```markdown
   ## Tool Calling
   
   Express tool needs as intents: `[TOOL: description of what you need]`
   
   Examples:
   - `[TOOL: search for email campaign directives]`
   - `[TOOL: execute the deploy_staging script with env=prod]`
   - `[TOOL: load knowledge about API rate limiting]`
   
   Do NOT worry about exact syntax or arguments—the system resolves them.
   ```

4. **Fallback mode**: Direct tool calls still work for backward compat.

### Files Changed/Created

```
kiwi_mcp/intent/
├── __init__.py
├── parser.py           # IntentParser
├── resolver.py         # ToolResolver (FunctionGemma)
└── prompts.py          # Resolver prompt templates

kiwi_mcp/server.py      # Hook intent parsing into harness loop

AGENTS.md               # Update with intent syntax
```

### Success Criteria

- [ ] Intent syntax `[TOOL: ...]` parsed correctly
- [ ] FunctionGemma resolves intents to valid tool calls
- [ ] RAG integration provides relevant schemas
- [ ] Fallback to direct calls works
- [ ] Latency < 500ms for resolution

### Effort: 6 days

---

## Phase 13: MCP 2.5 - Predictive Pre-Fetching (Weeks 29-31)

**Design Document:** [MCP_2_INTENT_DESIGN.md](./MCP_2_INTENT_DESIGN.md) (Section 3)

**Goal:** Predict tool intents during agent generation and pre-fetch search results, enabling FunctionGemma to skip search/load and execute directly.

### The Insight

While the front-end agent generates its response, we can:
1. Snapshot the conversation periodically
2. Predict likely tool intents
3. Pre-fetch search results for predicted intents
4. When actual intent arrives, if it matches prediction → shortcut to execute

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MCP 2.5 Architecture                            │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Front-End Agent (Generating...)             │  │
│  │  "To handle the campaign, I need to first..."                 │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │ (parallel snapshot)                   │
│          ┌───────────────────┴───────────────────┐                  │
│          │                                       │                   │
│          ▼                                       ▼                   │
│  ┌───────────────────┐                 ┌────────────────────────┐   │
│  │  Intent Predictor │                 │  Agent Completes       │   │
│  │  (BERT/small LLM) │                 │  "[TOOL: search...]"   │   │
│  └─────────┬─────────┘                 └───────────┬────────────┘   │
│            │                                       │                 │
│            ▼                                       │                 │
│  ┌───────────────────┐                             │                 │
│  │  Pre-Fetch        │                             │                 │
│  │  Dispatcher       │                             │                 │
│  │  (runs predicted  │                             │                 │
│  │   searches)       │                             │                 │
│  └─────────┬─────────┘                             │                 │
│            │                                       │                 │
│            ▼                                       ▼                 │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Intent Resolution (MCP 2.0)                   ││
│  │  IF actual ≈ predicted → use cached results → skip search       ││
│  │  ELSE → normal resolution                                        ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Periodic snapshot** during agent generation:
   ```python
   # Every 100 tokens or at newlines
   snapshot = {"history": messages[-5:], "partial": agent_buffer}
   ```

2. **Intent Predictor** (lightweight BERT or small LLM):
   ```python
   predictions = predictor.predict(snapshot)
   # Output: [
   #   {"intent": "search scripts for email", "confidence": 0.85},
   #   {"intent": "load directive outbound_campaign", "confidence": 0.6}
   # ]
   ```

3. **Pre-Fetch Dispatcher**:
   ```python
   # For top N predictions (confidence > threshold)
   for pred in predictions[:2]:
       if pred.confidence > 0.7:
           results = await self.search(pred.intent)
           self.cache[pred.intent_hash] = results  # TTL: 10s
   ```

4. **Resolution with cache**:
   ```python
   # When actual intent arrives
   if semantic_match(actual_intent, cached_predictions):
       # Shortcut: FunctionGemma gets pre-fetched results
       return await resolver.resolve(intent, context, prefetched=cache[match])
   else:
       # Normal path
       return await resolver.resolve(intent, context)
   ```

### Deliverables

1. **Intent Predictor**

   ```python
   class IntentPredictor:
       def __init__(self):
           self.model = load_model("sentence-transformers/all-MiniLM-L6-v2")
           # Fine-tuned on audit logs: conversation → intent mappings
       
       async def predict(self, snapshot: dict) -> list[Prediction]:
           # Encode snapshot
           embedding = self.model.encode(snapshot["partial"])
           
           # Match against common intent patterns
           # Return ranked predictions with confidence
   ```

2. **Pre-Fetch Cache**

   ```python
   class PreFetchCache:
       def __init__(self, ttl_seconds: int = 10):
           self.cache: dict[str, CacheEntry] = {}
           self.ttl = ttl_seconds
       
       async def store(self, intent_hash: str, results: list):
           self.cache[intent_hash] = CacheEntry(
               results=results,
               expires=time.time() + self.ttl
           )
       
       async def match(self, actual_intent: str) -> Optional[list]:
           # Semantic similarity match
           for key, entry in self.cache.items():
               if entry.is_valid() and similarity(key, actual_intent) > 0.8:
                   return entry.results
           return None
   ```

3. **Parallel Pipeline**

   ```python
   class MCP25Harness:
       async def process_agent_stream(self, stream: AsyncIterator[str]):
           buffer = ""
           async for chunk in stream:
               buffer += chunk
               
               # Snapshot every 100 chars
               if len(buffer) % 100 == 0:
                   asyncio.create_task(self._predict_and_prefetch(buffer))
               
               # Check for intent
               if "[TOOL:" in buffer:
                   intent = self.parser.parse(buffer)
                   cached = await self.cache.match(intent)
                   if cached:
                       # Shortcut!
                       result = await self.resolver.resolve(intent, prefetched=cached)
                   else:
                       result = await self.resolver.resolve(intent)
   ```

4. **Learning loop**:
   - Log prediction accuracy (hit/miss)
   - Fine-tune predictor on misses
   - Store patterns in knowledge entries

### Files Changed/Created

```
kiwi_mcp/intent/
├── predictor.py        # IntentPredictor
├── prefetch.py         # PreFetchCache + Dispatcher
└── pipeline.py         # MCP25Harness (streaming)

kiwi_mcp/training/
├── __init__.py
└── predictor_training.py  # Fine-tuning on audit logs
```

### Success Criteria

- [ ] Predictions generated during agent streaming
- [ ] Pre-fetch cache hit rate > 60%
- [ ] End-to-end latency reduced by 30%+
- [ ] Predictor improves from audit logs
- [ ] Graceful fallback on cache miss

### Effort: 7 days

---

## Summary Timeline

| Phase | Focus                         | Weeks | Days | Dependencies   |
| ----- | ----------------------------- | ----- | ---- | -------------- |
| 1     | Tool Foundation               | 1-2   | 5    | None           |
| 2     | Bash & API Executors          | 3-4   | 5    | Phase 1        |
| 3     | Proxy & Permission Enforce    | 5-7   | 8    | Phase 2        |
| 4     | Git Checkpoint                | 8-9   | 6    | Phase 3        |
| 5     | MCP Client Pool               | 10-11 | 6    | Phase 4        |
| 6     | RAG & Vector Search           | 12-14 | 7    | Phase 5        |
| 7     | Directive Executor            | 15-17 | 8    | Phase 6        |
| 8     | Annealing Integration         | 18-19 | 4    | Phase 7        |
| 9     | Human Approval                | 20-21 | 6    | Phase 7, 8     |
| 10    | Environments                  | 22-23 | 5    | Phase 7        |
| 11    | Docker Executor               | 24-25 | 6    | Phase 3        |
| 12    | MCP 2.0 Intent Calling        | 26-28 | 6    | Phase 6        |
| 13    | MCP 2.5 Predictive            | 29-31 | 7    | Phase 12       |

**Total: ~31 weeks, 79 days of development**

---

## Quick Wins (Can Do Anytime)

These are independent improvements that can be done in parallel:

1. **`<tools>` tag documentation** - Update DIRECTIVE_AUTHORING.md
2. **Tool manifest schema** - JSON Schema for validation
3. **git_checkpoint directive** - Can write without code changes
4. **MCP registry YAML** - Configuration file format
5. **Audit log viewer** - Simple CLI or web viewer

---

## Risk Mitigation

| Risk                      | Impact | Mitigation                               |
| ------------------------- | ------ | ---------------------------------------- |
| MCP protocol complexity   | High   | Start with stdio, simplest servers       |
| LLM cost explosion        | Medium | Budget limits, token tracking early      |
| Breaking existing scripts | High   | Backward compat alias, extensive testing |
| Docker availability       | Low    | Make DockerExecutor optional             |
| Human approval UX         | Medium | Start with CLI, add web later            |

---

## Success Metrics

**Phase 5 Completion (Scalable Search):**

- Semantic search across 100K+ directives
- Three-tier vector storage operational (project/user/registry)
- Validation-gated embedding (security layer)
- Hybrid search (semantic + keyword) outperforms baseline

**Phase 6 Completion (MVP Harness):**

- Directives spawn isolated executors
- Tool calls proxied through Kiwi
- Audit log for all operations
- At least 2 external MCPs working (supabase + github)

**Phase 9 Completion (Production Ready):**

- Human approval flow working
- Git checkpoints for mutations
- Annealing improves failed directives
- Cost tracking per execution

**Phase 11 Completion (Full Harness):**

- Docker isolation for untrusted tools
- Pre-loaded environments for pipelines
- All tool types working (Python, Bash, API, MCP, Docker)
- CLI for session management

**Phase 13 Completion (MCP 2.5 - Intent OS):**

- Agents express intents, not syntax
- FunctionGemma resolves with <500ms latency
- Predictive pre-fetching achieves >60% hit rate
- End-to-end latency reduced by 30%+
- System scales to 1M+ tools without context bloat

---

## Next Steps

1. **Review this roadmap** with stakeholders
2. **Phase 1 kickoff**: Create tool foundation branch
3. **Test strategy**: Define integration tests for each phase
4. **Documentation**: Update as each phase completes

---

## Related Documents

- [TOOLS_EVOLUTION_PROPOSAL.md](./TOOLS_EVOLUTION_PROPOSAL.md) - Scripts → Tools design
- [MCP_ORCHESTRATION_DESIGN.md](./MCP_ORCHESTRATION_DESIGN.md) - MCP routing design
- [DIRECTIVE_RUNTIME_ARCHITECTURE.md](./DIRECTIVE_RUNTIME_ARCHITECTURE.md) - Executor design
- [RUNTIME_PERMISSION_DESIGN.md](./RUNTIME_PERMISSION_DESIGN.md) - Permission enforcement & help tool
- [RAG_VECTOR_SEARCH_DESIGN.md](./RAG_VECTOR_SEARCH_DESIGN.md) - Vector DB and semantic search
- [MCP_2_INTENT_DESIGN.md](./MCP_2_INTENT_DESIGN.md) - Intent-based tool calling (2.0 & 2.5)
- [AGENT_ARCHITECTURE_COMPARISON.md](./AGENT_ARCHITECTURE_COMPARISON.md) - Normal vs Kiwi MCP approach
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Current system architecture
- [LILUX_VISION.md](./LILUX_VISION.md) - Long-term OS vision
