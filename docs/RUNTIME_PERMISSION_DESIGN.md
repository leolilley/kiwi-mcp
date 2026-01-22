# Runtime Permission Enforcement Design

**Date:** 2026-01-22  
**Status:** Approved  
**Author:** Kiwi Team  
**Phase:** 3 (Weeks 5-6)

---

## Executive Summary

Kiwi MCP implements **capability-based security** at the runtime level. Permissions declared in directives are not mere suggestions to the LLM—they are hard-enforced by the proxy layer. If an agent (or subagent) attempts an unauthorized action, it is blocked regardless of what the model "thinks" it should do.

This document covers:
1. Permission declaration syntax
2. Runtime enforcement architecture
3. Permission inheritance in recursion
4. Help tool redesign for agent control signals
5. Loop detection and stuck handling

---

## The Problem

### Why Model-Side Constraints Aren't Enough

LLMs are probabilistic. Even with perfect prompts, they can:
- Hallucinate tool calls that don't exist
- Request actions outside their scope
- Attempt privilege escalation in recursive setups
- Get stuck in loops without recognizing it

**Prompt-based constraints:**
```
System: You can only read files in src/. Do not access other directories.
Agent: I need to read config/secrets.yaml to proceed...
```
The model might still try. Without enforcement, this succeeds.

### The Kiwi Solution: Hard Enforcement

```
Agent: [TOOL: read config/secrets.yaml]
  ↓
KiwiProxy: Permission check against directive <permissions>
  ↓
Directive allows: <read resource="filesystem" path="src/**" />
  ↓
config/secrets.yaml does NOT match src/**
  ↓
DENIED: {"error": "Permission denied: read not allowed on config/secrets.yaml"}
```

The agent receives an error, not the file contents. It must adapt or escalate.

---

## Permission Declaration

### Syntax in Directives

Permissions are declared in the `<permissions>` section within `<metadata>`:

```xml
<directive name="test_feature" version="1.0.0">
  <metadata>
    <description>Run tests for a feature</description>
    <category>testing</category>
    <author>team</author>
    
    <permissions>
      <!-- Filesystem access -->
      <read resource="filesystem" path="src/**" />
      <read resource="filesystem" path="tests/**" />
      <write resource="filesystem" path="tests/output/**" />
      
      <!-- Tool execution -->
      <execute resource="tool" id="pytest" />
      <execute resource="tool" id="coverage" />
      
      <!-- Kiwi MCP meta-tools -->
      <execute resource="kiwi-mcp" action="search" />
      <execute resource="kiwi-mcp" action="load" />
      
      <!-- Shell commands -->
      <execute resource="shell" commands="git,npm" />
      
      <!-- External MCPs -->
      <execute resource="mcp" name="supabase" actions="query" />
      
      <!-- Explicit denials (optional, absence = denied) -->
      <deny resource="network" action="*" />
    </permissions>
  </metadata>
  
  <process>
    <!-- ... -->
  </process>
</directive>
```

### Resource Types

| Resource | Attributes | Description |
|----------|------------|-------------|
| `filesystem` | `path` (glob) | File/directory access |
| `tool` | `id` | Script/tool execution |
| `kiwi-mcp` | `action` | Meta-tool access (search, load, execute, help) |
| `shell` | `commands` | Shell command allowlist |
| `mcp` | `name`, `actions` | External MCP access |
| `network` | `hosts`, `ports` | Network access (future) |

### Glob Pattern Matching

Filesystem paths use glob patterns:

| Pattern | Matches |
|---------|---------|
| `src/**` | All files under src/, recursively |
| `src/*.ts` | TypeScript files directly in src/ |
| `tests/unit/*.py` | Python files in tests/unit/ |
| `**/*.md` | All Markdown files anywhere |

---

