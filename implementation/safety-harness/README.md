# Safety Harness Implementation Plan

**Source Documents:**

- `.ai/tmp/harness_and_execution_model.md` - Execution model
- `.ai/tmp/parser_first_principles.md` - Cost/permission structure

**Status:** Planning  
**Estimated Time:** 2-3 weeks

---

## Core Principle: Fully Data-Driven Hooks

Following the existing kernel pattern:

- **Primitives** (subprocess, http_client) = only code that executes
- **Everything else** = data/config that gets extracted and passed to primitives
- **Harness** = a tool that wraps thread execution with enforcement
- **Hooks** = expressions evaluated against a generic `event` context, NOT hardcoded trigger types

### Why Expression-Based Hooks?

The previous design used named trigger tags (`<on_permission_denied>`, `<on_cost_exceeded>`). This smuggles in an implicit enum—the harness must know when to emit each trigger name.

**Expression-based hooks are fully data-driven:**

1. Harness builds a generic `event` context at each checkpoint
2. Hooks define `<when>` expressions evaluated against that context
3. First matching hook executes
4. **No hardcoded trigger taxonomy**—new conditions = new expressions, not new code

---

## Architecture (Expression-Based Hooks)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Directive Metadata                           │
│  <hooks>                                                        │
│    <hook>                                                       │
│      <when>event.code == "permission_denied"</when>             │
│      <directive>request_elevated_permissions</directive>        │
│      <inputs>                                                   │
│        <original_directive>${directive.name}</original_directive>│
│      </inputs>                                                  │
│    </hook>                                                      │
│    <hook>                                                       │
│      <when>cost.turns > limits.turns</when>                     │
│      <directive>handle_cost_exceeded</directive>                │
│    </hook>                                                      │
│  </hooks>                                                       │
│                                                                 │
│  (No named trigger types - expressions match against context)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Parser extracts
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Extracted Hook Data                          │
│  [                                                              │
│    {                                                            │
│      "when": "event.code == \"permission_denied\"",             │
│      "directive": "request_elevated_permissions",               │
│      "inputs": {"original_directive": "${directive.name}"}      │
│    },                                                           │
│    {                                                            │
│      "when": "cost.turns > limits.turns",                       │
│      "directive": "handle_cost_exceeded"                        │
│    }                                                            │
│  ]                                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Harness evaluates at checkpoints
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              SafetyHarness Tool                                 │
│                                                                 │
│  At each checkpoint (before_step, after_step, on_error):        │
│  1. Build context: {event, cost, limits, directive, ...}        │
│  2. For each hook: evaluate "when" expression against context   │
│  3. First match: substitute templates, execute hook directive   │
│  4. Read action from directive output: {action: "retry"}        │
│  5. Do what the directive says                                  │
│                                                                 │
│  (Harness is a TOOL, not a kernel primitive)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions (Locked In)

| Decision               | Answer                                                              |
| ---------------------- | ------------------------------------------------------------------- |
| Hook matching          | **Expression-based.** `<when>` expressions, NOT named trigger tags  |
| Hook execution         | **Directives only.** Hooks execute directives, nothing else         |
| Hook actions           | **Returned by directive.** No `on_success`/`on_failure` in metadata |
| Expression eval        | Simple operators only. Evaluated against context dict               |
| Event structure        | Generic `{name, code, detail}` - no hardcoded event taxonomy        |
| Cost limits            | From `<limits>` tag: `turns`, `tokens`, `spawns`, `duration`, `spend` |
| First match wins       | Stop at first triggered hook, don't run multiple                    |
| Missing hook directive | Fail with error (directive must exist)                              |
| Template substitution  | `${path.to.value}` replaced from context. Missing = leave as-is     |
| Checkpoints            | Fixed control-flow points, not semantic triggers                    |

### Checkpoints vs Triggers

The harness evaluates hooks at **checkpoints** (control-flow points), not at semantic trigger events:

