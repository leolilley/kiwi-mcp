# Unified Tools: Deferred Architecture

**Date:** 2026-01-23  
**Status:** Future Vision (Phase 7+)  
**Related:** [UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md](./UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md), [UNIFIED_TOOLS_ARCHITECTURE.md](./UNIFIED_TOOLS_ARCHITECTURE.md)

---

## Executive Summary

This document captures the **deferred components** of the unified tools architecture—items that are conceptually sound but require more foundation before implementation:

1. **Directives as Tools** - Making directives `tool_type: directive` with `executor: llm_runtime`
2. **Knowledge as Tools** - Making knowledge entries `tool_type: knowledge` with `executor: null`
3. **Thread Spawning** - `tool_type: thread` for sub-agent execution
4. **LLM Runtime** - A runtime that calls LLM APIs to execute directives

These are **deferred, not rejected**. Once the tool foundation is solid (Phases A-D complete), these can be revisited.

---

## Why Deferred?

| Item                | Reason for Deferral                            | Prerequisites                       |
| ------------------- | ---------------------------------------------- | ----------------------------------- |
| Directives as tools | Loses XML parsing, inverts orchestration model | Stable tool system, KiwiProxy layer |
| Knowledge as tools  | Loses graph semantics, Zettel system           | Unified search working              |
| Thread spawning     | Requires LLM runtime, permission scoping       | LLM runtime, audit layer            |
| LLM runtime         | Complex integration with multiple providers    | Tool system stable                  |

---

## 1. Directives as Tools

### Current Model (Keep for Now)

```
┌─────────────────────────────────────────────┐
│              DirectiveHandler               │
│  - Parses XML <directive> structure         │
│  - Extracts <permissions>, <model>, etc.    │
│  - Executes steps sequentially              │
│  - Orchestrates tool calls                  │
└─────────────────────────────────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │  ToolHandler  │
            │  (executor)   │
            └───────────────┘
```

### Future Model (Deferred)

```yaml
# Directive as a tool
tool_id: research_topic
tool_type: directive
executor: llm_runtime
version: "1.0.0"
description: "Research a topic thoroughly"
config:
  model_tier: balanced
  max_tokens: 50000
  permissions:
    tools: [web_search, read_web_page, finder]
    filesystem:
      read: ["**/*"]
      write: []
# Content stored in tool_version_files as "directive.md"
```

### Why This Is Complex

1. **XML Parsing**: Current `parse_directive_file()` extracts:

   - `<metadata>` with category, author, model tier
   - `<permissions>` with read/write/execute grants
   - `<inputs>` with parameter definitions
   - `<process>` with sequential steps
   - `<outputs>` with success/failure schemas

   Making directives tools requires either:

   - Storing parsed structure in manifest JSONB (loses fidelity)
   - Keeping XML in `tool_version_files` and parsing on load (dual format)

2. **Execution Model**: Directives are **orchestrators**, not executables:

   ```
   Current: Agent → DirectiveHandler → reads steps → calls tools
   Future:  Agent → ToolHandler → llm_runtime → spawns sub-agent → executes directive
   ```

   This requires the LLM runtime and sub-agent spawning infrastructure.

3. **Permission Enforcement**: Current model enforces permissions in `DirectiveHandler._run_directive()`. Future model needs:
   - KiwiProxy layer intercepting all tool calls
   - Permission checking before routing
   - Audit logging of all operations

### Implementation Path (When Ready)

**Prerequisites:**

- [ ] KiwiProxy layer complete (Phase 3 in roadmap)
- [ ] LLM runtime working (Phase 7)
- [ ] Audit layer complete (Phase 3)
- [ ] Tool system stable for 1+ month

**Steps:**

1. Add `directive` to `tool_type` constraint
2. Create migration for existing directives → tools
3. Implement DirectiveExecutor that:
   - Loads directive content from `tool_version_files`
   - Parses XML structure
   - Spawns sub-agent with scoped permissions
   - Executes steps sequentially
4. Create backward-compatible `directives` view
5. Update `DirectiveHandler` to route through `ToolHandler`

**Effort Estimate:** 3-4 weeks after prerequisites

---

