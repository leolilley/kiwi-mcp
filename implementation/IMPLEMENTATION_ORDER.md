# Implementation Order: Parser + Safety Harness

**Status:** ✅ COMPLETE  
**Completed:** 2026-01-28  
**Total Estimated Time:** 2-3 weeks (completed in 1 session)

**Source Documents:**
- `.ai/tmp/parser_first_principles.md` - Parser spec
- `implementation/safety-harness/README.md` - Harness spec

---

## Overview

This document consolidates the implementation order for two related workstreams:

1. **Parser Updates** - New `<limits>` and `<model>` tag structure, hook extraction
2. **Safety Harness** - Expression-based hooks, checkpoint enforcement

The parser updates are prerequisites for the harness.

---

## Key Architecture Decisions

| Decision | Approach |
|----------|----------|
| `<cost>` tag | **Replaced** with `<limits>` - hard-cut, no backward compat |
| `fallback` attr | **Replaced** with `fallback_id` - deterministic model selection |
| Hook triggers | **Expression-based** - `<when>` expressions, not named trigger tags |
| Enforcement | **Hardcoded in harness** - known limits, events are data |
| Harness location | **Tool in `.ai/tools/`** - not a kernel primitive |
| Expression evaluator | **Tool-adjacent** in `.ai/tools/threads/` - tightly coupled to harness |
| Parser updates | **Both layers** - extractor rules AND underlying parser if needed |
| Spend tracking | **Phase 2** - `pricing.yaml` included, full spend enforcement |
| Test location | **New file** `tests/harness/test_safety_harness.py` - separate from capability tokens |

---

## Phase 0: Parser Updates (Days 1-2)

**Prerequisite for all other phases.**

### 0.1 Update `<limits>` Tag Extraction

**File:** `.ai/parsers/markdown_xml.py` (extraction logic)  
**File:** `.ai/extractors/directive/markdown_xml.py` (field rules)

Replace old `<cost>` structure:

```xml
<!-- OLD (remove support) -->
<cost>
  <context estimated_usage="high" turns="10" spawn_threshold="3">5000</context>
  <duration>300</duration>
  <spend currency="USD">10.00</spend>
</cost>

<!-- NEW -->
<limits>
  <turns>10</turns>
  <tokens>5000</tokens>
  <spawns>3</spawns>
  <duration>300</duration>
  <spend currency="USD">10.00</spend>
</limits>
```

**Extraction output:**
```python
"limits": {
    "turns": 10,
    "tokens": 5000,
    "spawns": 3,
    "duration": 300,
    "spend": 10.00,
    "spend_currency": "USD"
}
```

### 0.2 Update `<model>` Tag Extraction

**File:** `.ai/parsers/markdown_xml.py`

```xml
<model tier="reasoning" fallback_id="gpt-4o-mini" model_id="gpt-4">
  Brief context of what model capabilities are needed
</model>
```

**Extraction output:**
```python
"model": {
    "tier": "reasoning",
    "model_id": "gpt-4",
    "fallback_id": "gpt-4o-mini",
    "context": "Brief context of what model capabilities are needed"
}
```

### 0.3 Add `<hooks>` Tag Extraction (inside `<metadata>`)

**File:** `.ai/parsers/markdown_xml.py`

```xml
<metadata>
  <!-- ... other metadata ... -->
  <hooks>
    <hook>
      <when>event.code == "permission_denied"</when>
      <directive>request_elevated_permissions</directive>
      <inputs>
        <original_directive>${directive.name}</original_directive>
      </inputs>
    </hook>
  </hooks>
</metadata>
```

**Extraction output:**
```python
"hooks": [
    {
        "when": "event.code == \"permission_denied\"",
        "directive": "request_elevated_permissions",
        "inputs": {"original_directive": "${directive.name}"}
    }
]
```

### 0.4 Tasks

- [ ] Update `<limits>` extraction (replace `<cost>`) in `.ai/parsers/markdown_xml.py`
- [ ] Update extractor rules: rename `cost` → `limits`, add `hooks` field in `.ai/extractors/directive/markdown_xml.py`
- [ ] Update `<model>` extraction (`fallback_id` not `fallback`)
- [ ] Add `<hooks>` extraction (`<when>`, `<directive>`, `<inputs>`)
- [ ] Remove CDATA wrapping complexity
- [ ] Test with sample directives
- [ ] Update existing directives to new format (hard-cut migration)