| Checkpoint    | When It Runs                     | Example `event` Value                                       |
| ------------- | -------------------------------- | ----------------------------------------------------------- |
| `before_step` | Before executing a tool/step     | `{name: "before_step", step: "deploy"}`                     |
| `after_step`  | After successful step completion | `{name: "after_step", step: "deploy", result: {...}}`       |
| `on_error`    | After any error occurs           | `{name: "error", code: "permission_denied", detail: {...}}` |
| `on_limit`    | When a limit is about to be hit  | `{name: "limit", code: "turns", current: 10, max: 10}`      |

**Key insight:** Checkpoints are control-flow (where evaluation happens). Events are data values (what gets evaluated). This keeps the harness simple while allowing arbitrary hook logic.

### Event Context Structure

At each checkpoint, the harness builds this context:

```python
context = {
    "event": {
        "name": "error",           # Checkpoint that triggered
        "code": "permission_denied",  # Specific error/limit code
        "detail": {                # Error-specific details
            "missing": "fs.write",
            "attempted": "filesystem_mcp.write_file"
        }
    },
    "directive": {
        "name": "deploy_staging",
        "inputs": {...}
    },
    "cost": {
        # CURRENT USAGE (tracked by harness at runtime)
        "turns": 5,
        "spawns": 2,
        "duration_seconds": 120,
        "tokens": 3500
    },
    "limits": {
        # FROM METADATA (static, extracted from <limits> tag)
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

Hooks can match on any part of this context using expressions.

### Mapping `<limits>` Metadata to Context

The `<limits>` tag in directive metadata maps directly to context:

```xml
<limits>
  <turns>10</turns>
  <tokens>5000</tokens>
  <spawns>3</spawns>
  <duration>300</duration>
  <spend currency="USD">10.00</spend>
</limits>
```

Maps to context as:

| XML Element                          | Context Path             | Purpose                     |
| ------------------------------------ | ------------------------ | --------------------------- |
| `<turns>10</turns>`                  | `limits.turns`           | Max turns allowed           |
| `<tokens>5000</tokens>`              | `limits.tokens`          | Max tokens allowed          |
| `<spawns>3</spawns>`                 | `limits.spawns`          | Max spawns allowed          |
| `<duration>300</duration>`           | `limits.duration`        | Max seconds allowed         |
| `<spend currency="USD">10.00</spend>`| `limits.spend`           | Max spend allowed           |
| `<spend currency="...">`             | `limits.spend_currency`  | Currency for spend limit    |

The `cost` object (current usage) is tracked by the harness at runtime, not extracted from metadata.

**Key distinction:**
- `limits.*` = static values from directive metadata (what you're allowed)
- `cost.*` = dynamic values tracked during execution (what you've used)

### Hooks Execute Directives Only

Simplified hook model:

- Hooks call **directives only** - no arbitrary MCP tool exposure
- Metadata uses `<directive>name</directive>` with optional `<inputs>`
- **No hardcoded actions** in hook metadata
- Hook directives can do whatever they need internally (call tools, etc.)

### Hook Directives Return Actions

The hook directive determines what happens next via its **output**:

```xml
<!-- Hook directive outputs -->
<outputs>
  <action>retry|continue|skip|fail|abort</action>
  <context>Optional context passed back to harness</context>
</outputs>
```

**Flow:**

1. Expression matches → harness executes hook directive
2. Hook directive runs, returns `{action: "retry", context: {...}}`
3. Harness reads action from output, does what directive says

**Valid actions:**

- `retry` - re-execute the original directive
- `continue` - proceed despite the condition
- `skip` - skip current step, continue workflow
- `fail` - return error to caller
- `abort` - terminate entire execution tree

This keeps actions **fully data-driven** - the directive decides, not hardcoded metadata.

---

## Kernel vs Harness Separation

**CRITICAL: The kernel knows NOTHING about threads.**

```
┌─────────────────────────────────────┐
│     LLM Runtime (Amp, Cursor, etc.) │
│  - Has MCP attached                 │
│  - Instantiates SafetyHarness       │
└─────────────────────────────────────┘
           │
           │ Harness wraps LLM execution
           ▼