## 2. Knowledge as Tools

### Current Model (Keep for Now)

```
┌─────────────────────────────────────────────┐
│            KnowledgeHandler                 │
│  - Parses Zettel frontmatter                │
│  - Manages graph relationships              │
│  - Supports include_relationships param     │
│  - Category/tag/entry_type filtering        │
└─────────────────────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   ┌─────────────┐    ┌──────────────────┐
   │ knowledge_  │    │ knowledge_       │
   │ entries     │    │ relationships    │
   │ (Zettel DB) │    │ (Graph links)    │
   └─────────────┘    └──────────────────┘
```

### Future Model (Deferred)

```yaml
# Knowledge as a tool
tool_id: api_design_patterns
tool_type: knowledge
executor: null # No execution, just retrieval
version: "1.0.0"
description: "Common REST API design patterns"
config:
  entry_type: pattern
  source_type: docs
  relationships:
    extends: ["http_best_practices"]
    references: ["rest_principles", "json_api_spec"]
# Content stored in tool_version_files as "content.md"
```

### Why This Is Complex

1. **Graph Relationships Lost**: Current schema has dedicated `knowledge_relationships` table:

   ```sql
   CREATE TABLE knowledge_relationships (
       id UUID PRIMARY KEY,
       from_zettel_id TEXT NOT NULL,
       to_zettel_id TEXT NOT NULL,
       relationship_type TEXT NOT NULL,  -- extends, references, contradicts, etc.
       created_at TIMESTAMPTZ
   );
   ```

   The unified model would need to either:

   - Embed relationships in manifest JSONB (loses queryability)
   - Keep separate relationship table (then why unify?)

2. **Zettel System**: Knowledge uses Zettel IDs (e.g., `20260123-api-patterns`) with specific semantics:

   - Date-prefixed for temporal ordering
   - Slug for human readability
   - Cross-references via `[[zettel_id]]` syntax in content

   Tools use `tool_id` without these conventions.

3. **Search Semantics Differ**:

   - Tool search: "Find a tool that can scrape websites"
   - Knowledge search: "What do I know about API rate limiting?"

   Mixing these in one search could confuse results.

4. **No Execution**: Knowledge has `executor: null` which breaks the executor chain model. It's pure data retrieval, not tool execution.

### Implementation Path (When Ready)

**Prerequisites:**

- [ ] Unified search working across types (Phase 6)
- [ ] Tool system stable
- [ ] Clear use case for unification (currently unclear)

**Steps:**

1. Add `knowledge` to `tool_type` constraint
2. Handle `executor: null` case in execution flow
3. Migrate knowledge graph to tool relationships (or keep separate)
4. Create KnowledgeExecutor that just returns content
5. Update search to handle mixed results

**Effort Estimate:** 2-3 weeks after prerequisites

**Recommendation:** Consider NOT unifying knowledge. It's fundamentally different from executable tools.

---

## 3. Thread Spawning

### Concept

Threads are **running instances** of directives, similar to processes vs programs:

| Concept     | Directive          | Thread                         |
| ----------- | ------------------ | ------------------------------ |
| Analogy     | Program (.py file) | Process (running Python)       |
| State       | Static definition  | Dynamic execution state        |
| Permissions | Declared in XML    | Scoped from parent + directive |
| Lifecycle   | Persistent         | Created → Running → Completed  |

### Proposed Tool Type

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

### Why This Is Complex

1. **LLM Runtime Required**: Need infrastructure to:

   - Call LLM APIs (Anthropic, OpenAI, etc.)
   - Manage conversation context
   - Handle tool call responses
   - Track token usage and costs

2. **Permission Scoping**: Child threads must have ≤ parent permissions:

   - Intersection of parent + directive permissions
   - No privilege escalation possible
   - Audit trail for all operations

3. **State Management**: Need to track:

   - Thread status (pending, running, completed, failed)
   - Execution context (messages, tool calls)
   - Cost tracking (tokens used)
   - Result storage

4. **Orchestration**: Parent needs to:
   - Spawn children
   - Wait for results
   - Handle failures
   - Aggregate outputs

### Database Schema (Future)