## Runtime Enforcement Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Agent (LLM Process)                               │
│  • Generates tool calls (direct or via intent)                      │
│  • Doesn't "know" its permissions at model level                    │
│  • Just requests what it needs                                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    KiwiProxy (Enforcement Layer)                     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  PermissionContext                           │    │
│  │  Loaded from directive <permissions> at spawn time           │    │
│  │                                                               │    │
│  │  filesystem_read: ["src/**", "tests/**"]                     │    │
│  │  filesystem_write: ["tests/output/**"]                       │    │
│  │  tools_allowed: ["pytest", "coverage"]                       │    │
│  │  shell_commands: ["git", "npm"]                              │    │
│  │  mcp_actions: {"supabase": ["query"]}                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│  ┌─────────────────────────────▼─────────────────────────────────┐  │
│  │                  Permission Checker                            │  │
│  │                                                                │  │
│  │  1. Parse tool call (tool_id, params)                         │  │
│  │  2. Identify resource type (filesystem? tool? mcp?)           │  │
│  │  3. Check against PermissionContext                           │  │
│  │  4. Return: ALLOWED or DENIED(reason)                         │  │
│  └─────────────────────────────┬─────────────────────────────────┘  │
│                                │                                     │
│          ┌─────────────────────┼─────────────────────┐              │
│          │ ALLOWED             │ DENIED              │              │
│          ▼                     ▼                     │              │
│  ┌───────────────┐    ┌───────────────────────────┐ │              │
│  │   Execute     │    │   Return Error            │ │              │
│  │   via         │    │   + Log for annealing     │ │              │
│  │   Executor    │    │   + Suggest help signal   │ │              │
│  └───────────────┘    └───────────────────────────┘ │              │
│                                                      │              │
└──────────────────────────────────────────────────────┴──────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Audit Logger                                      │
│  Every request logged, whether allowed or denied                     │
│  .ai/logs/audit/{date}/{session}.jsonl                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# kiwi_mcp/runtime/permissions.py

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Optional
import logging


@dataclass
class PermissionContext:
    """Parsed permissions from directive <permissions> tag."""
    
    filesystem_read: list[str] = field(default_factory=list)
    filesystem_write: list[str] = field(default_factory=list)
    tools_allowed: list[str] = field(default_factory=list)
    shell_commands: list[str] = field(default_factory=list)
    kiwi_actions: list[str] = field(default_factory=list)
    mcp_permissions: dict[str, list[str]] = field(default_factory=dict)
    explicit_denials: list[dict] = field(default_factory=list)
    
    @classmethod
    def from_directive(cls, permissions_list: list[dict]) -> "PermissionContext":
        """Parse directive permissions into context."""
        ctx = cls()
        
        for perm in permissions_list:
            tag = perm.get("tag")
            attrs = perm.get("attrs", {})
            
            if tag == "read" and attrs.get("resource") == "filesystem":
                ctx.filesystem_read.append(attrs.get("path", ""))
            elif tag == "write" and attrs.get("resource") == "filesystem":
                ctx.filesystem_write.append(attrs.get("path", ""))
            elif tag == "execute":
                resource = attrs.get("resource")
                if resource == "tool":
                    ctx.tools_allowed.append(attrs.get("id"))
                elif resource == "shell":
                    ctx.shell_commands.extend(attrs.get("commands", "").split(","))
                elif resource == "kiwi-mcp":
                    ctx.kiwi_actions.append(attrs.get("action"))
                elif resource == "mcp":
                    mcp_name = attrs.get("name")
                    actions = attrs.get("actions", "").split(",")
                    ctx.mcp_permissions[mcp_name] = actions
            elif tag == "deny":
                ctx.explicit_denials.append(attrs)
        
        return ctx
    
    def can_read(self, path: str) -> bool:
        """Check if path is readable."""
        return any(fnmatch(path, pat) for pat in self.filesystem_read)
    
    def can_write(self, path: str) -> bool:
        """Check if path is writable."""
        return any(fnmatch(path, pat) for pat in self.filesystem_write)
    
    def can_execute_tool(self, tool_id: str) -> bool:
        """Check if tool can be executed."""
        return tool_id in self.tools_allowed
    
    def can_run_command(self, command: str) -> bool:
        """Check if shell command is allowed."""
        # Extract base command (e.g., "git" from "git status")
        base_cmd = command.split()[0] if command else ""
        return base_cmd in self.shell_commands
    
    def can_use_mcp(self, mcp_name: str, action: str) -> bool:
        """Check if MCP action is allowed."""
        allowed_actions = self.mcp_permissions.get(mcp_name, [])
        return action in allowed_actions or "*" in allowed_actions
    
    def intersect(self, other: "PermissionContext") -> "PermissionContext":
        """Create intersection of two permission contexts.
        
        Used for subagent spawning: child gets intersection of
        parent's actual permissions and child's declared permissions.
        """
        return PermissionContext(
            filesystem_read=[p for p in other.filesystem_read 
                           if any(fnmatch(p, pat) for pat in self.filesystem_read)],
            filesystem_write=[p for p in other.filesystem_write 
                            if any(fnmatch(p, pat) for pat in self.filesystem_write)],
            tools_allowed=[t for t in other.tools_allowed if t in self.tools_allowed],
            shell_commands=[c for c in other.shell_commands if c in self.shell_commands],
            kiwi_actions=[a for a in other.kiwi_actions if a in self.kiwi_actions],
            mcp_permissions={
                mcp: [a for a in actions if a in self.mcp_permissions.get(mcp, [])]
                for mcp, actions in other.mcp_permissions.items()
            }
        )
    
    def exceeds(self, parent: "PermissionContext") -> bool:
        """Check if this context exceeds parent's permissions.
        
        Returns True if any permission in self is not covered by parent.
        """
        # Check filesystem
        for path in self.filesystem_read:
            if not any(fnmatch(path, pat) for pat in parent.filesystem_read):
                return True
        for path in self.filesystem_write:
            if not any(fnmatch(path, pat) for pat in parent.filesystem_write):
                return True
        
        # Check tools
        for tool in self.tools_allowed:
            if tool not in parent.tools_allowed:
                return True
        
        # Check shell commands
        for cmd in self.shell_commands:
            if cmd not in parent.shell_commands:
                return True
        
        return False