---

## Phase 1: Expression Evaluator (Days 3-4)

**Output:** `.ai/tools/threads/expression_evaluator.py`

### 1.1 Safe Expression Grammar

Support only (non-Turing-complete):

```
expression  := or_expr
or_expr     := and_expr ("or" and_expr)*
and_expr    := not_expr ("and" not_expr)*
not_expr    := "not" not_expr | comparison
comparison  := additive (comp_op additive)?
comp_op     := "==" | "!=" | "<" | ">" | "<=" | ">=" | "in" | "not in"
additive    := term (("+"|"-") term)*
term        := factor (("*"|"/") factor)*
factor      := literal | path | "(" expression ")"
path        := IDENT ("." IDENT)*
literal     := NUMBER | STRING | "true" | "false" | "null"
```

**Supported:**
- Comparison: `>`, `<`, `==`, `!=`, `>=`, `<=`
- Logical: `and`, `or`, `not`
- Membership: `in`, `not in`
- Arithmetic: `+`, `-`, `*`, `/`
- Property access: `event.code`, `limits.turns`

**NOT supported (security):**
- Function calls
- Method access
- Imports

### 1.2 Core Functions

```python
def evaluate_expression(expr: str, context: Dict) -> bool:
    """Safely evaluate expression against context."""

def resolve_path(path: str, context: Dict) -> Any:
    """Resolve dotted path like 'event.detail.missing' from context."""

def substitute_templates(obj: Any, context: Dict) -> Any:
    """Replace ${path.to.value} with values from context."""
```

### 1.3 Expression Examples

```python
# Permission checks
"event.code == \"permission_denied\""
"\"fs.write\" in permissions.required"

# Cost checks
"cost.turns > limits.turns"
"cost.turns > limits.turns * 0.9"  # 90% warning
"cost.spawns >= limits.spawns"

# Error handling
"event.name == \"error\" and event.code == \"timeout\""

# Complex conditions
"event.name == \"error\" and (event.code == \"permission_denied\" or event.code == \"quota_exceeded\")"
```

### 1.4 Tasks

- [ ] Implement tokenizer
- [ ] Implement AST parser
- [ ] Implement evaluator with path resolution
- [ ] Implement template substitution
- [ ] Add comprehensive tests
- [ ] Document supported syntax

---

## Phase 2: Safety Harness Tool (Days 5-8)

**Output:** `.ai/tools/threads/safety_harness.py`

### 2.1 Cost Tracking Architecture

