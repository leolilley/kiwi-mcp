# Tools Evolution Proposal: Scripts → Tools Upgrade

**Date:** 2026-01-21  
**Status:** Draft Proposal  
**Author:** Kiwi Team

---

## Executive Summary

This document analyzes a proposed evolution of Kiwi MCP from Python-only scripts to a multi-executor tool system with Git-based enforcement. The proposal maps well to our existing architecture but requires careful consideration of scope, permissions, and implementation order.

---

## Current Architecture Recap

Kiwi MCP currently implements:

```
┌─────────────────────────────────────────────────────────────┐
│                    4 Meta-Tools                              │
│   search  │  load  │  execute  │  help                       │
└─────────────────────────────────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
    DirectiveHandler  ScriptHandler  KnowledgeHandler
            │            │            │
    (XML workflows)  (Python only) (Markdown entries)
```

**Key Existing Patterns:**

- `TypeHandlerRegistry` routes by `item_type`
- `ValidationManager` with type-specific validators
- `MetadataManager` with type-specific signing/hashing strategies
- Permission enforcement on directives (run/create/update)
- Content signature verification before publish/copy

---

## Mapping Proposal to Current Codebase

### 1. Scripts → Tools Rename

The proposal suggests renaming "scripts" to "tools" with a `tool_type` executor field.

**Current Structure:**

```
.ai/scripts/
├── scraping/
│   └── google_maps_scraper.py
└── lib/
    └── http_session.py
```

**Proposed Structure:**

```
.ai/tools/
├── python/
│   └── google_maps_scraper/
│       ├── tool.yaml          # Manifest
│       └── main.py            # Entrypoint
├── bash/
│   └── deploy_script/
│       ├── tool.yaml
│       └── script.sh
├── api/
│   └── stripe_customer/
│       └── tool.yaml          # No code, just config
└── lib/                       # Shared Python libs (unchanged)
```

**Impact on Current Code:**

| Component         | Current                  | Change Required                                     |
| ----------------- | ------------------------ | --------------------------------------------------- |
| `ScriptHandler`   | Python-only              | Becomes `ToolHandler` with executor dispatch        |
| `ScriptResolver`  | Finds `.py` files        | Becomes `ToolResolver`, finds `tool.yaml` manifests |
| `ScriptRegistry`  | Supabase `scripts` table | Rename to `tools` table, add `tool_type` column     |
| `ScriptValidator` | Validates Python         | Dispatch to type-specific validators                |
| Registry table    | `scripts`                | Rename or alias to `tools`                          |

### 2. Tool Type Registry Pattern

**Current Pattern (single executor):**

```python
# kiwi_mcp/handlers/script/handler.py
async def _run_script(self, script_name, params, dry_run):
    # Always Python execution
    result = subprocess.run(["python", script_path, ...])
```

**Proposed Pattern (multi-executor):**

```python
# kiwi_mcp/handlers/tool/executors/__init__.py
class ToolExecutor(ABC):
    @abstractmethod
    async def execute(self, tool: ToolManifest, params: dict) -> ExecutionResult:
        pass

class PythonExecutor(ToolExecutor):
    async def execute(self, tool, params):
        # Current script execution logic (venv, deps, etc.)
        ...

class BashExecutor(ToolExecutor):
    async def execute(self, tool, params):
        # Shell script execution with param injection
        ...

class APIExecutor(ToolExecutor):
    async def execute(self, tool, params):
        # HTTP request with auth handling
        ...

EXECUTORS = {
    "python": PythonExecutor(),
    "bash": BashExecutor(),
    "api": APIExecutor(),
    # Future: "docker", "mcp", "git"
}
```

**Fits Our Pattern:** This mirrors our existing `TypeHandlerRegistry` → handler dispatch pattern, just nested one level deeper within the tool handler.

### 3. Permission Model Differences

**Current Directive Permissions:**

```xml
<permissions>
  <read resource="files" path="src/**/*.ts" />
  <write resource="api" endpoint="POST /users" />
</permissions>
```