┌─────────────────────────────────────┐
│          SafetyHarness TOOL         │  ← .ai/tools/threads/safety_harness.py
│  - Calls spawn_thread (tool)        │
│  - Calls thread_registry (tool)     │
│  - Calls inject_message (tool)      │
│  - Calls MCP execute (via tool call)│
│  - Evaluates hook expressions       │
│  - NOT in kiwi_mcp/                 │
└─────────────────────────────────────┘
           │
           │ Makes MCP tool calls
           ▼
┌─────────────────────────────────────┐
│          KERNEL (Dumb)              │  ← kiwi_mcp/
│  - Just returns JSON                │
│  - No thread knowledge              │
│  - No harness knowledge             │
└─────────────────────────────────────┘
```

**Kernel primitives** (subprocess, http_client) = execution code for tools
**Harness** = a tool that orchestrates other tools, lives in `.ai/tools/`

---

## Phase 1: Hook Extraction (Days 1-2)

**Output:** Update `.ai/parsers/markdown_xml.py` to extract expression-based hooks

### Current Parser Architecture

Parsing is data-driven via:

1. **Parser** (`.ai/parsers/markdown_xml.py`) - parses file, returns structured dict
2. **Extractor** (`.ai/extractors/directive/markdown_xml.py`) - defines extraction rules
3. **SchemaExtractor** (`kiwi_mcp/schemas/tool_schema.py`) - orchestrates

We add hook extraction to the **parser**, not the kernel.

### 1.1 Update markdown_xml.py parser

Add hook extraction inside the `metadata` processing block:

```python
# In .ai/parsers/markdown_xml.py, inside the metadata processing loop

elif meta_tag == "hooks":
    hooks = []
    for hook_elem in meta_child:
        if hook_elem.tag != "hook":
            raise ValueError(f"Expected <hook> inside <hooks>, got <{hook_elem.tag}>")

        # Required: when expression
        when_elem = hook_elem.find("when")
        if when_elem is None or not when_elem.text:
            raise ValueError("Hook missing required <when> element")

        # Required: directive to execute
        directive_elem = hook_elem.find("directive")
        if directive_elem is None or not directive_elem.text:
            raise ValueError("Hook missing required <directive> element")

        hook = {
            "when": when_elem.text.strip(),
            "directive": directive_elem.text.strip(),
        }

        # Optional: inputs (template variables like ${directive.name})
        inputs_elem = hook_elem.find("inputs")
        if inputs_elem is not None:
            hook["inputs"] = _xml_to_dict(inputs_elem)

        hooks.append(hook)
    result["hooks"] = hooks
```

### 1.2 Update extractor to include hooks field

Add to `.ai/extractors/directive/markdown_xml.py`:

```python
EXTRACTION_RULES = {
    # ... existing rules ...
    "hooks": {"type": "path", "key": "hooks"},  # NEW
}
```

### 1.3 Result structure

After parsing, hooks are available at:

```python
parsed["hooks"]  # List of hook definitions
# [
#   {
#     "when": "event.code == \"permission_denied\"",
#     "directive": "request_elevated_permissions",
#     "inputs": {"original_directive": "${directive.name}"}
#   },
#   {
#     "when": "cost.turns > limits.turns",
#     "directive": "handle_cost_exceeded"
#   }
# ]
```

### 1.4 Example directive with hooks

```xml
<directive name="deploy_staging" version="1.0.0">
  <metadata>
    <description>Deploy to staging environment</description>
    <category>deployment</category>
    <author>devops</author>
    
    <model tier="balanced" fallback_id="gpt-4o-mini">
      Deployment orchestration with shell commands
    </model>
    
    <limits>
      <turns>20</turns>
      <tokens>50000</tokens>
      <spawns>3</spawns>
      <duration>600</duration>
      <spend currency="USD">5.00</spend>
    </limits>
    
    <permissions>
      <read resource="filesystem" path="src/**" />
      <write resource="filesystem" path="dist/**" />
      <execute resource="tool" id="bash" />
    </permissions>
    
    <hooks>
      <hook>
        <when>event.code == "permission_denied"</when>
        <directive>request_elevated_permissions</directive>
        <inputs>
          <original_directive>${directive.name}</original_directive>
          <missing_cap>${event.detail.missing}</missing_cap>
        </inputs>
      </hook>
      <hook>
        <when>cost.turns > limits.turns * 0.9</when>
        <directive>warn_approaching_limit</directive>
      </hook>
      <hook>
        <when>event.name == "error" and event.code == "timeout"</when>
        <directive>handle_timeout</directive>
      </hook>
    </hooks>
  </metadata>
  ...
