# Safety Harness Implementation Plan

**Source Document:** `.ai/tmp/harness_and_execution_model.md`  
**Status:** Planning  
**Estimated Time:** 2-3 weeks

## Overview

Implement the Safety Harness layer that sits between the MCP kernel and LLM execution. The harness orchestrates all the existing primitives (tokens, registry, spawn_thread, intervention tools) into a unified enforcement layer.

## Architecture Recap

```
┌─────────────────────────────────────────────────────────┐
│                    LLM Execution                        │
│  (Executes directive content, sees injected responses)  │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ Injects call+response
┌─────────────────────────────────────────────────────────┐
│                   SAFETY HARNESS                        │  ◄── THIS IS WHAT WE'RE BUILDING
│  - Wraps thread_directive calls                         │
│  - Enforces tokens, costs, limits                       │
│  - Triggers hooks on conditions                         │
│  - Deterministic injection                              │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ Returns JSON
┌─────────────────────────────────────────────────────────┐
│                   MCP KERNEL (Done)                     │
│  - Dumb, stateless                                      │
│  - Returns directive content                            │
└─────────────────────────────────────────────────────────┘
```

## Existing Primitives (Already Done ✅)

| Component | Location | Purpose |
|-----------|----------|---------|
| CapabilityToken | `kiwi_mcp/safety_harness/capabilities.py` | Token minting, signing, attenuation |
| CapabilityRegistry | `.ai/tools/capabilities/` | All capability definitions |
| ThreadRegistry | `.ai/tools/threads/thread_registry.py` | SQLite thread state |
| spawn_thread | `.ai/tools/threads/spawn_thread.py` | OS thread spawning |
| inject_message | `.ai/tools/threads/inject_message.py` | Thread intervention |
| pause/resume_thread | `.ai/tools/threads/` | Thread control |
| LLM configs | `.ai/tools/llm/` | Anthropic/OpenAI API configs |

---

## Phase 1: Core Safety Harness (Days 1-3)

The foundational harness class that wraps execution.

### 1.1 Create SafetyHarness class

**File:** `.ai/tools/threads/safety_harness.py`

**Tasks:**
- [ ] Create `SafetyHarness` dataclass with execution context
- [ ] Add `ExecutionContext` with thread_id, token, cost_budget, limits
- [ ] Add `HarnessConfig` for configurable limits
- [ ] Implement `__init__` that accepts config and parent token

**Key Methods:**
```python
class SafetyHarness:
    def __init__(self, config: HarnessConfig, parent_token: Optional[CapabilityToken] = None)
    async def execute_directive(self, directive_name: str, inputs: Dict) -> ExecutionResult
    async def spawn_thread_with_directive(self, directive_name: str, inputs: Dict) -> ThreadHandle
```

### 1.2 Implement permission checking

**Tasks:**
- [ ] Add `check_permissions(required_caps: List[str]) -> PermissionResult`
- [ ] Integrate with `CapabilityToken.has_all_capabilities()`
- [ ] Return structured result with missing caps list

### 1.3 Implement cost tracking

**Tasks:**
- [ ] Create `CostBudget` dataclass (max_tokens, max_turns, max_spawns, max_duration_sec)
- [ ] Create `CostUsage` dataclass (tokens_used, turns_used, spawns_used, duration_sec)
- [ ] Add `check_cost_budget() -> CostResult` 
- [ ] Add `record_usage(usage: CostUsage)` method
- [ ] Integrate with ThreadRegistry's `cost_budget_json` and `total_usage_json`

### 1.4 Implement limit enforcement

**Tasks:**
- [ ] Add turn limit checking (before each LLM turn)
- [ ] Add spawn threshold checking (before spawning child threads)
- [ ] Add duration limit checking (via asyncio timeout)
- [ ] Return structured limit violation results

---

## Phase 2: thread_directive Tool (Days 4-5)

The user-facing tool that LLMs call to spawn directives on threads.

### 2.1 Create thread_directive tool

**File:** `.ai/tools/threads/thread_directive.py`

**Tasks:**
- [ ] Create tool with standard metadata (`__tool_type__`, etc.)
- [ ] Accept `directive_name`, `inputs`, `model_tier` parameters
- [ ] Internally use SafetyHarness for all enforcement
- [ ] Return structured result with thread_id, status, result

