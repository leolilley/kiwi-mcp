# Tool Validation Design: Dynamic & Manifest-Driven

**Date:** 2026-01-23  
**Status:** Design Document  
**Issue:** Current validation is too rigid for dynamic tool architecture

---

## The Problem

Current `ToolValidator` assumes all tools are Python/Bash scripts with files:

```python
# kiwi_mcp/utils/validators.py lines 270-277
expected_extensions = {".py", ".sh", ".yaml", ".yml"}
actual_extension = file_path.suffix.lower()

if actual_extension not in expected_extensions:
    issues.append(
        f"Unsupported file extension '{actual_extension}'. "
        f"Expected one of: {', '.join(sorted(expected_extensions))}"
    )
```

**This breaks the "everything is a tool" architecture where:**
- API tools have NO files (pure config)
- MCP tools have NO files (references)
- Some tools have MANY files (complex scripts)
- Tools are defined by manifests, not file types

---

## The Architecture Vision

From `UNIFIED_TOOLS_ARCHITECTURE.md`:

```
Everything is a tool. Tools are defined by their manifest.
Different tool_types have different requirements.
```

### Tool Types & Their Validation Needs

| Tool Type | Files? | What to Validate |
|-----------|:------:|------------------|
| **primitive** | ❌ | Nothing (hard-coded in code) |
| **runtime** | Maybe | Manifest: executor_id, config |
| **mcp_server** | Maybe | Manifest: executor_id, transport, command/url |
| **mcp_tool** | ❌ | Manifest: executor_id (must be mcp_server), mcp_tool_name |
| **script** | ✅ | Manifest + Files: Python/Bash syntax, entrypoint |
| **api** | ❌ | Manifest: executor_id (must be http_client), method, url |
| **directive** | ✅ | Manifest + Files: XML structure, permissions |
| **knowledge** | ✅ | Manifest + Files: Markdown + YAML frontmatter |

**Key insight:** Validation depends on `tool_type`, not file extension!

---

## Current Validation Flow (Wrong)

```python
# For ALL tools:
1. Check file extension (.py, .sh, .yaml, .yml)
2. Check filename matches tool_id
3. Check manifest fields (tool_id, tool_type, version, executor_id)
```

**Problems:**
1. ❌ Requires a file (breaks API tools, MCP tools)
2. ❌ Restricts extensions (what about Rust? Go? Ruby?)
3. ❌ Doesn't validate tool_type-specific requirements
4. ❌ Doesn't handle multi-file tools (script with lib/ directory)

---

## Correct Validation Flow (Manifest-Driven)

```python
# Layer 1: Universal Validation (ALL tools)
1. Check manifest exists (tool.yaml or embedded metadata)
2. Validate required fields: tool_id, tool_type, version
3. Validate executor_id rules:
   - Primitives: must be NULL
   - Non-primitives: must reference a valid tool

# Layer 2: Tool-Type-Specific Validation
if tool_type == "script":
    - Validate files exist
    - Validate entrypoint specified
    - Validate language syntax (Python/Bash/etc)
    - Validate executor is a runtime
    
elif tool_type == "api":
    - Validate NO files required
    - Validate config: method, url, headers
    - Validate executor is http_client
    
elif tool_type == "mcp_tool":
    - Validate NO files required
    - Validate config: mcp_tool_name
    - Validate executor is an mcp_server
    
elif tool_type == "mcp_server":
    - Validate config: transport (stdio/sse/websocket)
    - If transport=stdio: validate command, args
    - If transport=sse/websocket: validate url
    - Validate executor is subprocess or http_client
    
elif tool_type == "runtime":
    - Validate config: command or similar
    - Validate executor is a primitive
    
elif tool_type == "knowledge":
    - Validate file is markdown
    - Validate YAML frontmatter
    - Validate executor is NULL
    
# Layer 3: Runtime Parameter Validation (at execution time)
# Handled by PrimitiveExecutor using tool's parameter schema
```

---

## Tool Manifest Structure

All tools are defined by a manifest (YAML or embedded metadata):

```yaml
# tool.yaml (or embedded in file metadata)
tool_id: my_tool
tool_type: script | api | mcp_tool | mcp_server | runtime | primitive
version: "1.0.0"
description: "What this tool does"
executor: other_tool_id  # NULL for primitives and knowledge

# Tool-type-specific config
config:
  # Different for each tool_type (validated separately)
  
parameters:
  - name: param1
    type: string
    required: true
```

### Manifest Locations

