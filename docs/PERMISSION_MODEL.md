# Kiwi MCP Permission Model

**Date:** 2026-01-25  
**Status:** Approved  
**Author:** Kiwi Team

---

## Executive Summary

Kiwi MCP uses a **capability token model** for permission enforcement. Permissions are declared in directives, minted into signed tokens by the harness, and validated by tools.

**Key Principles:**

1. **No special cases** - All tools validate tokens the same way
2. **Thread-scoped tokens** - One token per thread, persists for thread lifetime
3. **Hierarchical permissions** - Core directives have broad permissions, user directives don't
4. **Defense in depth** - Harness pre-validates, tools validate independently
5. **Kernel stays dumb** - MCP kernel forwards tokens opaquely, never interprets them

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Token Lifecycle](#token-lifecycle)
3. [Thread-Scoped Tokens](#thread-scoped-tokens)
4. [Nested Directive Execution](#nested-directive-execution)
5. [Spawning New Threads](#spawning-new-threads)
6. [Hierarchical Permissions](#hierarchical-permissions)
7. [Capability Definitions](#capability-definitions)
8. [Validation at Directive Creation](#validation-at-directive-creation)
9. [Tool Enforcement](#tool-enforcement)
10. [Examples](#examples)

---

## Core Concepts

### Capability Token

A capability token is a signed JWT/PASETO containing:

```python
@dataclass
class CapabilityToken:
    caps: List[str]              # Granted capabilities (e.g., ["fs.read", "tool.bash"])
    aud: str                     # Audience (prevents cross-service replay)
    exp: datetime                # Expiry time
    parent_id: Optional[str]     # Parent token ID (for delegation chains)
    directive_id: str            # Which directive this was minted from
    thread_id: str               # Which thread this token belongs to
```

### Permissions in Directives

Directives declare permissions in their `<permissions>` section:

```xml
<directive name="deploy_staging" version="1.0.0">
  <metadata>
    <permissions>
      <read resource="filesystem" path="src/**"/>
      <write resource="filesystem" path="dist/**"/>
      <execute resource="tool" id="bash"/>
      <execute resource="kiwi-mcp" action="execute"/>
    </permissions>
  </metadata>
</directive>
```

### Tool Requirements

Tools declare required capabilities in their YAML:

```yaml
# .ai/tools/filesystem/write_file.yaml
tool_id: write_file
executor_id: python

requires:
  - fs.write

parameters:
  - name: path
    type: string
  - name: content
    type: string
```

---

## Token Lifecycle

### 1. Thread Spawns

```python
# User calls
execute(tool, run, thread_directive, {
    directive_name: "deploy_staging"
})

# This spawns a new thread
```

### 2. Harness Loads Directive

```python
# Inside spawned thread, KiwiHarnessRunner loads directive
# This calls the MCP kernel with execute action
directive_data = await mcp.execute(
    item_type="directive",
    action="run",
    item_id="deploy_staging"
)
```

**What happens in the kernel:**

1. **Kernel calls DirectiveHandler** to execute the "run" action
2. **DirectiveHandler uses parse_directive_file()** (hardcoded Python parser)
3. **Parser reads .md file** and extracts XML from markdown
4. **Parser validates XML structure** and extracts `<permissions>` section
5. **Kernel returns parsed directive data** to the harness

**Important:** This parsing happens **without permission checks** because it's reading metadata, not executing code. The directive file itself is just data. Permissions are enforced later when the LLM tries to USE the capabilities declared in the directive.

### 3. Harness Mints Token

```python
# Extract permissions from directive (returned by kernel)
permissions = directive_data["permissions"]
# Example: [{"tag": "read", "attrs": {"resource": "filesystem", "path": "src/**"}}, ...]

# Convert to capability list
caps = permissions_to_caps(permissions)
# Result: ["fs.read", "fs.write", "tool.bash", "kiwi-mcp.execute"]

# Mint signed token
token = mint_token(
    caps=caps,
    aud="kiwi-mcp",
    exp=datetime.now() + timedelta(hours=1),
    directive_id="deploy_staging",
    thread_id=thread_id,
)

# Store in thread context
self.context.capability_token = token
```

### 4. Token Attached to Tool Calls

**Now the LLM starts executing and calling tools:**

```python
# When LLM requests tool execution through harness
await executor.execute(
    tool_id="write_file",
    params={
        "path": "dist/app.js",
        "content": "...",
        "__auth": self.context.capability_token,  # Token attached by harness
    }
)
```

**Key points:**
- The harness automatically attaches the token to ALL tool calls
- The LLM never sees or handles tokens directly
- Tokens are opaque to both LLM and kernel
- Only tools validate tokens

### 5. Tool Validates Token

```python
# write_file tool implementation
async def write_file(path: str, content: str, __auth: str = None) -> dict:
    # Validate token
    token = verify_token(__auth)
    
    if not token:
        return {"error": "Invalid token"}
    
    # Check required capabilities
    if "fs.write" not in token.caps:
        return {"error": "Missing capability: fs.write"}
    
    # Token is valid - proceed
    with open(path, 'w') as f:
        f.write(content)
    
    return {"success": True}
```

---

## Thread-Scoped Tokens

**Key Principle:** Tokens are scoped to threads, not directives.

### Token Lifetime

```
Thread spawns → Token minted → Token persists → Thread terminates → Token expires
```

- **One token per thread**
- **Minted once** when thread spawns (from directive's `<permissions>`)
- **Persists** for entire thread lifetime
- **Used for ALL tool calls** in that thread

### Token Storage

```python
@dataclass
class ThreadContext:
    thread_id: str
    directive_name: str
    capability_token: str  # Stored here, used by all tool calls
    cost_budget: CostBudget
```

---

## Nested Directive Execution

**What happens when a directive (already running on a thread) calls another directive?**

### Same Thread, Same Token

```
┌─────────────────────────────────────────────────────────────────────┐
│  Thread A spawned with directive_X                                   │
│  Token: [fs.read, tool.bash, kiwi-mcp.execute]                      │
│                                                                      │
│  directive_X calls: execute(directive, run, directive_Y)             │
│    │                                                                 │
│    ▼                                                                 │
│  Kernel returns directive_Y data (process steps, permissions, etc)   │
│  NO new token minted                                                 │
│    │                                                                 │
│    ▼                                                                 │
│  LLM follows directive_Y's process steps                             │
│  All tool calls use directive_X's token (SAME token)                 │
│    │                                                                 │
│    ▼                                                                 │
│  directive_Y step calls: execute(tool, run, write_file, {...})      │
│  Tool validates: Does directive_X's token have fs.write?             │
│    │                                                                 │
│    ▼                                                                 │
│  If directive_X only has fs.read: DENIED ❌                          │
│  If directive_X has fs.write: ALLOWED ✅                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### No Privilege Escalation

```xml
<!-- directive_X.md -->
<permissions>
  <read resource="filesystem" path="src/**"/>
  <execute resource="kiwi-mcp" action="execute"/>
</permissions>

<!-- directive_Y.md (called by directive_X) -->
<permissions>
  <write resource="filesystem" path="src/**"/>  <!-- directive_X doesn't have this -->
</permissions>
```

**Result:**
- directive_X calls directive_Y ✅ (has `kiwi-mcp.execute`)
- directive_Y tries to write files ❌ **DENIED** (directive_X's token lacks `fs.write`)

**Key insight:** directive_Y's declared permissions are **ignored** for enforcement. Only directive_X's token matters.

### Why This Design?

1. **Prevents privilege escalation** - Nested directives can't exceed parent's permissions
2. **Simple mental model** - One token per thread, clear ownership
3. **Cost tracking** - All nested execution counts toward parent's budget
4. **Audit trail** - All actions traceable to original directive

---

## Spawning New Threads

**To give a directive its own permissions, spawn a new thread:**

```xml
<directive name="orchestrator" version="1.0.0">
  <metadata>
    <permissions>
      <read resource="filesystem" path="**/*"/>
      <execute resource="spawn" action="thread"/>  <!-- Can spawn threads -->
      <execute resource="kiwi-mcp" action="execute"/>
    </permissions>
  </metadata>
  
  <process>
    <step name="run_deployment">
      <action>
        execute(tool, run, thread_directive, {
          directive_name: "deploy_staging",
          initial_message: "Deploy v1.2.3"
        })
      </action>
    </step>
  </process>
</directive>
```

### Token Attenuation (New Thread)

When spawning a new thread, tokens are **attenuated** (intersection of parent and child permissions):

```python
def attenuate_token(parent_token: CapabilityToken, child_directive: dict) -> CapabilityToken:
    """Child gets intersection of parent caps and child's declared caps."""
    parent_caps = set(parent_token.caps)
    child_caps = set(directive_to_caps(child_directive["permissions"]))
    
    return CapabilityToken(
        caps=list(parent_caps & child_caps),  # INTERSECTION
        aud=parent_token.aud,
        exp=datetime.now() + timedelta(minutes=30),
        parent_id=parent_token.id,
        directive_id=child_directive["name"],
        thread_id=new_thread_id,
    )
```

**Example:**

```
Parent thread token: [fs.read, fs.write, tool.bash, spawn.thread]
Child directive declares: [fs.write, fs.read, net.http]

Child thread gets: [fs.read, fs.write]  ← Intersection
```

---

## Hierarchical Permissions

**Core directives have broad permissions. User directives have limited permissions.**

### Core System Directives

```xml
<!-- .ai/directives/core/thread_directive.md -->
<directive name="thread_directive" version="1.0.0">
  <metadata>
    <description>Spawn directive on managed thread</description>
    <category>core</category>
    
    <permissions>
      <!-- System capabilities -->
      <execute resource="registry" action="write"/>
      <execute resource="registry" action="read"/>
      <execute resource="spawn" action="thread"/>
      
      <!-- MCP operations -->
      <execute resource="kiwi-mcp" action="execute"/>
      <execute resource="kiwi-mcp" action="load"/>
      
      <!-- Filesystem for validation -->
      <read resource="filesystem" path=".ai/directives/**"/>
    </permissions>
  </metadata>
</directive>
```

**Core directives can:**
- Access system infrastructure (thread_registry, etc.)
- Spawn threads
- Manage system resources

### User Directives

```xml
<!-- .ai/directives/user/deploy_staging.md -->
<directive name="deploy_staging" version="1.0.0">
  <metadata>
    <description>Deploy to staging environment</description>
    <category>user</category>
    
    <permissions>
      <read resource="filesystem" path="src/**"/>
      <write resource="filesystem" path="dist/**"/>
      <execute resource="tool" id="bash"/>
      <execute resource="kiwi-mcp" action="execute"/>
    </permissions>
  </metadata>
</directive>
```

**User directives:**
- Have task-specific permissions
- Cannot access system infrastructure
- Cannot spawn threads (unless explicitly granted)

### Permission Hierarchy

```
core directives (category="core")
├── Can grant system capabilities (registry.write, spawn.thread)
├── Can access infrastructure tools
└── Validated at creation with relaxed rules

user directives (category="user" or other)
├── Cannot grant system capabilities
├── Task-specific permissions only
└── Validated at creation with strict rules
```

---

## Extractors vs Directive Parsing

**Important distinction:**

### Tool Extraction (Extractor System)

For tools (Python files, YAML files, etc.), metadata extraction uses the **extractor system**:

```python
# .ai/tools/extractors/yaml_extractor.py
__tool_type__ = "extractor"
__category__ = "extractors"

EXTENSIONS = [".yaml", ".yml"]
PARSER = "yaml"

EXTRACTION_RULES = {
    "name": {"type": "path", "key": "tool_id"},
    "version": {"type": "path", "key": "version"},
    "requires": {"type": "path", "key": "requires"},  # Extracts tool's required caps!
    # ...
}
```

**Critical point:** When you load a tool like `write_file.yaml`, the system:

1. Detects file extension `.yaml`
2. Finds matching extractor: `yaml_extractor.py`
3. Runs `yaml_extractor` to extract metadata
4. Returns extracted metadata including `requires: [fs.write]`

**Extractors themselves are tools!** They:
- Are Python files in `.ai/tools/extractors/`
- Have their own metadata (version, category, etc.)
- Are validated and signed
- **Can be modified** (requires `fs.write` permission!)

### Recursive Permission Model

This creates an important recursive property:

```
┌─────────────────────────────────────────────────────────────────┐
│  To execute write_file tool:                                     │
│    1. Load write_file.yaml                                       │
│    2. Use yaml_extractor to extract "requires: [fs.write]"       │
│    3. LLM calls write_file with token                            │
│    4. write_file validates token has fs.write                    │
│                                                                  │
│  To modify yaml_extractor:                                       │
│    1. Need fs.write permission for .ai/tools/extractors/**       │
│    2. If granted, can modify extraction rules                    │
│    3. Changes affect how ALL YAML tools are loaded               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Security implication:** If a directive has `fs.write` for `.ai/tools/extractors/**`, it can:
- Modify yaml_extractor.py
- Change how `requires` fields are extracted
- Potentially bypass permission checks on future tool loads

**Example attack (if permitted):**

```python
# Modified yaml_extractor.py (malicious)
EXTRACTION_RULES = {
    "requires": {"type": "path", "key": "definitely_not_requires"},  # Wrong key!
    # Now yaml_extractor won't extract the real 'requires' field
}
```

This is why **extractor modification should require very high privilege** (typically only core system directives).

### Directive Parsing (Hardcoded Parser)

For directives, parsing uses **hardcoded Python code**:

```python
# kiwi_mcp/utils/parsers.py
def parse_directive_file(file_path: Path) -> Dict[str, Any]:
    """
    Hardcoded parser for directive markdown files.
    
    1. Reads .md file
    2. Extracts XML from markdown code block
    3. Parses XML and validates structure
    4. Extracts <permissions> section
    5. Returns parsed data
    """
    content = file_path.read_text()
    xml_content = _extract_xml_from_markdown(content)
    root = ET.fromstring(xml_content)
    
    # Extract permissions
    permissions_elem = root.find("metadata/permissions")
    permissions = []
    for child in permissions_elem:
        permissions.append({"tag": child.tag, "attrs": dict(child.attrib)})
    
    return {
        "name": root.get("name"),
        "permissions": permissions,
        # ...
    }
```

**Why hardcoded for directives?**

1. **Directives define permissions** - Can't use permission system to extract permissions (circular)
2. **Critical for security** - Permission parsing must be trusted, not modifiable
3. **Part of MCP core** - Not a pluggable tool

**Why extractors for tools?**

1. **Tools are data** - Extraction is just reading metadata
2. **Extensible** - New file types can have new extractors
3. **Modifiable** - But modification requires `fs.write` permission!

### Modifying Extractors Requires Permission

Extractors are just files, so modifying them follows the normal permission model:

```xml
<directive name="modify_extractor" version="1.0.0">
  <metadata>
    <permissions>
      <write resource="filesystem" path=".ai/tools/extractors/**"/>
    </permissions>
  </metadata>
</directive>
```

**What happens:**

1. Directive's token includes `fs.write` for `.ai/tools/extractors/**` ✅
2. LLM calls write_file on `yaml_extractor.py`
3. write_file tool validates token has `fs.write` ✅
4. File is modified
5. **New extraction behavior takes effect** on next tool load
6. **This affects ALL YAML tools** going forward

**Critical security consideration:**

Since extractors control how tool requirements are extracted, modifying them can compromise the permission system. Only core system directives should have write access to extractors.

### Extractor Loading (Bootstrap Problem)

**Question:** If extractors are tools that need to be extracted, how do we extract the extractors?

**Answer:** Extractors extract THEMSELVES (self-describing):

```python
# yaml_extractor.py extracts its own metadata using python_extractor
# python_extractor.py extracts its own metadata using python AST parsing

# Bootstrap chain:
1. Python has built-in AST parsing (no extraction needed)
2. python_extractor uses Python AST to extract its own metadata
3. python_extractor extracts yaml_extractor.py metadata
4. yaml_extractor extracts YAML tool metadata
```

The bootstrap is **hardcoded** in the tool loading system to use `python_extractor.py` for all `.py` files (including other extractors).

---

## Capability Definitions

Capabilities are defined as data-driven tools in `.ai/tools/capabilities/`:

### Capability Structure with Scopes

```python
# .ai/tools/capabilities/fs.py
__tool_type__ = "capability"
__category__ = "standard"
__version__ = "1.0.0"

CAPABILITIES = ["fs.read", "fs.write", "fs.delete"]
SYSTEM_ONLY = False  # User directives can grant these
DESCRIPTION = "Filesystem access capabilities"

# Scope validation
SCOPE_REQUIRED = True  # fs operations MUST include path scope

def validate_scope(cap: str, scope: dict, requested_path: str) -> bool:
    """Validate that requested path matches granted scope.
    
    Args:
        cap: Capability being checked (e.g., "fs.write")
        scope: Granted scope from permission (e.g., {"path": "src/**"})
        requested_path: Path being accessed (e.g., "src/main.py")
    
    Returns:
        True if requested_path matches scope pattern
    """
    import fnmatch
    
    if "path" not in scope:
        return False  # fs operations require path scope
    
    granted_pattern = scope["path"]
    return fnmatch.fnmatch(requested_path, granted_pattern)
```

### Standard Capabilities (User-Grantable)

```python
# .ai/tools/capabilities/fs.py
CAPABILITIES = ["fs.read", "fs.write", "fs.delete"]
SYSTEM_ONLY = False
SCOPE_REQUIRED = True  # MUST include path pattern

# .ai/tools/capabilities/net.py
CAPABILITIES = ["net.http", "net.websocket"]
SYSTEM_ONLY = False
SCOPE_REQUIRED = False  # Network ops are all-or-nothing

# .ai/tools/capabilities/tool.py
CAPABILITIES = ["tool.execute"]
SYSTEM_ONLY = False
SCOPE_REQUIRED = True  # MUST specify which tools (e.g., {"id": "bash"})
```

### System Capabilities (Core Only)

```python
# .ai/tools/capabilities/registry.py
CAPABILITIES = ["registry.read", "registry.write"]
SYSTEM_ONLY = True  # Only core directives can grant
SCOPE_REQUIRED = False  # Registry ops are all-or-nothing

# .ai/tools/capabilities/spawn.py
CAPABILITIES = ["spawn.thread", "spawn.process"]
SYSTEM_ONLY = True  # Only core directives can spawn
SCOPE_REQUIRED = False

# .ai/tools/capabilities/extractor.py
CAPABILITIES = ["extractor.modify"]
SYSTEM_ONLY = True  # CRITICAL: Only core can modify extractors
SCOPE_REQUIRED = False
```

---

## Path-Based Permission Scoping

**Key principle:** Filesystem permissions MUST include path scopes to prevent overly broad access.

### Permission Declaration with Scopes

```xml
<directive name="user_task" version="1.0.0">
  <metadata>
    <permissions>
      <!-- Scoped filesystem access -->
      <read resource="filesystem" path="src/**"/>
      <write resource="filesystem" path="dist/**"/>
      
      <!-- Scoped tool access -->
      <execute resource="tool" id="bash"/>
      <execute resource="tool" id="pytest"/>
      
      <!-- Cannot write to system files -->
      <!-- <write resource="filesystem" path=".ai/**"/> ❌ -->
    </permissions>
  </metadata>
</directive>
```

### Token Minting with Scopes

When the harness mints a token, it includes scopes:

```python
def permissions_to_caps(permissions: List[dict]) -> List[dict]:
    """Convert directive permissions to capability list with scopes.
    
    Returns:
        [
            {"cap": "fs.read", "scope": {"path": "src/**"}},
            {"cap": "fs.write", "scope": {"path": "dist/**"}},
            {"cap": "tool.execute", "scope": {"id": "bash"}},
        ]
    """
    caps = []
    
    for perm in permissions:
        if perm["tag"] == "read" and perm["attrs"].get("resource") == "filesystem":
            caps.append({
                "cap": "fs.read",
                "scope": {"path": perm["attrs"]["path"]}
            })
        elif perm["tag"] == "write" and perm["attrs"].get("resource") == "filesystem":
            caps.append({
                "cap": "fs.write",
                "scope": {"path": perm["attrs"]["path"]}
            })
        # ...
    
    return caps

@dataclass
class CapabilityToken:
    caps: List[dict]  # NOW includes scopes: [{"cap": str, "scope": dict}, ...]
    aud: str
    exp: datetime
    parent_id: Optional[str]
    directive_id: str
    thread_id: str
```

### Tool Validation with Scopes

Tools validate BOTH capability AND scope:

```python
# write_file tool implementation
async def write_file(path: str, content: str, __auth: str = None) -> dict:
    token = verify_token(__auth)
    
    # 1. Check has fs.write capability
    fs_write_grants = [c for c in token.caps if c["cap"] == "fs.write"]
    
    if not fs_write_grants:
        return {"error": "Missing capability: fs.write"}
    
    # 2. Check if requested path matches ANY granted scope
    import fnmatch
    
    path_allowed = False
    for grant in fs_write_grants:
        granted_pattern = grant["scope"]["path"]
        if fnmatch.fnmatch(path, granted_pattern):
            path_allowed = True
            break
    
    if not path_allowed:
        return {
            "error": f"Path not allowed: {path}",
            "granted_patterns": [g["scope"]["path"] for g in fs_write_grants],
        }
    
    # 3. All checks passed - write file
    with open(path, 'w') as f:
        f.write(content)
    
    return {"success": True}
```

### Preventing System File Modification

**Example: User directive tries to modify extractor**

```xml
<!-- user_directive.md -->
<directive name="malicious" version="1.0.0">
  <metadata>
    <category>user</category>
    <permissions>
      <write resource="filesystem" path="src/**"/>
    </permissions>
  </metadata>
  
  <process>
    <step name="try_modify_extractor">
      <action>
        execute(tool, run, write_file, {
          path: ".ai/tools/extractors/yaml_extractor.py",
          content: "# malicious code"
        })
      </action>
    </step>
  </process>
</directive>
```

**What happens:**

1. Token minted with: `[{"cap": "fs.write", "scope": {"path": "src/**"}}]`
2. LLM calls write_file for `.ai/tools/extractors/yaml_extractor.py`
3. write_file checks: Does path `.ai/tools/extractors/yaml_extractor.py` match `src/**`?
4. **NO MATCH** ❌
5. **DENIED:** "Path not allowed: .ai/tools/extractors/yaml_extractor.py, granted: [src/**]"

### Core Directive Can Modify Extractors

```xml
<!-- core/system_maintenance.md -->
<directive name="system_maintenance" version="1.0.0">
  <metadata>
    <category>core</category>
    <permissions>
      <!-- Broad system access -->
      <write resource="filesystem" path=".ai/**"/>
      <write resource="filesystem" path="src/**"/>
    </permissions>
  </metadata>
</directive>
```

**Token minted:** `[{"cap": "fs.write", "scope": {"path": ".ai/**"}}, {"cap": "fs.write", "scope": {"path": "src/**"}}]`

**Now can write to:**
- `.ai/tools/extractors/yaml_extractor.py` ✅ (matches `.ai/**`)
- `src/main.py` ✅ (matches `src/**`)

### Protected System Paths

Recommendation: Core directives should be very careful granting write access to:

```
.ai/tools/extractors/**       # Modifying extractors affects tool loading
.ai/tools/capabilities/**      # Modifying capabilities affects permission system
.ai/directives/core/**         # Core system directives
```

**Alternative: Explicit extractor capability**

Instead of relying solely on path patterns, we can add explicit capability:

```python
# .ai/tools/capabilities/extractor.py
CAPABILITIES = ["extractor.modify"]
SYSTEM_ONLY = True
```

Then write_file for extractor paths requires BOTH:
1. `fs.write` with matching path scope
2. `extractor.modify` capability

```python
# write_file enhanced validation for extractors
async def write_file(path: str, content: str, __auth: str = None) -> dict:
    token = verify_token(__auth)
    
    # Check if writing to extractor
    if path.startswith(".ai/tools/extractors/"):
        # Requires BOTH fs.write AND extractor.modify
        if "extractor.modify" not in [c["cap"] for c in token.caps]:
            return {"error": "Modifying extractors requires extractor.modify capability"}
    
    # Normal fs.write + scope check
    # ...
```

---

## Project-Scoped Permissions

**Key principle:** All path patterns are relative to the **project root** (where `.ai/` folder is located).

### Default Behavior: Project-Only Access

```xml
<directive name="user_task" version="1.0.0">
  <metadata>
    <permissions>
      <!-- All paths relative to project root -->
      <read resource="filesystem" path="src/**"/>        <!-- /project/src/** -->
      <write resource="filesystem" path="dist/**"/>      <!-- /project/dist/** -->
      <read resource="filesystem" path=".ai/**"/>        <!-- /project/.ai/** -->
    </permissions>
  </metadata>
</directive>
```

**What happens:**

```python
# Tool validation resolves paths relative to project root
project_root = "/home/user/my-project"  # Where .ai/ folder is

# Request: write to "dist/app.js"
requested_path = "dist/app.js"
full_path = project_root / requested_path
# Result: /home/user/my-project/dist/app.js

# Check against granted pattern: "dist/**"
if fnmatch.fnmatch(requested_path, "dist/**"):  # ✅ ALLOWED
    write_file(full_path)
```

### Attempting to Access Outside Project

```python
# LLM tries: write to "../other-project/file.txt"
requested_path = "../other-project/file.txt"
full_path = project_root / requested_path
# Result: /home/user/other-project/file.txt (OUTSIDE project!)

# Validation FAILS because:
# 1. Path normalization detects ".." escape attempt
# 2. Resolved path is outside project root
# 3. Even if pattern matched, project boundary check fails
```

**Security check in write_file:**

```python
# write_file tool implementation
async def write_file(path: str, content: str, __auth: str = None, __project_path: str = None) -> dict:
    token = verify_token(__auth)
    
    # Resolve path relative to project
    project_root = Path(__project_path)
    full_path = (project_root / path).resolve()
    
    # CRITICAL: Ensure resolved path is within project
    if not full_path.is_relative_to(project_root):
        return {
            "error": f"Path outside project: {path}",
            "resolved": str(full_path),
            "project_root": str(project_root),
        }
    
    # Get relative path for scope checking
    relative_path = full_path.relative_to(project_root)
    
    # Check capability + scope
    fs_write_grants = [c for c in token.caps if c["cap"] == "fs.write"]
    
    # Check if relative path matches granted patterns
    path_allowed = False
    for grant in fs_write_grants:
        if fnmatch.fnmatch(str(relative_path), grant["scope"]["path"]):
            path_allowed = True
            break
    
    if not path_allowed:
        return {"error": f"Path not in granted scope: {relative_path}"}
    
    # Write file
    with open(full_path, 'w') as f:
        f.write(content)
    
    return {"success": True, "path": str(relative_path)}
```

### Absolute Paths (System-Only)

To access paths **outside the project**, directives must:

1. Have `category="core"` (system directive)
2. Use **absolute path patterns** in permissions
3. Include special `fs.absolute` capability

```xml
<!-- core/system_backup.md -->
<directive name="system_backup" version="1.0.0">
  <metadata>
    <category>core</category>
    <permissions>
      <!-- Absolute paths require fs.absolute capability -->
      <execute resource="fs" action="absolute"/>
      
      <!-- Now can use absolute patterns -->
      <read resource="filesystem" path="/home/user/**"/>
      <write resource="filesystem" path="/tmp/backups/**"/>
    </permissions>
  </metadata>
</directive>
```

**Validation for absolute paths:**

```python
# .ai/tools/capabilities/fs.py
CAPABILITIES = ["fs.read", "fs.write", "fs.delete", "fs.absolute"]
SYSTEM_ONLY_CAPS = ["fs.absolute"]  # Only core directives can use absolute paths

def validate_directive_grant(capability: str, directive_category: str, scope: dict) -> bool:
    """Validate directive can grant this capability."""
    
    # Check if using absolute path
    path_pattern = scope.get("path", "")
    is_absolute = path_pattern.startswith("/")
    
    if is_absolute:
        # Absolute paths require fs.absolute capability
        if capability in ["fs.read", "fs.write", "fs.delete"]:
            if directive_category != "core":
                return False  # User directives cannot use absolute paths
    
    return True
```

**Tool validation with absolute paths:**

```python
async def write_file(path: str, content: str, __auth: str = None, __project_path: str = None) -> dict:
    token = verify_token(__auth)
    project_root = Path(__project_path)
    
    # Check if path is absolute
    requested_path = Path(path)
    is_absolute_request = requested_path.is_absolute()
    
    if is_absolute_request:
        # Requires fs.absolute capability
        if not any(c["cap"] == "fs.absolute" for c in token.caps):
            return {"error": "Absolute paths require fs.absolute capability"}
        
        # Use absolute path for matching
        full_path = requested_path
        match_path = str(requested_path)
    else:
        # Relative path - scoped to project
        full_path = (project_root / path).resolve()
        
        # Ensure within project
        if not full_path.is_relative_to(project_root):
            return {"error": "Path escape attempt"}
        
        match_path = str(full_path.relative_to(project_root))
    
    # Check against granted patterns
    fs_write_grants = [c for c in token.caps if c["cap"] == "fs.write"]
    
    for grant in fs_write_grants:
        if fnmatch.fnmatch(match_path, grant["scope"]["path"]):
            # Write file
            with open(full_path, 'w') as f:
                f.write(content)
            return {"success": True}
    
    return {"error": "Path not in granted scope"}
```

### Summary: Path Scope Rules

| Path Type | Requires | Example | Allowed For |
|-----------|----------|---------|-------------|
| **Relative (project)** | `fs.write` + scope | `src/**` | All directives |
| **Absolute (system)** | `fs.write` + `fs.absolute` + scope | `/home/user/**` | Core only |
| **Parent escape** | (blocked) | `../other-project` | None |
| **Symlink escape** | (blocked if outside project) | `link -> /etc` | Resolved first |

**Default security:** User directives are **sandboxed to their project**. Only core system directives can access absolute paths.

**System capabilities are rejected for user directives at creation time:**

```python
# kiwi_mcp/handlers/directive/handler.py

async def _create_directive(self, path: str, content: str) -> dict:
    # Parse directive
    directive_data = parse_directive_file(path)
    
    # Extract category
    category = directive_data.get("category", "user")
    
    # Validate each permission
    for perm in directive_data["permissions"]:
        cap = extract_capability(perm)
        cap_def = load_capability_definition(cap)
        
        # Check if directive can grant this capability
        if not cap_def.validate_directive_grant(category):
            return {
                "error": f"Permission denied: {category} directive cannot grant system capability: {cap}",
                "details": f"Only core directives can grant: {cap}",
                "path": path,
            }
    
    # Validation passed - create directive
    # ...
```

**This prevents:**

```xml
<!-- USER directive (category="user") -->
<permissions>
  <execute resource="registry" action="write"/>  <!-- ❌ REJECTED -->
  <!-- Error: user directive cannot grant system capability: registry.write -->
</permissions>
```

**But allows:**

```xml
<!-- CORE directive (category="core") -->
<permissions>
  <execute resource="registry" action="write"/>  <!-- ✅ ALLOWED -->
</permissions>
```

---

## Tool Enforcement

**All tools validate tokens the same way - no special cases:**

```python
# Generic tool validation pattern
async def tool_implementation(params: dict) -> dict:
    # 1. Extract token
    token_str = params.get("__auth")
    
    if not token_str:
        return {"error": "Missing authentication token"}
    
    # 2. Verify signature
    token = verify_token(token_str)
    
    if not token:
        return {"error": "Invalid token signature"}
    
    # 3. Check expiry
    if token.exp < datetime.now():
        return {"error": "Token expired"}
    
    # 4. Check required capabilities
    required_caps = get_tool_requirements(tool_id)  # From tool's YAML
    
    for cap in required_caps:
        if cap not in token.caps:
            return {
                "error": f"Missing capability: {cap}",
                "required": required_caps,
                "granted": token.caps,
            }
    
    # 5. All checks passed - execute tool
    return await execute_tool_logic(params)
```

### Defense in Depth

**Two layers of validation:**

1. **Harness pre-validation (fail fast):**
   ```python
   # Before calling tool
   if required_cap not in self.context.capability_token.caps:
       return {"error": "Capability check failed (harness)"}
   ```

2. **Tool validation (defense in depth):**
   ```python
   # Tool validates independently
   if required_cap not in token.caps:
       return {"error": "Capability check failed (tool)"}
   ```

**Why both layers?**
- Harness: Better error messages for LLM, fail fast
- Tool: Works even if called without harness, security guarantee

---

## Examples

### Example 1: User Directive (Limited Permissions)

```xml
<!-- .ai/directives/user/run_tests.md -->
<directive name="run_tests" version="1.0.0">
  <metadata>
    <category>user</category>
    <permissions>
      <read resource="filesystem" path="tests/**"/>
      <write resource="filesystem" path="tests/output/**"/>
      <execute resource="tool" id="pytest"/>
    </permissions>
  </metadata>
</directive>
```

**Token minted:** `["fs.read", "fs.write", "tool.pytest"]`

**Can do:**
- Read files in `tests/**` ✅
- Write files in `tests/output/**` ✅
- Run pytest ✅

**Cannot do:**
- Read files outside `tests/` ❌
- Write files outside `tests/output/` ❌
- Call thread_registry ❌ (no `registry.write`)
- Spawn threads ❌ (no `spawn.thread`)

### Example 2: Core Directive (Broad Permissions)

```xml
<!-- .ai/directives/core/orchestrate_tests.md -->
<directive name="orchestrate_tests" version="1.0.0">
  <metadata>
    <category>core</category>
    <permissions>
      <read resource="filesystem" path="**/*"/>
      <execute resource="spawn" action="thread"/>
      <execute resource="registry" action="write"/>
      <execute resource="kiwi-mcp" action="execute"/>
    </permissions>
  </metadata>
  
  <process>
    <step name="spawn_test_thread">
      <action>
        execute(tool, run, thread_directive, {
          directive_name: "run_tests",
          initial_message: "Run full test suite"
        })
      </action>
    </step>
  </process>
</directive>
```

**Token minted:** `["fs.read", "spawn.thread", "registry.write", "kiwi-mcp.execute"]`

**Can do:**
- Read any file ✅
- Spawn threads ✅
- Access thread_registry ✅
- Call other directives ✅

### Example 3: Nested Execution (Same Thread)

```xml
<!-- directive_A.md -->
<directive name="deploy" version="1.0.0">
  <metadata>
    <permissions>
      <read resource="filesystem" path="src/**"/>
      <execute resource="kiwi-mcp" action="execute"/>
      <execute resource="tool" id="bash"/>
    </permissions>
  </metadata>
  
  <process>
    <step name="run_tests">
      <action>execute(directive, run, run_tests)</action>
    </step>
    
    <step name="build">
      <action>execute(tool, run, bash, {command: "npm run build"})</action>
    </step>
  </process>
</directive>
```

**What happens:**

1. **Thread spawns with deploy's token:** `["fs.read", "kiwi-mcp.execute", "tool.bash"]`
2. **deploy calls run_tests:**
   - Kernel returns run_tests directive data ✅
   - LLM follows run_tests steps using deploy's token
   - If run_tests tries to write: ❌ **DENIED** (deploy only has `fs.read`)
3. **deploy calls bash:**
   - Token has `tool.bash` ✅
   - Build succeeds

### Example 4: Spawning New Thread (Different Permissions)

```xml
<!-- orchestrator.md -->
<directive name="orchestrator" version="1.0.0">
  <metadata>
    <permissions>
      <read resource="filesystem" path="**/*"/>
      <execute resource="spawn" action="thread"/>
      <execute resource="kiwi-mcp" action="execute"/>
    </permissions>
  </metadata>
  
  <process>
    <step name="spawn_isolated_task">
      <action>
        execute(tool, run, thread_directive, {
          directive_name: "risky_task"  <!-- Has fs.write permission -->
        })
      </action>
    </step>
  </process>
</directive>
```

**What happens:**

1. **orchestrator thread:** Token = `["fs.read", "spawn.thread", "kiwi-mcp.execute"]`
2. **orchestrator spawns risky_task thread:**
   - New thread created
   - risky_task declares: `<permissions><write resource="filesystem" path="temp/**"/></permissions>`
   - Token attenuation: parent `[fs.read, ...]` ∩ child `[fs.write]` = `[]` (no overlap!)
   - **risky_task gets NO write permission** ✅ (parent didn't have `fs.write`)

**To allow risky_task to write:**

```xml
<!-- orchestrator.md (fixed) -->
<permissions>
  <read resource="filesystem" path="**/*"/>
  <write resource="filesystem" path="temp/**"/>  <!-- Add this -->
  <execute resource="spawn" action="thread"/>
  <execute resource="kiwi-mcp" action="execute"/>
</permissions>
```

Now: `[fs.read, fs.write, ...]` ∩ `[fs.write]` = `[fs.write]` ✅

---

## Summary

**The Clean Model:**

1. **One token per thread** - Minted from directive's `<permissions>`
2. **Thread-scoped** - Persists for thread lifetime, used by all tool calls
3. **Nested execution uses same token** - No privilege escalation
4. **New threads get attenuated tokens** - Intersection of parent and child permissions
5. **Hierarchical permissions** - Core directives have broad permissions, user directives don't
6. **System capabilities** - Marked `SYSTEM_ONLY`, rejected for user directives at creation
7. **All tools enforce uniformly** - No special cases, no bypasses
8. **Defense in depth** - Harness pre-validates, tools validate independently
9. **Kernel stays dumb** - Just forwards tokens, never interprets

**No special tokens. No privileged tools. Just clean hierarchical permissions.**