The proposal introduces tool-level permissions for Docker, shell, etc. This is **complementary** to our existing model:

| Layer      | Scope                        | Enforcement Point                   |
| ---------- | ---------------------------- | ----------------------------------- |
| Directive  | Workflow-level intents       | `DirectiveHandler._run_directive()` |
| Tool (NEW) | Execution-level capabilities | `ToolExecutor.execute()`            |

**Key Insight:** Directive permissions declare _intent_, tool permissions declare _capability_. A directive that calls `bash_tool` should require:

```xml
<permissions>
  <execute resource="tool" tool_type="bash" />
</permissions>
```

### 4. Git Integration Analysis

The proposal suggests mandatory `git_checkpoint` after state-mutating operations.

**Current State:**

- We have signature verification (`MetadataManager.verify_signature()`)
- We enforce validation before publish/copy
- No Git integration currently

**Proposed Git Layer:**

```
Directive Run
     │
     ▼
Tool Execution (mutates files)
     │
     ▼
git_checkpoint directive
     │
     ├─ git status / git diff
     ├─ AI explains changes
     └─ git commit or git reset --hard
```

**Implementation Considerations:**

1. **Where does Git live?**

   - New `GitHandler` in handlers?
   - Built-in to `ToolHandler` for mutating ops?
   - Separate `git_checkpoint` directive (proposal approach)

2. **What triggers checkpoint?**

   - Explicit directive step (proposal)
   - Automatic after certain tool types (bash, docker)
   - Configurable per-tool in manifest

3. **What about non-Git projects?**
   - Need graceful degradation
   - Optional enforcement flag

**Recommended Approach:**

```python
# In ToolManifest (tool.yaml)
executor:
  type: bash
  mutates_state: true  # Triggers checkpoint requirement

# In ToolHandler
async def execute_tool(self, tool, params):
    result = await executor.execute(tool, params)

    if tool.executor.mutates_state:
        # Run git_checkpoint if available
        if self._has_git_context():
            await self._run_checkpoint(tool, result)

    return result
```

---

## Proposal Concerns & Corrections

### 1. Permission Model Mismatch

The proposal shows permissions in tool manifests:

```yaml
permissions:
  - type: shell
    commands: ["curl", "jq"]
```

**Our current model** uses permissions in _directives_, not scripts/tools. Tools are the _executors_, directives are the _authorizers_.