**Option 1: Separate `tool.yaml` file**
```
.ai/tools/
  ├── my_script/
  │   ├── tool.yaml          ← Manifest
  │   ├── main.py            ← Entrypoint
  │   └── lib/utils.py       ← Additional files
```

**Option 2: Embedded in file metadata**
```python
#!/usr/bin/env python3
"""
tool_id: my_script
tool_type: script
version: 1.0.0
executor: python_runtime
"""
```

**Option 3: Pure data (API tools, MCP tools)**
```
.ai/tools/
  ├── weather_api.yaml       ← Entire tool is one manifest file
  └── slack_webhook.yaml     ← No separate files needed
```

---

## Examples

### Example 1: Script Tool (Has Files)

```yaml
# .ai/tools/email_enricher/tool.yaml
tool_id: email_enricher
tool_type: script
version: "1.2.0"
executor: python_runtime
description: "Enrich email addresses with company data"
config:
  entrypoint: main.py
  requires:
    - httpx>=0.24.0
    - pydantic>=2.0
parameters:
  - name: email
    type: string
    required: true
```

**Files:**
```
.ai/tools/email_enricher/
  ├── tool.yaml
  ├── main.py               ← Entrypoint
  ├── requirements.txt
  └── lib/
      └── clearbit.py
```

**Validation:**
- ✅ Manifest exists
- ✅ `tool_id`, `tool_type`, `version`, `executor` present
- ✅ `executor: python_runtime` is a valid runtime
- ✅ `config.entrypoint: main.py` exists as file
- ✅ `main.py` has valid Python syntax
- ✅ `requirements.txt` has valid format

### Example 2: API Tool (No Files)

```yaml
# .ai/tools/weather_api.yaml  ← Entire tool is one file
tool_id: weather_forecast
tool_type: api
version: "1.0.0"
executor: http_client
description: "Get weather forecast for coordinates"
config:
  method: GET
  url_template: "https://api.weather.com/v1/forecast?lat={lat}&lon={lon}&units=metric"
  headers:
    X-API-Key: "${WEATHER_API_KEY}"
  response_transform: "$.forecast.daily[0:7]"
parameters:
  - name: lat
    type: number
    required: true
  - name: lon
    type: number
    required: true
```

**Files:** NONE (entire tool is manifest)

**Validation:**
- ✅ Manifest exists
- ✅ `tool_id`, `tool_type`, `version`, `executor` present
- ✅ `executor: http_client` is a primitive
- ✅ `config.method` is valid HTTP method
- ✅ `config.url_template` is valid URL
- ✅ Template variables match parameters
- ❌ NO file extension validation
- ❌ NO syntax checking

### Example 3: MCP Tool (No Files)

```yaml
# .ai/tools/supabase_execute_sql.yaml
tool_id: supabase_execute_sql
tool_type: mcp_tool
version: "1.0.0"
executor: supabase_mcp
description: "Execute SQL queries on Supabase"
config:
  mcp_tool_name: execute_sql
parameters:
  - name: project_id
    type: string
    required: true
  - name: query
    type: string
    required: true
```

**Files:** NONE

**Validation:**
- ✅ Manifest exists
- ✅ `tool_id`, `tool_type`, `version`, `executor` present
- ✅ `executor: supabase_mcp` is an mcp_server
- ✅ `config.mcp_tool_name` present
- ❌ NO file validation

### Example 4: MCP Server (Config Only)

```yaml
# .ai/tools/github_mcp.yaml
tool_id: github_mcp
tool_type: mcp_server
version: "1.0.0"
executor: subprocess
description: "GitHub MCP server for repository operations"
config:
  transport: stdio
  command: npx
  args: ["-y", "@modelcontextprotocol/server-github"]
  env:
    GITHUB_TOKEN: "${GITHUB_TOKEN}"
  startup_timeout: 10
```

**Files:** NONE (spawns external NPM package)

**Validation:**
- ✅ Manifest exists
- ✅ `tool_id`, `tool_type`, `version`, `executor` present
- ✅ `executor: subprocess` is a primitive
- ✅ `config.transport: stdio` valid
- ✅ `config.command` and `config.args` present for stdio transport
- ❌ NO file validation

---

## New Validation Architecture

### ValidationManager (Layer 1: Universal)