**Flow:**
```
thread_directive(directive_name, inputs)
  └─► SafetyHarness.spawn_thread_with_directive()
        ├─► check_permissions()
        ├─► check_cost_budget()
        ├─► spawn_thread() [existing tool]
        ├─► make MCP call: execute(directive, run, directive_name)
        ├─► inject call+response into thread
        └─► return ThreadHandle
```

### 2.2 Implement deterministic injection

**Tasks:**
- [ ] After spawning thread, harness makes MCP call (not LLM)
- [ ] Harness injects tool_call message into thread transcript
- [ ] Harness injects tool_result message into thread transcript
- [ ] LLM sees pre-filled conversation and executes directive content

**Injection format:**
```json
{"type": "tool_call", "tool": "kiwi-mcp", "action": "execute", "params": {...}}
{"type": "tool_result", "result": {"directive": "...", "instruction": "execute now"}}
```

### 2.3 Add YAML sidecar for discoverability

**File:** `.ai/tools/threads/thread_directive.yaml`

**Tasks:**
- [ ] Create YAML with tool metadata for discovery
- [ ] Declare required capabilities: `spawn.thread`, `kiwi-mcp.execute`
- [ ] Document parameters and usage

---

## Phase 3: Hook System Foundation (Days 6-8)

Implement the hook trigger and execution system.

### 3.1 Hook metadata parser

**File:** `kiwi_mcp/handlers/hook_parser.py`

**Tasks:**
- [ ] Extract `<hooks>` element from directive metadata
- [ ] Parse hook conditions: `on_permission_denied`, `on_cost_exceeded`, etc.
- [ ] Extract `<condition>` custom conditions (for flexible hooks)
- [ ] Extract `<directive_name>`, `<on_success>`, `<on_failure>`
- [ ] Validate hook structure

**Data structure:**
```python
@dataclass
class HookDefinition:
    condition_type: str  # "on_permission_denied", "on_cost_exceeded", "custom"
    condition_expr: Optional[str]  # For custom conditions
    directive_name: str
    on_success: str  # "retry", "continue", "skip", "fail", "abort"
    on_failure: str
    fallback_tier: Optional[str]
```

### 3.2 Condition evaluation engine

**File:** `.ai/tools/threads/condition_evaluator.py`

**Tasks:**
- [ ] Implement safe expression evaluator (NO `eval()`)
- [ ] Support comparison operators: `>`, `<`, `==`, `!=`, `>=`, `<=`
- [ ] Support logical operators: `and`, `or`, `not`
- [ ] Support membership tests: `in`, `not in`
- [ ] Build evaluation context from execution state

### 3.3 Template variable substitution

**Tasks:**
- [ ] Support `${directive.name}` syntax
- [ ] Support nested paths: `${token.capabilities}`, `${cost.tokens_used}`
- [ ] Recursively substitute in nested structures
- [ ] Handle missing variables gracefully

### 3.4 Hook trigger logic in harness

**Tasks:**
- [ ] Add `evaluate_hooks(execution_state: Dict) -> List[TriggeredHook]`
- [ ] Check all hook conditions after each event
- [ ] Return list of triggered hooks in metadata order

---

## Phase 4: Hook Execution (Days 9-11)

Execute hooks and handle their results.

### 4.1 Hook executor

**Tasks:**
- [ ] Add `execute_hook(hook: HookDefinition, context: Dict) -> HookResult`
- [ ] Spawn new thread for hook directive (recursive harness attachment)
- [ ] Wait for hook completion
- [ ] Return success/failure with result data

### 4.2 Action handlers

**Tasks:**
- [ ] Implement `retry` action - re-execute original directive
- [ ] Implement `continue` action - proceed despite condition
- [ ] Implement `skip` action - skip current step, continue workflow
- [ ] Implement `fail` action - return error to caller
- [ ] Implement `abort` action - terminate entire execution tree
- [ ] Implement `retry_with_fallback` - retry with different model tier

### 4.3 Recursive harness attachment

**Tasks:**
- [ ] Ensure all spawned threads (including hooks) have SafetyHarness
- [ ] Pass attenuated token to child harness
- [ ] Share cost budget across tree (or allocate sub-budgets)
- [ ] Verify enforcement at every level

---

## Phase 5: Hook Directives (Days 12-13)

Create the standard hook directives.

### 5.1 Create hook directives

**Location:** `.ai/directives/hooks/`