class PermissionChecker:
    """Checks tool calls against permission context."""
    
    def __init__(self, context: PermissionContext):
        self.context = context
        self.logger = logging.getLogger("PermissionChecker")
    
    def check(self, tool_id: str, params: dict) -> tuple[bool, Optional[str]]:
        """Check if tool call is permitted.
        
        Returns:
            (allowed: bool, reason: Optional[str])
        """
        # Filesystem operations
        if tool_id.startswith("filesystem."):
            return self._check_filesystem(tool_id, params)
        
        # Shell operations
        if tool_id == "shell.run":
            return self._check_shell(params)
        
        # Tool execution
        if tool_id in ("execute", "run"):
            return self._check_tool(params)
        
        # MCP operations
        if "." in tool_id and tool_id.split(".")[0] in self.context.mcp_permissions:
            return self._check_mcp(tool_id, params)
        
        # Kiwi meta-tools (always allowed if in context)
        if tool_id in ("search", "load", "execute", "help"):
            if tool_id in self.context.kiwi_actions or not self.context.kiwi_actions:
                return (True, None)
            return (False, f"Kiwi action '{tool_id}' not permitted")
        
        # Unknown tool - deny by default
        self.logger.warning(f"Unknown tool '{tool_id}' - denying by default")
        return (False, f"Unknown tool '{tool_id}' not in permission context")
    
    def _check_filesystem(self, tool_id: str, params: dict) -> tuple[bool, Optional[str]]:
        path = params.get("path", params.get("file", ""))
        
        if tool_id == "filesystem.read":
            if self.context.can_read(path):
                return (True, None)
            return (False, f"Read not allowed on '{path}'")
        
        elif tool_id in ("filesystem.write", "filesystem.create", "filesystem.delete"):
            if self.context.can_write(path):
                return (True, None)
            return (False, f"Write not allowed on '{path}'")
        
        elif tool_id == "filesystem.list":
            if self.context.can_read(path):
                return (True, None)
            return (False, f"List not allowed on '{path}'")
        
        return (False, f"Unknown filesystem operation '{tool_id}'")
    
    def _check_shell(self, params: dict) -> tuple[bool, Optional[str]]:
        command = params.get("command", "")
        
        if self.context.can_run_command(command):
            return (True, None)
        
        base_cmd = command.split()[0] if command else "unknown"
        return (False, f"Shell command '{base_cmd}' not in allowlist")
    
    def _check_tool(self, params: dict) -> tuple[bool, Optional[str]]:
        tool_id = params.get("tool_id", params.get("script_name", params.get("item_id", "")))
        
        if self.context.can_execute_tool(tool_id):
            return (True, None)
        
        return (False, f"Tool '{tool_id}' not permitted")
    
    def _check_mcp(self, tool_id: str, params: dict) -> tuple[bool, Optional[str]]:
        mcp_name, action = tool_id.split(".", 1)
        
        if self.context.can_use_mcp(mcp_name, action):
            return (True, None)
        
        return (False, f"MCP action '{mcp_name}.{action}' not permitted")