```python
class ValidationManager:
    """
    Layer 1: Universal validation for all tools.
    Checks manifest structure, not files.
    """
    
    @classmethod
    def validate_manifest(cls, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Validate universal manifest fields."""
        issues = []
        
        # Required for all tools
        if not manifest.get("tool_id"):
            issues.append("tool_id is required")
        if not manifest.get("tool_type"):
            issues.append("tool_type is required")
        if not manifest.get("version"):
            issues.append("version is required")
            
        # Executor rules
        tool_type = manifest.get("tool_type")
        executor = manifest.get("executor")
        
        if tool_type == "primitive":
            if executor is not None:
                issues.append("Primitives must have executor: null")
        elif tool_type == "knowledge":
            if executor is not None:
                issues.append("Knowledge entries must have executor: null")
        else:
            if not executor:
                issues.append(f"Tool type '{tool_type}' requires executor field")
                
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    @classmethod
    def validate_tool(cls, tool_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a tool based on its type.
        Delegates to type-specific validators.
        """
        # Layer 1: Universal validation
        universal_result = cls.validate_manifest(manifest)
        if not universal_result["valid"]:
            return universal_result
            
        # Layer 2: Type-specific validation
        tool_type = manifest.get("tool_type")
        validator = TYPE_VALIDATORS.get(tool_type)
        
        if not validator:
            return {"valid": False, "issues": [f"Unknown tool_type: {tool_type}"]}
            
        return validator.validate(tool_path, manifest)
```

### Type-Specific Validators (Layer 2)

```python
class ScriptToolValidator:
    """Validates script tools (Python, Bash, etc)."""
    
    def validate(self, tool_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        # Script tools MUST have files
        if not tool_path.is_dir():
            issues.append("Script tools must be a directory with files")
            return {"valid": False, "issues": issues}
            
        # Must specify entrypoint
        entrypoint = manifest.get("config", {}).get("entrypoint")
        if not entrypoint:
            issues.append("Script tools must specify config.entrypoint")
            
        # Entrypoint must exist
        entrypoint_path = tool_path / entrypoint
        if not entrypoint_path.exists():
            issues.append(f"Entrypoint '{entrypoint}' not found")
            
        # Validate syntax based on extension
        if entrypoint_path.suffix == ".py":
            syntax_result = validate_python_syntax(entrypoint_path)
            if not syntax_result["valid"]:
                issues.extend(syntax_result["issues"])
        elif entrypoint_path.suffix == ".sh":
            syntax_result = validate_bash_syntax(entrypoint_path)
            if not syntax_result["valid"]:
                issues.extend(syntax_result["issues"])
                
        # Executor must be a runtime
        executor = manifest.get("executor")
        if not executor.endswith("_runtime"):
            issues.append(f"Script executor must be a runtime, got: {executor}")
            
        return {"valid": len(issues) == 0, "issues": issues}


class APIToolValidator:
    """Validates API tools (no files, pure config)."""
    
    def validate(self, tool_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        # API tools should be a single YAML file, not a directory
        if tool_path.is_dir():
            issues.append("API tools should be a single .yaml file, not a directory")
            
        # Executor must be http_client
        executor = manifest.get("executor")
        if executor != "http_client":
            issues.append(f"API tools must use executor: http_client, got: {executor}")
            
        # Required config fields
        config = manifest.get("config", {})
        if not config.get("method"):
            issues.append("API tools must specify config.method")
        if not config.get("url_template") and not config.get("url"):
            issues.append("API tools must specify config.url_template or config.url")
            
        # Validate method
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        if config.get("method") not in valid_methods:
            issues.append(f"Invalid HTTP method: {config.get('method')}")
            
        return {"valid": len(issues) == 0, "issues": issues}


class MCPToolValidator:
    """Validates MCP tool references (no files)."""
    
    def validate(self, tool_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        # MCP tools should be a single YAML file
        if tool_path.is_dir():
            issues.append("MCP tools should be a single .yaml file")
            
        # Executor must be an mcp_server
        executor = manifest.get("executor")
        if not executor or not executor.endswith("_mcp"):
            issues.append(f"MCP tools must reference an mcp_server, got: {executor}")
            
        # Required config fields
        config = manifest.get("config", {})
        if not config.get("mcp_tool_name"):
            issues.append("MCP tools must specify config.mcp_tool_name")
            
        return {"valid": len(issues) == 0, "issues": issues}


class MCPServerValidator:
    """Validates MCP server configurations."""
    
    def validate(self, tool_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        # Executor must be subprocess or http_client
        executor = manifest.get("executor")
        if executor not in ["subprocess", "http_client"]:
            issues.append(
                f"MCP servers must use subprocess or http_client, got: {executor}"
            )
            
        # Validate transport-specific config
        config = manifest.get("config", {})
        transport = config.get("transport")
        
        if not transport:
            issues.append("MCP servers must specify config.transport")
        elif transport == "stdio":
            if not config.get("command"):
                issues.append("stdio transport requires config.command")
        elif transport in ["sse", "websocket"]:
            if not config.get("url"):
                issues.append(f"{transport} transport requires config.url")
        else:
            issues.append(f"Invalid transport: {transport}")
            
        return {"valid": len(issues) == 0, "issues": issues}


class RuntimeValidator:
    """Validates runtime tools."""
    
    def validate(self, tool_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        # Executor must be a primitive
        executor = manifest.get("executor")
        if executor not in ["subprocess", "http_client"]:
            issues.append(
                f"Runtimes must use a primitive executor, got: {executor}"
            )
            
        # Must have some execution config
        config = manifest.get("config", {})
        if not config.get("command") and not config.get("url"):
            issues.append("Runtimes must specify config.command or config.url")
            
        return {"valid": len(issues) == 0, "issues": issues}


# Registry
TYPE_VALIDATORS = {
    "script": ScriptToolValidator(),
    "api": APIToolValidator(),
    "mcp_tool": MCPToolValidator(),
    "mcp_server": MCPServerValidator(),
    "runtime": RuntimeValidator(),
    # "primitive": No validation (hard-coded)
    # "knowledge": Uses existing KnowledgeValidator
    # "directive": Uses existing DirectiveValidator
}
```