</directive>
```

### Tasks:

- [ ] Update `.ai/parsers/markdown_xml.py` to extract `<hooks>` with expression-based `<when>`
- [ ] Validate `<when>` and `<directive>` are present (required)
- [ ] Extract optional `<inputs>`
- [ ] Update `.ai/extractors/directive/markdown_xml.py` to include hooks field
- [ ] Add tests for hook extraction

---

## Phase 2: Expression Evaluator (Days 3-4)

**Output:** `.ai/tools/threads/expression_evaluator.py`

### 2.1 Safe expression evaluator

Support only (non-Turing-complete):

- Comparison: `>`, `<`, `==`, `!=`, `>=`, `<=`
- Logical: `and`, `or`, `not`
- Membership: `in`, `not in`
- Arithmetic: `+`, `-`, `*`, `/` (for limit calculations)
- Literals: numbers, strings, booleans
- Property access: `event.code`, `cost.turns`, `limits.turns`
- Variables: identifiers resolved from context

**NOT supported** (security):

- Function calls
- Attribute access to methods
- Imports
- Arbitrary Python execution

```python
# .ai/tools/threads/expression_evaluator.py

def evaluate_expression(expr: str, context: Dict) -> bool:
    """
    Safely evaluate expression against context.

    Examples:
        evaluate_expression("cost.turns > limits.turns", context)  # True/False
        evaluate_expression("event.code == \"permission_denied\"", context)
        evaluate_expression("\"fs.write\" in permissions.required", context)
    """
    tokens = tokenize(expr)
    ast = parse_expression(tokens)
    return evaluate_ast(ast, context)


def resolve_path(path: str, context: Dict) -> Any:
    """
    Resolve dotted path like 'event.detail.missing' from context.

    Returns None if path doesn't exist (rather than raising).
    """
    parts = path.split(".")
    value = context
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
        if value is None:
            return None
    return value
```

### 2.2 Template substitution

```python
def substitute_templates(obj: Any, context: Dict) -> Any:
    """
    Replace ${path.to.value} with values from context.

    Handles:
    - Strings: "${directive.name}" → "deploy_staging"
    - Nested dicts: recursively substitute
    - Lists: substitute each element
    - Missing: leave ${...} as-is
    """
```

### 2.3 Expression grammar

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

### Tasks:

- [ ] Implement tokenizer for safe expressions
- [ ] Implement AST parser (only allowed operators)
- [ ] Implement evaluator with path resolution
- [ ] Implement template substitution
- [ ] Add comprehensive tests
- [ ] Document supported syntax

---

## Phase 3: Safety Harness Tool (Days 5-8)

**Output:** `.ai/tools/threads/safety_harness.py`

### Key Principle: Harness is a TOOL, NOT a Kernel Primitive

The kernel is dumb. It knows nothing about threads. The harness:

- Lives in `.ai/tools/threads/` (NOT in `kiwi_mcp/`)
- Uses other tools: `spawn_thread`, `thread_registry`, `inject_message`
- Calls MCP via standard tool interface
- Is instantiated by the LLM runtime, not the kernel

### 3.1 SafetyHarness class

```python
# .ai/tools/threads/safety_harness.py