```

### KiwiProxy Integration

```python
# kiwi_mcp/runtime/proxy.py

from dataclasses import dataclass
from typing import Any, Optional
import logging
import time

from .permissions import PermissionContext, PermissionChecker
from .audit import AuditLogger
from .loop_detector import LoopDetector


@dataclass
class ToolCallResult:
    """Result of a tool call through the proxy."""
    success: bool
    result: Any
    denied: bool = False
    denial_reason: Optional[str] = None
    rate_limited: bool = False
    execution_time_ms: float = 0


class KiwiProxy:
    """Proxy layer for all tool calls with permission enforcement."""
    
    def __init__(
        self,
        permission_context: PermissionContext,
        executor_registry: "ExecutorRegistry",
        session_id: str,
        directive_name: str
    ):
        self.permissions = permission_context
        self.checker = PermissionChecker(permission_context)
        self.executors = executor_registry
        self.session_id = session_id
        self.directive_name = directive_name
        
        self.audit = AuditLogger(session_id)
        self.loop_detector = LoopDetector()
        self.logger = logging.getLogger("KiwiProxy")
        
        # Rate limiting
        self.call_counts: dict[str, int] = {}
        self.rate_limits: dict[str, int] = {
            "filesystem.write": 100,  # Max 100 writes per session
            "shell.run": 50,          # Max 50 shell commands
            "mcp.*": 200,             # Max 200 MCP calls
        }
    
    async def call_tool(self, tool_id: str, params: dict) -> ToolCallResult:
        """Execute a tool call with full enforcement.
        
        1. Log request (always)
        2. Check permissions (hard enforcement)
        3. Check rate limits
        4. Detect loops
        5. Execute if allowed
        6. Log result
        """
        start_time = time.time()
        
        # 1. Always log the request
        self.audit.log_request(tool_id, params)
        
        # 2. Permission check
        allowed, denial_reason = self.checker.check(tool_id, params)
        
        if not allowed:
            self.logger.warning(
                f"DENIED: {tool_id} - {denial_reason} "
                f"[session={self.session_id}, directive={self.directive_name}]"
            )
            self.audit.log_denial(tool_id, params, denial_reason)
            
            return ToolCallResult(
                success=False,
                result={"error": f"Permission denied: {denial_reason}"},
                denied=True,
                denial_reason=denial_reason
            )
        
        # 3. Rate limit check
        if self._is_rate_limited(tool_id):
            self.audit.log_rate_limit(tool_id)
            return ToolCallResult(
                success=False,
                result={"error": f"Rate limit exceeded for {tool_id}"},
                rate_limited=True
            )
        
        # 4. Loop detection
        stuck_signal = self.loop_detector.record_call(tool_id, params)
        if stuck_signal:
            self.logger.warning(f"Loop detected: {stuck_signal.pattern}")
            # Don't block, but add hint to result
        
        # 5. Execute
        try:
            result = await self.executors.execute(tool_id, params)
            
            execution_time = (time.time() - start_time) * 1000
            self.audit.log_success(tool_id, params, result, execution_time)
            
            # Add loop warning if detected
            if stuck_signal:
                result["_loop_warning"] = stuck_signal.suggestion
            
            return ToolCallResult(
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.audit.log_error(tool_id, params, str(e), execution_time)
            
            return ToolCallResult(
                success=False,
                result={"error": str(e)},
                execution_time_ms=execution_time
            )
    
    def _is_rate_limited(self, tool_id: str) -> bool:
        """Check if tool call exceeds rate limit."""
        # Find matching rate limit
        limit = None
        for pattern, max_calls in self.rate_limits.items():
            if pattern == tool_id or (pattern.endswith("*") and 
                                       tool_id.startswith(pattern[:-1])):
                limit = max_calls
                break
        
        if limit is None:
            return False
        
        # Increment and check
        self.call_counts[tool_id] = self.call_counts.get(tool_id, 0) + 1
        return self.call_counts[tool_id] > limit
```

---

## Permission Inheritance in Recursion

### The Problem

In recursive agent setups (directive spawns subagent), we must prevent privilege escalation:

```
Parent Directive: Can read src/**, write tests/**
  └─ Spawns Child Directive: Declares it wants to write src/**
     └─ DENIED: Child cannot exceed parent's permissions
```

### The Solution: Permission Intersection

```python
def spawn_subagent(self, child_directive_name: str, inputs: dict):
    # Load child's declared permissions
    child_directive = self.load_directive(child_directive_name)
    child_declared = PermissionContext.from_directive(
        child_directive.get("permissions", [])
    )
    
    # Compute intersection with parent's actual permissions
    child_actual = self.permissions.intersect(child_declared)
    
    # Check for escalation attempt
    if child_declared.exceeds(self.permissions):
        # Log the attempt
        self.audit.log_escalation_attempt(
            child_directive_name,
            child_declared,
            self.permissions
        )
        
        # Option 1: Deny spawn entirely
        return {"error": "Permission escalation denied"}
        
        # Option 2: Spawn with reduced permissions (silent downgrade)
        # child_actual already has intersection, so this would work
    
    # Spawn with scoped permissions
    return Executor(
        directive=child_directive,
        permissions=child_actual,
        parent_session=self.session_id
    )
```

### Inheritance Rules

| Parent Has | Child Declares | Child Gets | Reason |
|------------|----------------|------------|--------|
| `src/**` read | `src/**` read | `src/**` read | Equal = allowed |
| `src/**` read | `src/utils/**` read | `src/utils/**` read | Subset = allowed |
| `src/**` read | `**/*` read | `src/**` read | Intersection |
| `src/**` read | `config/**` read | (none) | No overlap |
| (none) | `src/**` read | (denied) | Parent lacks permission |

---

## Help Tool Redesign: Agent Control Signals

### Motivation

The help tool currently only provides documentation. We extend it to serve as an **agent control channel**:

1. **Stuck Signal**: Agent recognizes it's in a loop or confused
2. **Escalate Signal**: Agent needs human decision on ambiguous situation
3. **Checkpoint Request**: Agent wants to save state before risky action

### Extended Schema

```python
class HelpTool(BaseTool):
    @property
    def schema(self) -> Tool:
        return Tool(
            name="help",
            description="Get help, guidance, or signal for human intervention",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["guidance", "stuck", "escalate", "checkpoint"],
                        "description": "Type of help needed",
                        "default": "guidance"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Help topic (for guidance action)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why help is needed (for stuck/escalate)"
                    },
                    "attempts": {
                        "type": "integer",
                        "description": "Number of failed attempts (for stuck)"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Decision options (for escalate)"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for the signal"
                    }
                }
            }
        )
```

### Signal Handling

```python
async def _signal_stuck(self, arguments: dict) -> dict:
    """Agent signals it's stuck."""
    session_id = self._get_session_id()
    reason = arguments.get("reason", "Unknown")
    attempts = arguments.get("attempts", 0)
    
    # Log to monitoring
    await self.monitor.log_stuck_signal(
        session_id=session_id,
        reason=reason,
        attempts=attempts,
        context=arguments.get("context", {})
    )
    
    # Queue for human review if too many attempts
    if attempts > 3:
        await self.approval_queue.add(
            session_id=session_id,
            type="stuck",
            reason=reason,
            priority="high" if attempts > 5 else "normal"
        )
    
    # Trigger annealing analysis
    if attempts > 2:
        await self.annealing.analyze_stuck(
            session_id=session_id,
            directive_name=self._get_directive_name(),
            reason=reason
        )
    
    return {
        "status": "stuck_acknowledged",
        "action": "awaiting_intervention" if attempts > 3 else "retry_suggested",
        "session_id": session_id,
        "suggestion": self._get_stuck_suggestion(reason, attempts)
    }


async def _signal_escalate(self, arguments: dict) -> dict:
    """Agent needs human decision."""
    session_id = self._get_session_id()
    reason = arguments.get("reason", "Decision needed")
    options = arguments.get("options", [])
    
    # Add to approval queue
    approval_id = await self.approval_queue.add(
        session_id=session_id,
        type="escalation",
        reason=reason,
        options=options,
        context=arguments.get("context", {})
    )
    
    # Notify human (webhook, CLI alert, etc.)
    await self.notifier.send_escalation(
        approval_id=approval_id,
        reason=reason,
        options=options
    )
    
    return {
        "status": "escalated",
        "approval_id": approval_id,
        "action": "awaiting_human_decision",
        "message": f"Escalated to human. Approval ID: {approval_id}"
    }


async def _request_checkpoint(self, arguments: dict) -> dict:
    """Agent requests state checkpoint before risky action."""
    session_id = self._get_session_id()
    reason = arguments.get("reason", "Pre-action checkpoint")
    
    # Create checkpoint
    checkpoint_id = await self.checkpoint_manager.create(
        session_id=session_id,
        reason=reason,
        context=arguments.get("context", {})
    )
    
    # If git available, also create git checkpoint
    if self.git_helper.is_available():
        commit_sha = await self.git_helper.checkpoint(
            message=f"Checkpoint: {reason}",
            session_id=session_id
        )
    else:
        commit_sha = None
    
    return {
        "status": "checkpoint_created",
        "checkpoint_id": checkpoint_id,
        "git_sha": commit_sha,
        "message": "State saved. You can proceed with risky action."
    }
```

### Integration with Directives

Directives can specify deviation rules that reference help signals:

```xml
<directive name="risky_operation" version="1.0.0">
  <metadata>
    <deviation_rules auto_fix="false" ask_first="true" escalate="true">
      On uncertainty, use help(action="escalate")
      On repeated failures, use help(action="stuck")
      Before destructive actions, use help(action="checkpoint")
    </deviation_rules>
  </metadata>
</directive>
```

---

## Loop Detection

### The Problem

Agents can get stuck in loops:
- Repeatedly calling same tool with same params
- Alternating between two failing states
- Retry loops without progress

### Detection Algorithm

```python
# kiwi_mcp/runtime/loop_detector.py

from dataclasses import dataclass
from typing import Optional
import hashlib


@dataclass
class StuckSignal:
    reason: str
    pattern: str
    attempts: int
    suggestion: str


class LoopDetector:
    """Detects repetitive call patterns indicating stuck agent."""
    
    def __init__(
        self,
        window_size: int = 10,
        repeat_threshold: int = 3,
        similarity_threshold: float = 0.9
    ):
        self.window_size = window_size
        self.repeat_threshold = repeat_threshold
        self.similarity_threshold = similarity_threshold
        self.recent_calls: list[dict] = []
        self.call_hashes: list[str] = []
    
    def record_call(self, tool_id: str, params: dict) -> Optional[StuckSignal]:
        """Record a call and check for loop patterns.
        
        Returns StuckSignal if loop detected, None otherwise.
        """
        # Create call signature
        call = {"tool": tool_id, "params": params}
        call_hash = self._hash_call(call)
        
        # Add to history
        self.recent_calls.append(call)
        self.call_hashes.append(call_hash)
        
        # Trim to window
        if len(self.recent_calls) > self.window_size:
            self.recent_calls.pop(0)
            self.call_hashes.pop(0)
        
        # Check for patterns
        if len(self.call_hashes) >= self.repeat_threshold:
            # Check exact repeats
            if self._detect_exact_repeat():
                return StuckSignal(
                    reason="exact_repeat",
                    pattern=f"Same call repeated {self.repeat_threshold}+ times",
                    attempts=self._count_repeats(),
                    suggestion="Consider using help(action='stuck', reason='Repeating same action')"
                )
            
            # Check alternating pattern
            if self._detect_alternating():
                return StuckSignal(
                    reason="alternating_pattern",
                    pattern="Alternating between two calls",
                    attempts=len(self.call_hashes) // 2,
                    suggestion="Consider using help(action='stuck', reason='Alternating between states')"
                )
        
        return None
    
    def _hash_call(self, call: dict) -> str:
        """Create hash of call for comparison."""
        import json
        content = json.dumps(call, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _detect_exact_repeat(self) -> bool:
        """Check if last N calls are identical."""
        if len(self.call_hashes) < self.repeat_threshold:
            return False
        
        last_hash = self.call_hashes[-1]
        recent = self.call_hashes[-self.repeat_threshold:]
        return all(h == last_hash for h in recent)
    
    def _detect_alternating(self) -> bool:
        """Check for A-B-A-B pattern."""
        if len(self.call_hashes) < 4:
            return False
        
        # Check last 4 calls: A B A B
        h = self.call_hashes[-4:]
        return h[0] == h[2] and h[1] == h[3] and h[0] != h[1]
    
    def _count_repeats(self) -> int:
        """Count consecutive repeats of last call."""
        if not self.call_hashes:
            return 0
        
        last = self.call_hashes[-1]
        count = 0
        for h in reversed(self.call_hashes):
            if h == last:
                count += 1
            else:
                break
        return count
    
    def reset(self):
        """Reset detection state (e.g., after successful progress)."""
        self.recent_calls.clear()
        self.call_hashes.clear()
```

---

## Audit Logging

### Log Format

Every tool call is logged:

```json
{
  "timestamp": "2026-01-22T10:30:00.123Z",
  "session_id": "sess_abc123",
  "directive_name": "test_feature",
  "event_type": "tool_call",
  "tool_id": "filesystem.read",
  "params": {"path": "src/main.py"},
  "permission_check": {
    "allowed": true,
    "checked_against": ["src/**"]
  },
  "result": {
    "success": true,
    "execution_time_ms": 12.5
  }
}
```

For denials:

```json
{
  "timestamp": "2026-01-22T10:30:01.456Z",
  "session_id": "sess_abc123",
  "directive_name": "test_feature",
  "event_type": "permission_denied",
  "tool_id": "filesystem.write",
  "params": {"path": "config/secrets.yaml"},
  "permission_check": {
    "allowed": false,
    "reason": "Write not allowed on 'config/secrets.yaml'",
    "directive_allows_write": ["tests/output/**"]
  },
  "annealing_hint": "Consider adding <write resource='filesystem' path='config/**' /> if needed"
}
```

---

## Success Metrics

- [ ] 100% of tool calls pass through permission checker
- [ ] Zero permission escalations in recursive spawning
- [ ] All denials logged with annealing hints
- [ ] Loop detection catches >90% of stuck patterns
- [ ] Help signals processed within 100ms
- [ ] Audit logs complete and queryable

---

## Related Documents

- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Phase 3
- [DIRECTIVE_RUNTIME_ARCHITECTURE.md](./DIRECTIVE_RUNTIME_ARCHITECTURE.md) - Executor spawning
- [PERMISSION_ENFORCEMENT.md](./PERMISSION_ENFORCEMENT.md) - Current implementation
- [MCP_ORCHESTRATION_DESIGN.md](./MCP_ORCHESTRATION_DESIGN.md) - MCP routing