**Directives to create:**
- [ ] `handle_loop_detected.md` - Break infinite loops
- [ ] `request_elevated_permissions.md` - Request additional caps (with user approval)
- [ ] `anneal_directive.md` - Simplify directive for cost reduction
- [ ] `switch_to_fallback_model.md` - Switch to lower model tier
- [ ] `abort_execution.md` - Clean abort with state preservation

### 5.2 Directive structure

Each hook directive should have:
- [ ] Clear inputs (execution context, failed condition, etc.)
- [ ] Clear outputs (action to take, modified state, etc.)
- [ ] Process steps for the hook logic
- [ ] Signed and validated

---

## Phase 6: Integration & Testing (Days 14-16)

### 6.1 Integration tests

**File:** `tests/harness/test_safety_harness.py`

**Tests:**
- [ ] Permission denied → hook → retry with elevated token
- [ ] Cost exceeded → hook → retry with simplified request
- [ ] Model unavailable → fallback tier selection
- [ ] Execution failure → hook → fallback action
- [ ] Hook success → retry original
- [ ] Hook failure → fail to caller
- [ ] Recursive spawning with harness at all levels
- [ ] Cost tracking across spawn tree

### 6.2 Template variable tests

- [ ] Simple variables `${directive.name}`
- [ ] Nested variables `${token.capabilities}`
- [ ] Missing variable handling

### 6.3 Condition evaluation tests

- [ ] Comparison operators
- [ ] Logical operators
- [ ] Membership tests
- [ ] Complex expressions

### 6.4 Action execution tests

- [ ] All action types work correctly
- [ ] Actions chain correctly
- [ ] Multiple hooks for same condition (first wins)

---

## Phase 7: Documentation (Day 17)

### 7.1 User documentation

- [ ] Hook metadata format
- [ ] Hook action types
- [ ] Template variable syntax
- [ ] Condition evaluation syntax
- [ ] Safety harness behavior
- [ ] Recursive enforcement

### 7.2 Developer documentation

- [ ] SafetyHarness API
- [ ] Adding custom hooks
- [ ] Extending condition evaluator

---

## File Structure (Final)

```
.ai/tools/threads/
├── safety_harness.py      # NEW: Core harness class
├── thread_directive.py    # NEW: User-facing tool
├── thread_directive.yaml  # NEW: Tool discovery metadata
├── condition_evaluator.py # NEW: Safe expression evaluation
├── spawn_thread.py        # Existing
├── thread_registry.py     # Existing
├── inject_message.py      # Existing
├── pause_thread.py        # Existing
├── resume_thread.py       # Existing
└── read_transcript.py     # Existing

.ai/directives/hooks/
├── handle_loop_detected.md
├── request_elevated_permissions.md
├── anneal_directive.md
├── switch_to_fallback_model.md
└── abort_execution.md

kiwi_mcp/handlers/
└── hook_parser.py         # NEW: Hook metadata extraction

tests/harness/
├── test_safety_harness.py # NEW: Integration tests
├── test_condition_eval.py # NEW: Condition evaluator tests
└── test_capability_tokens.py # Existing
```

---

## Verification Checklist

After implementation, verify:

- [ ] `thread_directive` tool works end-to-end
- [ ] Permissions are enforced (denied → hook → retry)
- [ ] Costs are tracked and enforced
- [ ] Hooks trigger on all condition types
- [ ] Actions execute correctly
- [ ] Recursive spawning has harness at all levels
- [ ] All tests pass
- [ ] Documentation is complete

---

## Dependencies

| Phase | Depends On |
|-------|------------|
| Phase 1 | Existing primitives (✅ done) |
| Phase 2 | Phase 1 |
| Phase 3 | Phase 1 |
| Phase 4 | Phase 3 |
| Phase 5 | Phase 4 |
| Phase 6 | All phases |
| Phase 7 | All phases |

**Parallelization:** Phases 2 and 3 can run in parallel after Phase 1.

---

## Open Questions (from doc)

Decisions needed during implementation:

1. **Hook recursion depth** - Max depth for hooks-calling-hooks?
2. **Cost budget sharing** - Shared budget or sub-allocation for child threads?
3. **Hook ordering** - Metadata order, or priority field?
4. **Expression language** - Custom safe eval, or something like CEL?

---

## Related Documents

- `.ai/tmp/harness_and_execution_model.md` - Full architecture spec
- `implementation/thread-streaming/README.md` - Thread streaming phases
- `docs/PERMISSION_MODEL.md` - Permission enforcement details