**Recommendation:** Keep permissions at directive level. Tool manifests declare _requirements_ (what they need), not _permissions_ (what they're allowed to do):

```yaml
# tool.yaml
executor:
  type: bash
  requires:
    commands: ["curl", "jq"] # Requirements to run
    environment: ["API_KEY"] # Required env vars
```

```xml
<!-- Directive authorizes tool use -->
<permissions>
  <execute resource="tool" id="my_bash_tool" />
  <shell commands="curl,jq" />
  <env vars="API_KEY" />
</permissions>
```

### 2. Over-Engineering Risk

The proposal includes:

- Docker executor
- MCP-to-MCP executor (tools calling other MCP servers)
- VM orchestration
- Full audit trail

**Phased Approach Recommended:**

| Phase | Scope                                         | Value                 |
| ----- | --------------------------------------------- | --------------------- |
| 1     | Rename scripts → tools, add `tool_type` field | Foundation            |
| 2     | Bash executor                                 | Most requested        |
| 3     | API executor                                  | External integrations |
| 4     | Git checkpoint directive                      | Audit trail           |
| 5     | Docker executor                               | Isolation             |
| 6     | MCP executor                                  | Meta-orchestration    |
| 7     | VM/automation                                 | Scale                 |

### 3. Backward Compatibility

The proposal doesn't address migration. Current scripts must continue working.

**Migration Strategy:**

```python
# In ToolResolver
def resolve(self, item_id):
    # Try new structure first
    if (self.tools_dir / item_id / "tool.yaml").exists():
        return self._load_tool_manifest(item_id)

    # Fall back to legacy Python script
    legacy_path = self._find_legacy_script(item_id)
    if legacy_path:
        return self._convert_legacy_to_manifest(legacy_path)

    return None

def _convert_legacy_to_manifest(self, script_path):
    """Create virtual manifest from legacy script metadata."""
    metadata = parse_script_metadata(script_path)
    return ToolManifest(
        tool_id=metadata["name"],
        tool_type="python",
        version=metadata.get("version", "0.0.0"),
        executor={
            "type": "python",
            "entrypoint": script_path.name,
            "legacy": True,  # Flag for special handling
        },
        ...
    )
```

---

## Tool Manifest Specification

Based on proposal but adapted to our patterns:

```yaml
---
# .ai/tools/{category}/{tool_id}/tool.yaml

tool_id: google_maps_scraper
tool_type: python # python | bash | api | docker | mcp
version: "2.1.0"
category: scraping
description: Extract business data from Google Maps

# Executor configuration (type-specific)
executor:
  # === Python ===
  type: python
  entrypoint: main.py
  venv: true # Use isolated venv
  dependencies:
    - requests>=2.31.0
    - beautifulsoup4>=4.12.0
  lib_imports: # From .ai/tools/lib/
    - http_session
    - proxy_pool

  # === Bash ===
  # type: bash
  # entrypoint: script.sh
  # shell: /bin/bash
  # requires:
  #   commands: [jq, curl]
  #   environment: [API_KEY]

  # === API ===
  # type: api
  # method: POST
  # endpoint: https://api.example.com/process
  # auth:
  #   type: bearer
  #   env_var: API_TOKEN
  # timeout: 30

  # === Docker ===
  # type: docker
  # image: python:3.11-slim
  # build_context: .
  # volumes:
  #   - source: ./data
  #     target: /app/data
  # network: host

# State mutation flag (triggers git checkpoint)
mutates_state: false

# Input parameters
parameters:
  - name: query
    type: string
    required: true
    description: Search query for Google Maps
  - name: location
    type: string
    required: false
    default: "New York, NY"

# Output specification
outputs:
  format: json # json | text | file
  schema: business_list # Optional: reference to known schema

# Metadata for search/discovery
tags: [scraping, google, maps, leads]
author: kiwi-team
created_at: 2026-01-15
---
```

---

## Handler Architecture Changes

### Current Handler Structure

```
kiwi_mcp/handlers/
├── __init__.py
├── registry.py              # TypeHandlerRegistry
├── directive/
│   ├── __init__.py
│   └── handler.py           # DirectiveHandler
├── script/
│   ├── __init__.py
│   └── handler.py           # ScriptHandler
└── knowledge/
    ├── __init__.py
    └── handler.py           # KnowledgeHandler
```

### Proposed Handler Structure

```
kiwi_mcp/handlers/
├── __init__.py
├── registry.py              # TypeHandlerRegistry (add "tool" type)
├── directive/
│   └── handler.py           # DirectiveHandler (unchanged)
├── tool/                    # Renamed from script/
│   ├── __init__.py
│   ├── handler.py           # ToolHandler (dispatch to executors)
│   ├── manifest.py          # ToolManifest dataclass
│   └── executors/
│       ├── __init__.py      # ExecutorRegistry
│       ├── base.py          # ToolExecutor ABC
│       ├── python.py        # PythonExecutor (current logic)
│       ├── bash.py          # BashExecutor (new)
│       ├── api.py           # APIExecutor (new)
│       └── docker.py        # DockerExecutor (future)
├── knowledge/
│   └── handler.py           # KnowledgeHandler (unchanged)
└── git/                     # New for checkpoint
    ├── __init__.py
    └── checkpoint.py        # GitCheckpoint helper
```

### TypeHandlerRegistry Changes

```python
# kiwi_mcp/handlers/registry.py

class TypeHandlerRegistry:
    def __init__(self, project_path: str):
        ...
        # Add tool handler (with backward compat alias)
        self.tool_handler = ToolHandler(project_path=project_path)
        self.handlers["tool"] = self.tool_handler
        self.handlers["script"] = self.tool_handler  # Backward compat alias
```

---

## Git Checkpoint Implementation

### As a Directive (Recommended)

Create a new core directive that can be called from other directives:

````markdown
<!-- .ai/directives/core/git_checkpoint.md -->
<!-- kiwi-mcp:validated:2026-01-21T00:00:00Z:abc123 -->

# Git Checkpoint

```xml
<directive name="git_checkpoint" version="1.0.0">
  <metadata>
    <description>Create checkpoint commit after state-mutating operations</description>
    <category>core</category>
    <author>kiwi-mcp</author>
    <model tier="fast" />
    <permissions>
      <execute resource="shell" commands="git" />
      <write resource="filesystem" path=".git/**" />
    </permissions>
  </metadata>

  <inputs>
    <input name="operation" type="string" required="true">
      Name of the operation that triggered this checkpoint
    </input>
    <input name="caller_directive" type="string" required="false">
      ID of the directive that invoked this checkpoint
    </input>
  </inputs>

  <process>
    <step name="check_git_status">
      <description>Check for changes</description>
      <action>
        Run: git status --porcelain
        If empty: Return early with "no_changes"
      </action>
    </step>

    <step name="show_diff">
      <description>Display changes for review</description>
      <action>
        Run: git diff --stat
        Run: git diff (if small enough)
        Present to user/supervisor
      </action>
    </step>

    <step name="generate_commit_message">
      <description>Create conventional commit message</description>
      <action>
        Analyze changes and generate message:
        - type: feat|fix|chore|refactor|docs|test
        - scope: derived from changed paths
        - description: summary of changes
        - footer: [directive: {caller_directive}]
      </action>
    </step>

    <step name="commit_or_abort">
      <description>Commit changes or abort</description>
      <action>
        If changes are acceptable:
          git add -A
          git commit -m "{generated_message}"
          Return commit SHA
        Else:
          git reset --hard
          Return failure with reason
      </action>
    </step>
  </process>

  <outputs>
    <success>
      commit_sha: string
      commit_message: string
      files_changed: number
      insertions: number
      deletions: number
    </success>
    <failure>
      reason: string
      state: "rolled_back" | "unchanged"
    </failure>
  </outputs>
</directive>
```
````

````

### Integration with Tools

```python
# kiwi_mcp/handlers/tool/handler.py

class ToolHandler:
    async def execute(self, action, tool_id, parameters, **kwargs):
        if action == "run":
            return await self._run_tool(tool_id, parameters)
        # ... other actions

    async def _run_tool(self, tool_id, parameters):
        # Load and execute tool
        manifest = await self._load_manifest(tool_id)
        executor = self._get_executor(manifest.tool_type)

        result = await executor.execute(manifest, parameters)

        # Check if checkpoint needed
        if manifest.mutates_state and self._has_git():
            result["checkpoint_recommended"] = True
            result["checkpoint_hint"] = (
                "This tool mutates state. Consider running git_checkpoint directive: "
                f"execute(item_type='directive', action='run', item_id='git_checkpoint', "
                f"parameters={{'operation': '{tool_id}'}})"
            )

        return result
````

---

## Migration Plan

### Phase 1: Foundation (Week 1-2)

1. **Create tool manifest schema** (`kiwi_mcp/handlers/tool/manifest.py`)
2. **Rename handler directory** (`script/` → `tool/`)
3. **Add backward compatibility** in `TypeHandlerRegistry`
4. **Update validators** for tool manifests
5. **Tests:** Ensure existing scripts still work

### Phase 2: Executor Framework (Week 3-4)

1. **Extract Python execution** into `PythonExecutor`
2. **Create `ExecutorRegistry`** for dispatch
3. **Implement `BashExecutor`**
4. **Add tool_type detection** in manifest loading
5. **Tests:** Python + Bash executors

### Phase 3: API & Git (Week 5-6)

1. **Implement `APIExecutor`**
2. **Create `git_checkpoint` directive**
3. **Add `mutates_state` flag handling**
4. **Tests:** API calls, Git integration

### Phase 4: Documentation & Migration (Week 7-8)

1. **Update AGENTS.md** command dispatch table
2. **Create migration guide** for existing scripts
3. **Add `migrate_script_to_tool` directive**
4. **Registry schema updates** (if needed)

---

## Open Questions & Recommendations

### 1. Storage location: Should tools live in `.ai/tools/` or keep `.ai/scripts/` for backward compat?

**Recommendation: Keep `.ai/scripts/` with graceful evolution.**

- Phase 1: Support both `.ai/scripts/*.py` (legacy) and `.ai/scripts/{name}/tool.yaml` (new)
- Phase 2: Add `.ai/tools/` as alias that resolves to scripts
- Rationale: Existing scripts continue working, no migration required initially

### 2. Registry compatibility: Do we rename the Supabase table or add `tool_type` column to existing?

**Recommendation: Add `tool_type` column to existing `scripts` table.**

```sql
ALTER TABLE scripts ADD COLUMN tool_type VARCHAR(20) DEFAULT 'python';
ALTER TABLE scripts ADD COLUMN executor_config JSONB;
```

- Rationale: No data migration, backward compatible, existing scripts get `tool_type='python'`
- Future: Create `tools` view that unions scripts with potential future tool sources

### 3. MCP executor: Should tools be able to call other MCP servers?

**Recommendation: Yes, via Kiwi proxy mode.**

- Tools declare MCP dependencies in their manifest
- Kiwi routes calls through its proxy layer
- See [MCP_ORCHESTRATION_DESIGN.md](./MCP_ORCHESTRATION_DESIGN.md) for full design
- This enables the agent harness pattern where Kiwi controls all tool access

### 4. Git enforcement: Should `git_checkpoint` be automatic, explicit, or configurable?

**Recommendation: Configurable per-directive, default to explicit.**

```xml
<metadata>
  <git_checkpoint mode="auto" />  <!-- auto | explicit | disabled -->
</metadata>
```

- `auto`: Checkpoint after each mutating tool call
- `explicit`: Only when directive includes checkpoint step (default)
- `disabled`: No checkpointing (for read-only or idempotent directives)
- Rationale: Different workflows need different granularity

### 5. Sandboxing: For bash/docker tools, what isolation do we need beyond venv?

**Recommendation: Layered isolation based on trust level.**

| Trust Level | Isolation | Use Case |
|-------------|-----------|----------|
| `trusted` | None (runs in main process) | Internal scripts, known-safe |
| `standard` | Subprocess with timeout | Most bash scripts |
| `sandboxed` | Docker container | Untrusted/external tools |
| `restricted` | Docker + network isolation | High-risk operations |

- Declare in tool manifest: `isolation: standard`
- Default: `standard` for bash, `trusted` for python (venv provides isolation)

---

## Conclusion

The proposal is **fundamentally sound** and maps well to our existing architecture. The key insight—abstracting scripts to typed tools with pluggable executors—extends our pattern naturally.

**Recommended approach:**

1. Start with Phase 1 (rename + manifest) to validate the pattern
2. Add executors incrementally (bash is highest value)
3. Git integration as a separate directive, not baked into tool execution
4. Keep permissions at directive level, not tool level
5. Ensure backward compatibility throughout

The VM/automation vision from the proposal is achievable once the foundation is solid, but should be considered a Phase 5+ goal.

---

## Cross-Reference

This document is part of the Kiwi MCP evolution:

- [MCP_ORCHESTRATION_DESIGN.md](./MCP_ORCHESTRATION_DESIGN.md) - MCP routing and proxy
- [DIRECTIVE_RUNTIME_ARCHITECTURE.md](./DIRECTIVE_RUNTIME_ARCHITECTURE.md) - Executor spawning
- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Implementation roadmap

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Current system architecture
- [PERMISSION_ENFORCEMENT.md](./PERMISSION_ENFORCEMENT.md) - Permission model
- [LILUX_VISION.md](./LILUX_VISION.md) - Long-term OS vision
- [HANDLER_ARCHITECTURE.md](./HANDLER_ARCHITECTURE.md) - Handler patterns