---

## Implementation Plan

### Phase 1: Refactor ToolValidator ✅ Start Here

**Goal:** Make validation manifest-driven, not file-driven

1. **Remove file extension checks**
   - Delete lines 270-277 in `validators.py`
   - Tool validation should NOT care about file extensions

2. **Add tool_type dispatching**
   - Check `manifest.tool_type`
   - Dispatch to type-specific validator

3. **Keep existing validation for**:
   - `tool_id`, `tool_type`, `version` (universal)
   - `executor_id` rules (universal)

### Phase 2: Add Type-Specific Validators

Create new validators:
- `ScriptToolValidator` (Python/Bash with files)
- `APIToolValidator` (no files, HTTP config)
- `MCPToolValidator` (no files, references mcp_server)
- `MCPServerValidator` (connection config)
- `RuntimeValidator` (executor config)

### Phase 3: Update Tool Handler

Modify `ToolHandler._create_tool()` to:
1. Accept `tool_type` parameter
2. Create appropriate structure:
   - Scripts: directory with files
   - APIs/MCP tools: single YAML file
3. Validate using correct validator

### Phase 4: Update Tests

Add tests for each tool type:
- Script with multiple files ✅
- API tool (single YAML) ✅
- MCP tool (single YAML) ✅
- MCP server (config only) ✅

---

## Migration Path

### Current State
```
.ai/tools/
  └── my_script.py          ← Single file, embedded metadata
```

### Target State (Flexible)
```
.ai/tools/
  ├── email_enricher/       ← Script: directory with files
  │   ├── tool.yaml
  │   ├── main.py
  │   └── lib/utils.py
  ├── weather_api.yaml      ← API: single manifest file
  ├── slack_webhook.yaml    ← API: single manifest file
  └── github_create_pr.yaml ← MCP tool: single manifest file
```

**Backward compatibility:** Still support embedded metadata in `.py` files

---

## Summary

### Key Principles

1. **Manifest-driven:** Tools are defined by manifests, not file structure
2. **Type-specific:** Each `tool_type` has different validation rules
3. **Flexible:** Support scripts (files), APIs (no files), MCP tools (references)
4. **Layered:**
   - Layer 1: Universal validation (all tools)
   - Layer 2: Type-specific validation (per tool_type)
   - Layer 3: Runtime validation (parameter checking)

### What Changes

**Before (Wrong):**
```python
# All tools must be .py, .sh, .yaml, .yml
# All tools must have a file
# Filename must match tool_id
```

**After (Correct):**
```python
# Tool structure depends on tool_type
# Some tools have files (scripts), some don't (APIs)
# Validation checks manifest fields, not file extensions
# Each tool_type has specific requirements
```

### Implementation Priority

1. ✅ **Phase 1:** Refactor `ToolValidator` (remove file extension checks)
2. ✅ **Phase 2:** Add type-specific validators
3. ✅ **Phase 3:** Update `ToolHandler._create_tool()` for different types
4. ⏳ **Phase 4:** Test full workflow for each tool type

---

## Next Steps

1. Update `validators.py` to remove rigid file checks
2. Implement type-specific validators
3. Update tool creation to support all types
4. Test: create script, API, MCP tool end-to-end