__tool_type__ = "python"
__version__ = "1.0.0"
__executor_id__ = "python_runtime"
__category__ = "threads"

"""
Safety Harness: Wraps directive execution with enforcement.

This is a TOOL that orchestrates other tools. It:
- Calls spawn_thread, thread_registry, inject_message (other tools)
- Calls MCP via tool interface
- Evaluates hook expressions at checkpoints
- Is NOT part of the kernel
"""

from expression_evaluator import evaluate_expression, substitute_templates

class SafetyHarness:
    """
    Wraps directive execution with permission, cost, and hook enforcement.
    Uses expression-based hooks evaluated at checkpoints.
    """

    # Checkpoints where hooks are evaluated (control-flow points, not semantic events)
    CHECKPOINTS = ["before_step", "after_step", "on_error", "on_limit"]

    def __init__(self, project_path: Path, parent_token: Optional[CapabilityToken] = None):
        self.project_path = project_path
        self.parent_token = parent_token

    async def execute_directive(
        self,
        directive_name: str,
        inputs: Dict,
        hooks: List[Dict],      # Extracted from directive metadata
        limits: Dict,           # From <limits> tag
        model_config: Dict,     # From <model> tag
    ) -> HarnessResult:
        """Execute directive with full harness enforcement."""

        # 1. Build initial context
        context = self._build_context(directive_name, inputs, limits)

        # 2. Check permissions (using capability token)
        perm_result = self._check_permissions(context)
        if not perm_result.ok:
            # Set event for permission failure
            context["event"] = {
                "name": "error",
                "code": "permission_denied",
                "detail": {
                    "missing": perm_result.missing_caps,
                    "granted": list(self.parent_token.caps) if self.parent_token else []
                }
            }
            return await self._evaluate_hooks(hooks, context)

        # 3. Spawn thread using spawn_thread TOOL
        thread_result = await spawn_thread.execute(
            thread_id=f"{directive_name}_{uuid4().hex[:8]}",
            directive_name=directive_name,
            project_path=str(self.project_path),
        )

        # 4. Inject MCP call + response using inject_message TOOL
        await inject_message.execute(
            thread_id=thread_result["thread_id"],
            role="assistant",
            content=json.dumps({
                "tool_call": "kiwi-mcp",
                "action": "execute",
                "params": {"item_type": "directive", "action": "run", "item_id": directive_name}
            }),
        )
        directive_content = await self._load_directive(directive_name)
        await inject_message.execute(
            thread_id=thread_result["thread_id"],
            role="tool_result",
            content=json.dumps(directive_content),
        )

        # 5. Execute with enforcement loop
        return await self._execute_with_enforcement(
            thread_result["thread_id"], context, hooks, limits
        )

    async def _execute_with_enforcement(self, thread_id, context, hooks, limits):
        """Execute turns with checkpoint-based hook evaluation."""

        while not self._is_thread_complete(thread_id):
            # CHECKPOINT: on_limit - check before each turn
            if context["cost"]["turns"] >= limits["turns"]:
                context["event"] = {
                    "name": "limit",
                    "code": "turns",
                    "current": context["cost"]["turns"],
                    "max": limits["turns"]
                }
                result = await self._evaluate_hooks(hooks, context)
                if result.action != "continue":
                    return result

            if context["cost"]["spawns"] >= limits["spawns"]:
                context["event"] = {
                    "name": "limit",
                    "code": "spawns",
                    "current": context["cost"]["spawns"],
                    "max": limits["spawns"]
                }
                result = await self._evaluate_hooks(hooks, context)
                if result.action != "continue":
                    return result

            # CHECKPOINT: before_step
            context["event"] = {"name": "before_step", "turn": context["cost"]["turns"]}
            result = await self._evaluate_hooks(hooks, context)
            if result.action == "skip":
                continue
            if result.action not in ("continue", None):
                return result

            # Let LLM execute one turn
            await self._wait_for_turn(thread_id)
            context["cost"]["turns"] += 1

            # Check for errors via thread_registry TOOL
            status = await thread_registry.get_status(thread_id)
            if status.get("error"):
                # CHECKPOINT: on_error
                context["event"] = {
                    "name": "error",
                    "code": status["error"].get("code", "unknown"),
                    "detail": status["error"]
                }
                result = await self._evaluate_hooks(hooks, context)
                if result.action != "continue":
                    return result

            # CHECKPOINT: after_step
            context["event"] = {
                "name": "after_step",
                "turn": context["cost"]["turns"],
                "result": status.get("result")
            }
            await self._evaluate_hooks(hooks, context)

        return HarnessResult(success=True, output=self._get_thread_result(thread_id))

    async def _evaluate_hooks(self, hooks: List[Dict], context: Dict) -> HarnessResult:
        """Evaluate all hooks against context. First match wins."""

        for hook in hooks:
            when_expr = hook["when"]

            # Evaluate expression against context
            try:
                if evaluate_expression(when_expr, context):
                    # First match - execute hook directive
                    return await self._execute_hook(hook, context)
            except Exception as e:
                # Expression evaluation error - log and continue
                logger.warning(f"Hook expression error: {when_expr} - {e}")
                continue

        # No hook matched - return continue (default behavior)
        return HarnessResult(action="continue")

    async def _execute_hook(self, hook: Dict, context: Dict) -> HarnessResult:
        """Execute hook directive and read action from its output."""

        # Substitute templates in hook inputs
        hook_directive_name = hook["directive"]
        inputs = substitute_templates(hook.get("inputs", {}), context)

        # Create child harness for hook execution (recursive enforcement)
        child_harness = SafetyHarness(
            project_path=self.project_path,
            parent_token=self._attenuate_token(context),
        )

        # Load hook directive to get its hooks/limits
        hook_directive = await self._load_directive(hook_directive_name)

        # Execute hook directive with child harness
        result = await child_harness.execute_directive(
            directive_name=hook_directive_name,
            inputs=inputs,
            hooks=hook_directive["metadata"].get("hooks", []),
            limits=hook_directive["metadata"]["limits"],
            model_config=hook_directive["metadata"]["model"],
        )

        # Read action from directive output (data-driven)
        action = result.output.get("action", "fail")  # Default to fail if no action
        return self._handle_action(action, context, result)

    def _handle_action(self, action: str, context, result):
        """Handle action returned by hook directive."""
        if action == "retry":
            return HarnessResult(action="retry")
        elif action == "continue":
            return HarnessResult(action="continue", success=True)
        elif action == "skip":
            return HarnessResult(action="skip", success=True)
        elif action == "fail":
            return HarnessResult(success=False, error=result.output.get("error"))
        elif action == "abort":
            raise AbortExecution(result.output.get("error"))
        else:
            # Unknown action - treat as fail
            return HarnessResult(success=False, error=f"Unknown action: {action}")