```sql
CREATE TABLE threads (
    id UUID PRIMARY KEY,
    thread_id TEXT NOT NULL UNIQUE,
    directive_id UUID REFERENCES tools(id),
    parent_thread_id UUID REFERENCES threads(id),

    -- Execution state
    status TEXT NOT NULL,  -- pending | running | completed | failed | cancelled
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Context
    input_params JSONB,
    scoped_permissions JSONB,

    -- Results
    output JSONB,
    error TEXT,

    -- Cost tracking
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(10,6),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE thread_messages (
    id UUID PRIMARY KEY,
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE,
    role TEXT NOT NULL,  -- system | user | assistant | tool
    content TEXT,
    tool_calls JSONB,
    tool_results JSONB,
    tokens INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Implementation Path (When Ready)

**Prerequisites:**

- [ ] LLM runtime complete
- [ ] KiwiProxy layer complete
- [ ] Audit layer complete
- [ ] Directives as tools (optional but helpful)

**Steps:**

1. Add `thread` to `tool_type` constraint
2. Create `threads` and `thread_messages` tables
3. Implement ThreadExecutor that:
   - Loads directive definition
   - Computes scoped permissions
   - Spawns LLM conversation
   - Routes tool calls through KiwiProxy
   - Tracks costs and state
4. Implement spawn_thread tool for parent threads
5. Add thread management CLI commands

**Effort Estimate:** 4-6 weeks after prerequisites

---

## 4. LLM Runtime

### Concept

The `llm_runtime` is a **runtime** (not a primitive) that uses `http_client` to call LLM APIs:

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
      models:
        - claude-sonnet-4-20250514
        - claude-3-haiku-20240307
    openai:
      url: https://api.openai.com/v1/chat/completions
      auth: "Bearer ${OPENAI_API_KEY}"
      models:
        - gpt-4o
        - gpt-4o-mini
  model_tiers:
    fast: { provider: anthropic, model: claude-3-haiku-20240307 }
    balanced: { provider: anthropic, model: claude-sonnet-4-20250514 }
    powerful: { provider: anthropic, model: claude-sonnet-4-20250514 }
    reasoning: { provider: openai, model: o1-preview }
  defaults:
    max_tokens: 4096
    temperature: 0
```

### Why This Keeps Two Primitives Pure

The design maintains that **only two primitives exist**:

- `subprocess` - Spawns processes
- `http_client` - Makes HTTP requests

LLM calling is just HTTP requests, managed by a specialized runtime. This is elegant because:

- No new primitive needed
- LLM providers are just HTTP endpoints
- Model selection is configuration, not code

### Components Needed

```
┌────────────────────────────────────────────────────────────┐
│                       LLMRuntime                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  ProviderRegistry                     │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │  │
│  │  │ Anthropic   │ │  OpenAI     │ │  Other          │ │  │
│  │  │ Adapter     │ │  Adapter    │ │  Adapters       │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│  ┌─────────────────────────┴────────────────────────────┐  │
│  │                 ConversationManager                   │  │
│  │  - Message history                                    │  │
│  │  - Tool call handling                                 │  │
│  │  - Context window management                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│  ┌─────────────────────────┴────────────────────────────┐  │
│  │                    CostTracker                        │  │
│  │  - Token counting                                     │  │
│  │  - Budget enforcement                                 │  │
│  │  - Usage reporting                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│                     http_client                             │
│                     (primitive)                             │
└────────────────────────────────────────────────────────────┘
```

### Implementation Path (When Ready)

**Prerequisites:**

- [ ] Tool system stable
- [ ] KiwiProxy layer complete
- [ ] Clear use case for automated directive execution

**Steps:**

1. Create `kiwi_mcp/runtime/llm/` module structure
2. Implement provider adapters (Anthropic, OpenAI)
3. Implement ConversationManager for message history
4. Implement CostTracker for token/budget management
5. Create LLMExecutor that:
   - Selects model based on tier
   - Builds system prompt from directive
   - Manages conversation loop
   - Routes tool calls through KiwiProxy
6. Register as runtime in database
7. Integrate with thread spawning

**Effort Estimate:** 6-8 weeks

---

## The Kernel Parallel (Future Vision)