The harness tracks cost throughout thread lifetime. Data flows from LLM API responses through the thread tools.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LLM API Response                                 │
│                                                                         │
│  OpenAI:                          Anthropic:                            │
│  {                                {                                     │
│    "usage": {                       "usage": {                          │
│      "prompt_tokens": 150,            "input_tokens": 150,              │
│      "completion_tokens": 50,         "output_tokens": 50               │
│      "total_tokens": 200              // no total field                 │
│    }                                }                                   │
│  }                                }                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    openai_thread / anthropic_thread                      │
│                                                                         │
│  After each turn, extract usage from response and pass to harness:      │
│  {                                                                      │
│    "turn_usage": {                                                      │
│      "input_tokens": 150,                                               │
│      "output_tokens": 50,                                               │
│      "total_tokens": 200    // calculated if not provided               │
│    }                                                                    │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          SafetyHarness                                   │
│                                                                         │
│  self.cost = {                                                          │
│    "turns": 5,                    # Incremented each turn               │
│    "tokens": 3500,                # Accumulated from turn_usage         │
│    "spawns": 2,                   # Incremented on spawn_thread         │
│    "duration_seconds": 120,       # time.time() - start_time            │
│    "spend": 0.035                 # Calculated from tokens + pricing    │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        thread_registry                                   │
│                                                                         │
│  Persists cost to SQLite:                                               │
│  - total_usage_json: current accumulated cost                           │
│  - cost_budget_json: limits from directive                              │
│  - Events logged for audit trail                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Handling Missing Usage Data

LLM APIs may not always return usage data (streaming, errors, rate limits). The harness must handle this gracefully:

```python
def _extract_usage(self, llm_response: Dict) -> Dict[str, int]:
    """
    Extract token usage from LLM response.
    Handles differences between OpenAI and Anthropic formats.
    Falls back to estimation if data unavailable.
    """
    usage = llm_response.get("usage", {})
    
    # OpenAI format
    if "total_tokens" in usage:
        return {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage["total_tokens"],
        }
    
    # Anthropic format (no total)
    if "input_tokens" in usage or "output_tokens" in usage:
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
    
    # No usage data - estimate from content length
    # ~4 chars per token for English text
    content = llm_response.get("content", "")
    if isinstance(content, list):
        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    estimated_output = len(str(content)) // 4
    
    return {
        "input_tokens": 0,  # Unknown
        "output_tokens": estimated_output,
        "total_tokens": estimated_output,
        "estimated": True,  # Flag that this is estimated
    }
```

### 2.3 Spend Calculation

Spend is calculated from tokens using a pricing table (data-driven):

```python
# .ai/tools/llm/pricing.yaml (data-driven pricing)
models:
  gpt-4o:
    input_per_million: 2.50
    output_per_million: 10.00
  gpt-4o-mini:
    input_per_million: 0.15
    output_per_million: 0.60
  claude-sonnet-4-20250514:
    input_per_million: 3.00
    output_per_million: 15.00
  # ... more models

def _calculate_spend(self, usage: Dict, model: str) -> float:
    """Calculate spend from token usage and model pricing."""
    pricing = self._load_pricing(model)
    if not pricing:
        return 0.0  # Unknown model, can't calculate
    
    input_cost = (usage.get("input_tokens", 0) / 1_000_000) * pricing["input_per_million"]
    output_cost = (usage.get("output_tokens", 0) / 1_000_000) * pricing["output_per_million"]
    
    return input_cost + output_cost
```

### 2.4 Cost Accumulation

```python
class SafetyHarness:
    def __init__(self, project_path: Path, parent_token: Optional[CapabilityToken] = None):
        self.project_path = project_path
        self.parent_token = parent_token
        self.start_time = time.time()
        
        # Initialize cost tracking
        self.cost = {
            "turns": 0,
            "tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "spawns": 0,
            "duration_seconds": 0,
            "spend": 0.0,
        }
    
    def _update_cost_after_turn(self, llm_response: Dict, model: str) -> None:
        """Update cost tracking after each LLM turn."""
        self.cost["turns"] += 1
        self.cost["duration_seconds"] = time.time() - self.start_time
        
        # Extract and accumulate token usage
        usage = self._extract_usage(llm_response)
        self.cost["tokens"] += usage.get("total_tokens", 0)
        self.cost["input_tokens"] += usage.get("input_tokens", 0)
        self.cost["output_tokens"] += usage.get("output_tokens", 0)
        
        # Calculate and accumulate spend
        turn_spend = self._calculate_spend(usage, model)
        self.cost["spend"] += turn_spend
        
        # Persist to registry
        await self._persist_usage()
    
    def _increment_spawn_count(self) -> None:
        """Called when spawning a child thread."""
        self.cost["spawns"] += 1
    
    async def _persist_usage(self) -> None:
        """Persist current usage to thread registry."""
        await thread_registry.execute(
            action="update_status",
            thread_id=self.thread_id,
            status="running",
            metadata={"usage": self.cost}
        )
```

### 2.5 Child Thread Cost Handling

Child threads have independent budgets (from their directive's `<limits>`), but parent can track total spawn count:

```python
async def _spawn_child_thread(self, directive_name: str, inputs: Dict) -> Dict:
    """Spawn a child thread with its own harness."""
    
    # Increment parent's spawn count
    self._increment_spawn_count()
    
    # Check spawn limit BEFORE spawning
    if self.cost["spawns"] > self.limits["spawns"]:
        self.context["event"] = {
            "name": "limit",
            "code": "spawns_exceeded",
            "current": self.cost["spawns"],
            "max": self.limits["spawns"]
        }
        return await self._evaluate_hooks(self.hooks, self.context)
    
    # Child gets its own harness with attenuated token
    child_harness = SafetyHarness(
        project_path=self.project_path,
        parent_token=self._attenuate_token(),
    )
    
    # Child tracks its own cost independently
    return await child_harness.execute_directive(directive_name, inputs, ...)
```

### 2.7 Event Context Structure

At each checkpoint, harness builds:

```python
context = {
    "event": {
        "name": "error",
        "code": "permission_denied",
        "detail": {"missing": "fs.write"}
    },
    "directive": {
        "name": "deploy_staging",
        "inputs": {...}
    },
    "cost": {
        # Runtime tracking
        "turns": 5,
        "spawns": 2,
        "duration_seconds": 120,
        "tokens": 3500
    },
    "limits": {
        # From <limits> tag
        "turns": 10,
        "tokens": 5000,
        "spawns": 3,
        "duration": 300,
        "spend": 10.00,
        "spend_currency": "USD"
    },
    "permissions": {
        "granted": ["fs.read", "tool.bash"],
        "required": ["fs.read", "fs.write"]
    }
}
```

### 2.8 Checkpoints (Hardcoded Control Flow)

| Checkpoint     | When It Runs                     | Event Set                                              |
| -------------- | -------------------------------- | ------------------------------------------------------ |
| `before_step`  | Before executing a tool/step     | `{name: "before_step", step: "..."}`                   |
| `after_step`   | After successful step            | `{name: "after_step", step: "...", result: {...}}`     |
| `on_error`     | After any error                  | `{name: "error", code: "...", detail: {...}}`          |
| `on_limit`     | When limit about to be exceeded  | `{name: "limit", code: "turns", current: 10, max: 10}` |

### 2.9 Enforcement (Hardcoded)

Harness always checks these limits:
- `cost.turns >= limits.turns` → emit `{code: "turns_exceeded"}`
- `cost.tokens >= limits.tokens` → emit `{code: "tokens_exceeded"}`
- `cost.spawns >= limits.spawns` → emit `{code: "spawns_exceeded"}`
- `cost.duration >= limits.duration` → emit `{code: "duration_exceeded"}`
- Permission check fails → emit `{code: "permission_denied"}`

### 2.10 Hook Evaluation (Data-Driven)

```python
async def _evaluate_hooks(self, hooks: List[Dict], context: Dict) -> HarnessResult:
    """Evaluate all hooks against context. First match wins."""
    for hook in hooks:
        if evaluate_expression(hook["when"], context):
            return await self._execute_hook(hook, context)
    return HarnessResult(action="continue")
```

### 2.11 Hook Actions

Hook directives return actions:

| Action     | Behavior                           |
| ---------- | ---------------------------------- |
| `retry`    | Re-execute the original directive  |
| `continue` | Proceed despite the condition      |
| `skip`     | Skip current step, continue        |
| `fail`     | Return error to caller             |
| `abort`    | Terminate entire execution tree    |

### 2.12 Tasks

- [ ] Create `SafetyHarness` class
- [ ] Implement cost tracking (`turns`, `tokens`, `spawns`, `duration`, `spend`)
- [ ] Implement `_extract_usage()` with OpenAI/Anthropic format handling
- [ ] Implement `_calculate_spend()` with data-driven pricing table
- [ ] Create `.ai/tools/llm/pricing.yaml` pricing data
- [ ] Handle missing usage data (estimation fallback)
- [ ] Implement context building with event structure
- [ ] Implement hardcoded limit enforcement
- [ ] Implement checkpoint-based hook evaluation
- [ ] Implement hook directive execution
- [ ] Implement action handling
- [ ] Wire to spawn_thread, thread_registry, inject_message tools
- [ ] Persist usage to thread_registry after each turn
- [ ] Add tests for cost tracking
- [ ] Add tests for missing usage data handling

---

### 2.13 Model Pricing Data

Create `.ai/tools/llm/pricing.yaml` for spend calculation:

```yaml
# .ai/tools/llm/pricing.yaml
# Model pricing per million tokens (USD)
# Updated: 2026-01-28

models:
  # OpenAI
  gpt-4o:
    input_per_million: 2.50
    output_per_million: 10.00
  gpt-4o-mini:
    input_per_million: 0.15
    output_per_million: 0.60
  gpt-4:
    input_per_million: 30.00
    output_per_million: 60.00
  gpt-3.5-turbo:
    input_per_million: 0.50
    output_per_million: 1.50
  
  # Anthropic
  claude-sonnet-4-20250514:
    input_per_million: 3.00
    output_per_million: 15.00
  claude-3-5-sonnet-20241022:
    input_per_million: 3.00
    output_per_million: 15.00
  claude-3-opus-20240229:
    input_per_million: 15.00
    output_per_million: 75.00
  claude-3-haiku-20240307:
    input_per_million: 0.25
    output_per_million: 1.25

# Default for unknown models (conservative estimate)
default:
  input_per_million: 5.00
  output_per_million: 15.00
```

This keeps pricing **data-driven** - update the YAML when prices change, no code changes needed.

---

## Phase 3: thread_directive Tool (Days 9-10)

**Output:** `.ai/tools/threads/thread_directive.py`

### 3.1 User-Facing Tool

```python
async def execute(
    directive_name: str,
    inputs: Optional[Dict] = None,
    **params
) -> Dict:
    """Spawn a thread and execute a directive with harness enforcement."""
    
    # Load directive
    directive = await _load_directive(directive_name, project_path)
    
    # Create harness
    harness = SafetyHarness(
        project_path=project_path,
        parent_token=params.get("_token"),
    )
    
    # Execute with full enforcement
    result = await harness.execute_directive(
        directive_name=directive_name,
        inputs=inputs or {},
        hooks=directive["metadata"].get("hooks", []),
        limits=directive["metadata"]["limits"],
        model_config=directive["metadata"]["model"],
    )
    
    return result.to_dict()
```

### 3.2 YAML Sidecar

```yaml
tool_id: thread_directive
tool_type: python
version: "1.0.0"
executor_id: python_runtime
description: "Spawn a thread and execute a directive with harness enforcement"

requires:
  - spawn.thread
  - kiwi-mcp.execute

parameters:
  - name: directive_name
    type: string
    required: true
  - name: inputs
    type: object
    required: false
```

### 3.3 Tasks

- [ ] Create tool Python file
- [ ] Create YAML sidecar
- [ ] Wire to SafetyHarness
- [ ] Add tests

---

## Phase 4: Hook Directives (Days 11-12)

**Output:** `.ai/directives/hooks/`

### 4.1 Example Hook Directives

Create standard hook directives:

```
.ai/directives/hooks/
├── request_elevated_permissions.md
├── handle_turns_exceeded.md
├── handle_tokens_exceeded.md
├── handle_timeout.md
└── warn_approaching_limit.md
```

### 4.2 Example: request_elevated_permissions

```xml
<directive name="request_elevated_permissions" version="1.0.0">
  <metadata>
    <description>Request elevated permissions when access is denied</description>
    <category>hooks</category>
    <author>system</author>
    
    <model tier="fast">
      Simple user interaction for permission request
    </model>
    
    <limits>
      <turns>5</turns>
      <tokens>5000</tokens>
      <spawns>0</spawns>
      <duration>60</duration>
      <spend currency="USD">0.10</spend>
    </limits>
    
    <permissions>
      <!-- Minimal permissions -->
    </permissions>
  </metadata>

  <inputs>
    <original_directive type="string" required="true" />
    <missing_cap type="string" required="true" />
  </inputs>

  <outputs>
    <action type="string">retry|fail</action>
  </outputs>

  <process>
    <step name="request_permission">
      Ask the user for permission to use capability: ${missing_cap}
      
      If granted, return: {"action": "retry"}
      If denied, return: {"action": "fail", "error": "Permission denied by user"}
    </step>
  </process>
</directive>
```

### 4.3 Tasks

- [ ] Create request_elevated_permissions.md
- [ ] Create handle_turns_exceeded.md
- [ ] Create handle_tokens_exceeded.md
- [ ] Create handle_timeout.md
- [ ] Create warn_approaching_limit.md
- [ ] Sign all directives

---

## Phase 5: Integration & Tests (Days 13-15)

### 5.1 Test Cases

```python
# tests/harness/test_safety_harness.py

async def test_permission_denied_triggers_hook():
    """event.code == 'permission_denied' → hook matches → directive runs."""

async def test_turns_exceeded_triggers_hook():
    """cost.turns > limits.turns → hook matches."""

async def test_first_hook_wins():
    """Multiple hooks match → only first executes."""

async def test_no_hook_matches_continues():
    """No hook expression matches → default continue."""

async def test_hook_returns_retry():
    """Hook returns {action: "retry"} → re-execute directive."""

async def test_hook_returns_abort():
    """Hook returns {action: "abort"} → terminate execution tree."""

async def test_template_substitution():
    """${directive.name}, ${event.detail.missing} replaced correctly."""

async def test_arithmetic_expression():
    """cost.turns > limits.turns * 0.9 evaluates correctly."""

async def test_recursive_harness():
    """Hook directive spawns child → child has own harness."""
```

### 5.2 Tasks

- [ ] Write expression evaluator tests in `tests/harness/test_expression_evaluator.py`
- [ ] Write harness unit tests in `tests/harness/test_safety_harness.py`
- [ ] Write integration tests for full hook flow
- [ ] Test full flow end-to-end
- [ ] Update existing directives to new format
- [ ] Document usage patterns

---

## File Structure (Final)

```
kiwi_mcp/                       # KERNEL (unchanged philosophy)
├── utils/
│   └── parsers.py              # UNCHANGED - thin wrapper delegates to SchemaExtractor
├── primitives/                 # Unchanged
├── handlers/                   # Unchanged
└── ...

.ai/parsers/                    # DATA-DRIVEN PARSERS
└── markdown_xml.py             # UPDATE: <limits>, <hooks> extraction logic

.ai/extractors/directive/       # DATA-DRIVEN EXTRACTORS
└── markdown_xml.py             # UPDATE: Rename cost→limits, add hooks field

.ai/tools/llm/                  # LLM TOOLS + CONFIG
├── openai_chat.yaml            # Existing
├── anthropic_messages.yaml     # Existing
└── pricing.yaml                # NEW: Model pricing data

.ai/tools/threads/              # HARNESS + THREAD TOOLS
├── expression_evaluator.py     # NEW: Safe expression eval
├── safety_harness.py           # NEW: SafetyHarness class
├── thread_directive.py         # NEW: User-facing tool
├── thread_directive.yaml       # NEW: Tool sidecar
├── spawn_thread.py             # Existing
├── thread_registry.py          # Existing
├── inject_message.py           # Existing
├── openai_thread.yaml          # Existing
├── anthropic_thread.yaml       # Existing
├── pause_thread.py             # Existing
└── resume_thread.py            # Existing

.ai/directives/hooks/           # NEW: Hook directives
├── request_elevated_permissions.md
├── handle_turns_exceeded.md
├── handle_tokens_exceeded.md
├── handle_timeout.md
└── warn_approaching_limit.md
```

---

## Success Criteria

### Parser (Phase 0) ✅ COMPLETE
- [x] `<limits>` tag extracts correctly
- [x] `<model>` tag extracts with `fallback_id`
- [x] `<hooks>` tag extracts with `when`, `directive`, `inputs`
- [ ] All existing directives updated to new format (DEFERRED)
- [x] Parser tests pass

### Expression Evaluator (Phase 1) ✅ COMPLETE
- [x] All operators work: `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `not in`, `and`, `or`, `not`
- [x] Arithmetic works: `+`, `-`, `*`, `/`
- [x] Path resolution works: `event.code`, `limits.turns`
- [x] Template substitution works: `${directive.name}`
- [x] Security: no function calls, no imports

### Safety Harness (Phases 2-3) ✅ COMPLETE
- [x] Context built correctly at each checkpoint
- [x] Hardcoded enforcement triggers correct events
- [x] Hook expressions evaluated correctly
- [x] First matching hook executes
- [x] Hook actions handled correctly
- [x] Recursive harness works for hook directives

### Integration (Phases 4-5) ✅ COMPLETE
- [x] Hook directives created (not signed - signing deferred)
- [x] End-to-end flow works
- [x] All tests pass (102 tests)
- [x] Documentation complete

---

## Dependencies

```
Phase 0 (Parser) ─────┬────► Phase 1 (Expression Evaluator)
                      │
                      └────► Phase 2 (Safety Harness) ────► Phase 3 (thread_directive)
                                                                      │
                                                                      ▼
                                                          Phase 4 (Hook Directives)
                                                                      │
                                                                      ▼
                                                          Phase 5 (Integration)
```

**Critical path:** Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 5

Phase 4 (Hook Directives) can be done in parallel with Phase 3.