```

### 3.2 Standardized error envelope

All tools/directives must return errors in this format for consistent hook matching:

```python
# Success
{"ok": True, "output": {...}}

# Error
{"ok": False, "error": {"code": "permission_denied", "detail": {...}}}
```

This allows hooks to match on `event.code` without harness changes for new error types.

### Tasks:

- [x] Create `SafetyHarness` class in `.ai/tools/threads/`
- [x] Implement execution context building with `event` structure
- [x] Implement permission checking using CapabilityToken
- [x] Implement checkpoint-based hook evaluation loop
- [x] Implement expression-based hook matching (first wins)
- [x] Implement hook execution with child harness (recursive)
- [x] Read action from directive output (not hardcoded metadata)
- [x] Wire to use other tools (spawn_thread, thread_registry, inject_message)
- [x] Add tests (102 harness tests passing)

---

## Phase 4: thread_directive Tool (Days 9-10)

**Output:** `.ai/tools/threads/thread_directive.py`

### 4.1 User-facing tool

This is the tool LLMs call to spawn a directive on a new thread. It uses `SafetyHarness` internally.

```python
# .ai/tools/threads/thread_directive.py

__tool_type__ = "python"
__version__ = "1.0.0"
__executor_id__ = "python_runtime"
__category__ = "threads"