When all deferred items are complete, Kiwi MCP becomes an **AI kernel**:

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

```
┌─────────────────────────────────────────────────────────────┐
│                    KIWI KERNEL (Phase 7+)                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Thread Scheduler                    │   │
│  │  - Token budgets                                     │   │
│  │  - Parallel execution                                │   │
│  │  - Priority queuing                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌───────────────────────┴──────────────────────────────┐  │
│  │                    KiwiProxy                          │  │
│  │  - Permission enforcement                             │  │
│  │  - Audit logging                                      │  │
│  │  - Rate limiting                                      │  │
│  │  - Tool routing                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│  ┌───────────────────────┴──────────────────────────────┐  │
│  │              Unified Tool System                      │  │
│  │  - All tool types in one table                        │  │
│  │  - Executor chain resolution                          │  │
│  │  - Dynamic tool creation                              │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│        ┌─────────────────┼─────────────────┐               │
│        ▼                 ▼                 ▼               │
│   ┌─────────┐      ┌───────────┐    ┌───────────────┐      │
│   │subprocess│      │http_client│    │   (future)    │      │
│   │primitive │      │ primitive │    │  primitives   │      │
│   └─────────┘      └───────────┘    └───────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Decision Matrix: When to Revisit

| Deferred Item       | Revisit When                | Signal to Proceed                  |
| ------------------- | --------------------------- | ---------------------------------- |
| Directives as tools | KiwiProxy + Audit complete  | Need automated directive execution |
| Knowledge as tools  | Unified search stable       | Clear value from unification       |
| Thread spawning     | LLM runtime working         | Need sub-agent orchestration       |
| LLM runtime         | Tool system stable 1+ month | Directive automation needed        |

---

## Risk Assessment

### Directives as Tools

- **Risk:** Loses XML parsing, breaks existing directives
- **Mitigation:** Keep backward-compatible view, dual-format support
- **Recommendation:** Proceed only if automation benefits outweigh complexity

### Knowledge as Tools

- **Risk:** Loses graph semantics, confuses search
- **Mitigation:** Keep separate or create hybrid model
- **Recommendation:** May never be worth unifying; keep separate

### Thread Spawning

- **Risk:** Complex state management, permission bugs
- **Mitigation:** Extensive testing, gradual rollout
- **Recommendation:** High value if done right; proceed carefully

### LLM Runtime

- **Risk:** Provider API changes, cost overruns
- **Mitigation:** Adapter pattern, strict budgets
- **Recommendation:** Essential for automation; implement after tool foundation

---

## Timeline (Estimated)

| Phase | Item                | Prerequisites       | Duration  | Earliest Start |
| ----- | ------------------- | ------------------- | --------- | -------------- |
| 7     | LLM Runtime         | Phases A-D complete | 6-8 weeks | Month 3        |
| 8     | Thread Spawning     | LLM Runtime         | 4-6 weeks | Month 5        |
| 9     | Directives as Tools | Thread Spawning     | 3-4 weeks | Month 6        |
| 10    | Knowledge as Tools  | Unified Search      | 2-3 weeks | Month 7+       |

**Total Deferred Work:** ~4-5 months after core implementation

---

## Conclusion

The deferred items represent the **ambitious vision** of UNIFIED_TOOLS_ARCHITECTURE.md. They're conceptually elegant but require:

1. **Stable foundation** - Phases A-D must be rock solid
2. **Clear use cases** - Automation needs that justify complexity
3. **Careful design** - Permission scoping, state management

The hybrid approach adopted in [UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md](./UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md) delivers immediate value while keeping the path open to this future vision.

**Key Insight:** Directives orchestrate tools; knowledge informs decisions. Making them tools inverts their purpose. Consider carefully before proceeding.

---

## Related Documents

- [UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md](./UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md) - Immediate implementation
- [UNIFIED_TOOLS_ARCHITECTURE.md](./UNIFIED_TOOLS_ARCHITECTURE.md) - Original full vision
- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Full roadmap with phases
- [DIRECTIVE_RUNTIME_ARCHITECTURE.md](./DIRECTIVE_RUNTIME_ARCHITECTURE.md) - Executor spawning design
