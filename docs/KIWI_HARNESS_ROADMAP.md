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

## Phase 3: Kiwi Proxy Layer (Weeks 5-6)

**Goal:** Route all tool calls through a proxy that enforces permissions and logs actions.

### Deliverables

1. **KiwiProxy class**

   ```python
   class KiwiProxy:
       async def call_tool(self, tool_id: str, params: dict) -> Any:
           # Permission check
           # Rate limit check
           # Audit log
           # Route to executor
   ```

2. **FilesystemExecutor** (builtin proxy)

   - `filesystem.read`, `filesystem.write`, `filesystem.list`
   - Path enforcement from directive permissions

3. **ShellExecutor** (builtin proxy)

   - `shell.run` with command allowlist
   - Timeout and output capture

4. **Audit logging**

   - `.ai/logs/audit/{date}/{session}.jsonl`
   - Tool call, params, result, timing

5. **Directive context threading**
   - Pass directive context through tool calls
   - Enforce permissions at proxy level

### Files Changed/Created

```
kiwi_mcp/
├── runtime/             # NEW directory
│   ├── __init__.py
│   ├── proxy.py         # KiwiProxy
│   └── audit.py         # AuditLogger
└── handlers/tool/executors/
    ├── filesystem.py    # NEW: FilesystemExecutor
    └── shell.py         # NEW: ShellExecutor
```

### Success Criteria

- [ ] All tool calls logged to audit file
- [ ] Permission denied when tool not in directive
- [ ] Filesystem paths enforced
- [ ] Shell commands filtered

### Effort: 6 days

---

## Phase 4: MCP Client Pool (Weeks 7-8)

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

## Phase 5: Directive Executor Runtime (Weeks 9-11)

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

## Phase 6: Annealing Integration (Week 12)

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

## Phase 7: Git Checkpoint Integration (Weeks 13-14)

**Goal:** Audit trail via git commits for state-mutating operations.

### Deliverables

1. **git_checkpoint directive**

   - Show diff
   - Generate commit message
   - Commit or rollback

2. **`mutates_state` handling**

   - Tool manifests declare mutation
   - Executor recommends checkpoint after mutating tools

3. **Rollback support**

   - `execute(action="rollback", item_id="{session_id}")`
   - Revert to pre-execution state

4. **Git helper utilities**
   - `GitHelper.status()`, `GitHelper.commit()`, `GitHelper.reset()`

### Files Changed/Created

```
kiwi_mcp/handlers/git/
├── __init__.py
├── checkpoint.py    # GitCheckpoint helper
└── helper.py        # Git operations

.ai/directives/core/
└── git_checkpoint.md  # Checkpoint directive
```

### Success Criteria

- [ ] Mutating tool triggers checkpoint recommendation
- [ ] Checkpoint creates commit with directive reference
- [ ] Rollback reverts changes

### Effort: 5 days

---

## Phase 8: Human Approval & Checkpoints (Weeks 15-16)

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

## Phase 9: Pre-Loading & Environments (Weeks 17-18)

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

## Phase 10: Docker Executor & Advanced Isolation (Weeks 19-20)

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

## Summary Timeline

| Phase | Focus                 | Weeks | Days | Dependencies |
| ----- | --------------------- | ----- | ---- | ------------ |
| 1     | Tool Foundation       | 1-2   | 5    | None         |
| 2     | Bash & API Executors  | 3-4   | 5    | Phase 1      |
| 3     | Kiwi Proxy Layer      | 5-6   | 6    | Phase 2      |
| 4     | MCP Client Pool       | 7-8   | 6    | Phase 3      |
| 5     | Directive Executor    | 9-11  | 8    | Phase 4      |
| 6     | Annealing Integration | 12    | 4    | Phase 5      |
| 7     | Git Checkpoint        | 13-14 | 5    | Phase 5      |
| 8     | Human Approval        | 15-16 | 6    | Phase 5, 7   |
| 9     | Environments          | 17-18 | 5    | Phase 5      |
| 10    | Docker Executor       | 19-20 | 6    | Phase 3      |

**Total: ~20 weeks, 56 days of development**

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

**Phase 5 Completion (MVP):**

- Directives spawn isolated executors
- Tool calls proxied through Kiwi
- Audit log for all operations
- At least 2 external MCPs working (supabase + github)

**Phase 8 Completion (Production Ready):**

- Human approval flow working
- Git checkpoints for mutations
- Annealing improves failed directives
- Cost tracking per execution

**Phase 10 Completion (Full Harness):**

- Docker isolation for untrusted tools
- Pre-loaded environments for pipelines
- All tool types working (Python, Bash, API, MCP, Docker)
- CLI for session management

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
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Current system architecture
- [LILUX_VISION.md](./LILUX_VISION.md) - Long-term OS vision