"""
Thread Directive Tool: Spawn a thread and execute a directive with harness enforcement.

This tool:
1. Loads the directive to get metadata (hooks, cost, permissions)
2. Creates a SafetyHarness instance
3. Calls harness.execute_directive()
4. Returns the result
"""

from safety_harness import SafetyHarness

async def execute(
    directive_name: str,
    inputs: Optional[Dict] = None,
    **params
) -> Dict:
    """
    Spawn a thread and execute a directive on it.
    """
    project_path = Path(params.get("_project_path", Path.cwd()))

    # Load directive to get hooks, cost, permissions, model
    # (Uses MCP load call internally)
    directive = await _load_directive(directive_name, project_path)

    # Create harness with parent token (if we're in a child thread)
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


async def _load_directive(name: str, project_path: Path) -> Dict:
    """Load directive using MCP (as a tool would)."""
    from kiwi_mcp.handlers.directive.handler import DirectiveHandler
    handler = DirectiveHandler(str(project_path))
    return await handler.load(name, source="project")
```

### 4.2 YAML sidecar

```yaml
# .ai/tools/threads/thread_directive.yaml
tool_id: thread_directive
tool_type: python
version: "1.0.0"
executor_id: python_runtime
description: "Spawn a thread and execute a directive with full harness enforcement"

requires:
  - spawn.thread
  - kiwi-mcp.execute

parameters:
  - name: directive_name
    type: string
    required: true
    description: "Name of the directive to execute"
  - name: inputs
    type: object
    required: false
    description: "Input parameters for the directive"
```

### Tasks:

- [x] Create tool Python file
- [x] Create YAML sidecar
- [x] Wire to SafetyHarness class
- [x] Add tests

---

## Phase 5: Integration & Tests (Days 11-13)

### 5.1 End-to-end tests

```python
# tests/harness/test_thread_harness.py

async def test_permission_denied_triggers_hook():
    """Permission denied → event.code == 'permission_denied' → hook matches → retry."""

async def test_cost_exceeded_triggers_hook():
    """cost.turns > limits.turns → hook matches → handle_cost_exceeded runs."""

async def test_first_hook_wins():
    """Multiple hooks match → only first executes."""

async def test_no_hook_matches():
    """No hook expression matches → default continue behavior."""

async def test_recursive_harness():
    """Hook directive spawns child → child also has harness with own hooks."""

async def test_template_substitution():
    """${directive.name}, ${event.detail.missing} replaced correctly in hook inputs."""

async def test_complex_expression():
    """event.name == 'error' and event.code in ['timeout', 'rate_limit']"""

async def test_arithmetic_in_expression():
    """cost.turns > limits.turns * 0.9 evaluates correctly."""
```

### 5.2 Hook directive examples

Create example hook directives that get called:

```
.ai/directives/hooks/
├── request_elevated_permissions.md
├── handle_cost_exceeded.md
├── handle_timeout.md
├── warn_approaching_limit.md
└── handle_execution_failure.md
```

Each is just a normal directive with its own `<metadata>`, `<inputs>`, `<outputs>`, and content.

### 5.3 Example hook directive

````xml
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
      <!-- Hook directives have minimal permissions -->
    </permissions>
  </metadata>

  <inputs>
    <original_directive type="string" required="true" />
    <missing_cap type="string" required="true" />
  </inputs>

  <outputs>
    <action type="string">retry|fail</action>
    <context type="object" />
  </outputs>

  <process>
    <step name="request_permission">
      Ask the user for permission to use capability: ${missing_cap}

      If granted, return:
      ```json
      {"action": "retry", "context": {"elevated": true}}
      ```

      If denied, return:
      ```json
      {"action": "fail", "error": "Permission denied by user"}
      ```
    </step>
  </process>
</directive>
````

### Tasks:

- [ ] Write integration tests
- [ ] Create example hook directives
- [ ] Test full flow end-to-end
- [ ] Document expression syntax
- [ ] Document hook patterns

---

## File Structure (Final)

```
kiwi_mcp/                 # KERNEL (dumb, no thread knowledge, UNCHANGED)
├── primitives/           # Unchanged
├── handlers/             # Unchanged
├── schemas/              # Unchanged (uses data-driven extractors)
└── utils/                # Unchanged

.ai/parsers/              # DATA-DRIVEN PARSERS
└── markdown_xml.py       # UPDATE: Add expression-based hook extraction

.ai/extractors/directive/ # DATA-DRIVEN EXTRACTORS
└── markdown_xml.py       # UPDATE: Add hooks field

.ai/tools/threads/        # HARNESS + THREAD TOOLS (outside kernel)
├── safety_harness.py     # NEW: SafetyHarness class with checkpoint-based evaluation
├── thread_directive.py   # NEW: User-facing tool
├── thread_directive.yaml # NEW: Tool discovery
├── expression_evaluator.py # NEW: Safe expression eval with path resolution
├── spawn_thread.py       # Existing
├── thread_registry.py    # Existing
├── inject_message.py     # Existing
├── pause_thread.py       # Existing
└── resume_thread.py      # Existing

.ai/directives/hooks/     # NEW: Example hook directives
├── request_elevated_permissions.md
├── handle_cost_exceeded.md
├── handle_timeout.md
├── warn_approaching_limit.md
└── handle_execution_failure.md
```

**Key principles:**

- Kernel (`kiwi_mcp/`) is UNCHANGED - stays dumb
- Hook extraction added to data-driven parser (`.ai/parsers/`)
- Harness is a tool in `.ai/tools/` - uses other tools
- **Hooks are expression-based** - no hardcoded trigger taxonomy

---

## Summary

| Layer                  | What It Does                                   | Code Location                               |
| ---------------------- | ---------------------------------------------- | ------------------------------------------- |
| **Directive metadata** | Defines hooks with `<when>` expressions        | `.ai/directives/*.md`                       |
| **Parser**             | Extracts hooks to JSON (no trigger enum)       | `.ai/parsers/markdown_xml.py`               |
| **Expression eval**    | Safely evaluates expressions against context   | `.ai/tools/threads/expression_evaluator.py` |
| **SafetyHarness tool** | Builds context, evaluates hooks at checkpoints | `.ai/tools/threads/safety_harness.py`       |
| **thread_directive**   | User-facing tool, uses SafetyHarness           | `.ai/tools/threads/thread_directive.py`     |

**Key principles:**

1. **Kernel is dumb** - just extracts and returns JSON, no thread knowledge
2. **Harness is a tool** - lives in `.ai/tools/`, NOT in `kiwi_mcp/`
3. **Hooks are expression-based** - `<when>` expressions, NOT named trigger tags
4. **Events are data** - generic `{name, code, detail}` structure, no hardcoded taxonomy
5. **Checkpoints are control-flow** - fixed points where hooks are evaluated
6. **New conditions = new expressions** - no code changes needed for new hook types
7. **Harness uses other tools** - spawn_thread, thread_registry, inject_message

---

## Appendix: Expression Examples

```python
# Permission checks
"event.code == \"permission_denied\""
"\"fs.write\" in permissions.required"
"event.detail.missing == \"spawn.thread\""

# Cost checks
"cost.turns > limits.turns"
"cost.turns > limits.turns * 0.9"  # 90% warning
"cost.spawns >= limits.spawns"

# Error handling
"event.name == \"error\""
"event.name == \"error\" and event.code == \"timeout\""
"event.code in [\"timeout\", \"rate_limit\", \"network_error\"]"

# Complex conditions
"event.name == \"error\" and (event.code == \"permission_denied\" or event.code == \"quota_exceeded\")"
"cost.turns > 5 and event.name == \"before_step\""
```
