# Implementation Notes - Kiwi MCP Tooling

**Date:** 2026-01-28  
**Status:** Current Implementation  
**Version:** 0.1.0

---

## Architecture Overview

### The 4 MCP Tools

```
KiwiMCP (server.py)
├── SearchTool        (tools/search.py)
├── LoadTool         (tools/load.py)
├── ExecuteTool      (tools/execute.py)
└── HelpTool         (tools/help.py)
    ↓
TypeHandlerRegistry (handlers/registry.py)
    ├── DirectiveHandler     (handlers/directive/handler.py)
    ├── ToolHandler         (handlers/tool/handler.py)
    └── KnowledgeHandler    (handlers/knowledge/handler.py)
```

### Tool Handler Architecture

```
ToolHandler (handlers/tool/handler.py)
├── search()           → Search local tools
├── load()             → Load tool file
├── execute()          → Run or sign tool
│   ├── _run_tool()    → Execute via PrimitiveExecutor
│   └── _sign_tool()   → Update signature
└── _search_local()    → Find files in .ai/tools/
```

---

## File Structure

### Local Tool Storage

```
.ai/
└── tools/
    ├── primitives/
    │   ├── subprocess.py     # Primitive: spawns processes
    │   └── http_client.py    # Primitive: makes HTTP requests
    ├── utility/
    │   ├── hello_world.py    # Python tool
    │   └── http_test.py      # API tool
    └── my_category/
        └── my_tool.py        # User-created tool
```

### User Tools

```
~/.ai/
└── tools/
    ├── personal_tools/
    └── lib/                  # Shared libraries
        └── *.py
```

### Output Storage

```
.ai/outputs/
└── tools/
    └── {tool_name}/
        ├── output_20260128_120000.json
        └── output_20260128_120100.json
```

---

## Tool Metadata Extraction

### How `extract_tool_metadata()` Works

Located in: `kiwi_mcp/schemas.py`

```python
def extract_tool_metadata(file_path: Path, project_path: Path) -> dict:
    """Extract tool metadata from Python file."""
    
    # 1. Read file
    content = file_path.read_text()
    
    # 2. Extract __variables__
    import ast
    tree = ast.parse(content)
    
    # Find assignments like: __version__ = "1.0.0"
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith('__'):
                    value = ast.literal_eval(node.value)
                    metadata[target.id] = value
    
    # 3. Extract docstring
    docstring = ast.get_docstring(tree)
    
    # 4. Parse Config Schema from docstring
    # Look for "Config Schema:" section
    
    # 5. Return structured metadata
    return {
        "name": file_path.stem,
        "description": docstring,
        "version": metadata.get("__version__"),
        "tool_type": metadata.get("__tool_type__"),
        "executor_id": metadata.get("__executor_id__"),
        "category": metadata.get("__category__"),
        ...
    }
```

### Metadata Fields

| Field | Extract From | Type | Required |
|-------|--------------|------|----------|
| `name` | Filename stem | str | ✅ |
| `description` | Module docstring | str | ✅ |
| `version` | `__version__` | str | ✅ |
| `tool_type` | `__tool_type__` | str | ✅ |
| `executor_id` | `__executor_id__` | str or None | ✅ |
| `category` | `__category__` | str | ✅ |
| `config_schema` | Docstring "Config Schema:" section | dict | ❌ |

---

## Execution Flow

### 1. Search (ToolHandler.search)

```python
async def search(query: str, source: str = "all", limit: int = 10):
    results = []
    
    # Search project tools
    project_tools = project_path / ".ai" / "tools"
    for file_path in search_python_files(project_tools, query):
        meta = extract_tool_metadata(file_path, project_path)
        score = score_relevance(f"{meta['name']} {meta['description']}", query.split())
        results.append({
            "name": meta["name"],
            "description": meta.get("description"),
            "source": "project",
            "path": str(file_path),
            "score": score,
            "tool_type": meta.get("tool_type")
        })
    
    # Search user tools
    user_tools = get_user_space() / "tools"
    for file_path in search_python_files(user_tools, query):
        # ... same as above, source="user"
    
    # Sort and limit
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"results": results[:limit], "total": len(results), ...}
```

### 2. Load (ToolHandler.load)

```python
async def load(tool_name: str, source: str, destination: str = None):
    # Resolve tool location
    file_path = resolver.resolve(tool_name)  # Returns path or None
    
    if not file_path:
        return {"error": f"Tool '{tool_name}' not found"}
    
    # Copy to destination if specified
    if destination and destination != source:
        target_dir = (project_path / ".ai" / "tools" if destination == "project"
                      else get_user_space() / "tools")
        target_file = target_dir / file_path.name
        target_file.write_text(file_path.read_text())
        file_path = target_file
    
    # Extract metadata
    meta = extract_tool_metadata(file_path, project_path)
    
    return {
        "name": tool_name,
        "path": str(file_path),
        "content": file_path.read_text(),
        "source": source,
        "metadata": meta,
        "destination": destination if destination != source else None
    }
```

### 3. Execute: Run (ToolHandler._run_tool)

```python
async def _run_tool(tool_name: str, params: dict, dry_run: bool):
    # Resolve tool
    file_path = resolver.resolve(tool_name)
    if not file_path:
        return {"error": f"Tool '{tool_name}' not found"}
    
    # Extract metadata
    meta = extract_tool_metadata(file_path, project_path)
    
    # Validate signature
    stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path)
    if not ValidationManager.validate_hash(file_content, stored_hash):
        return {"error": "Content hash mismatch - file was modified"}
    
    # Execute via PrimitiveExecutor
    executor = PrimitiveExecutor(project_path)
    result = await executor.execute(
        tool_id=tool_name,
        parameters=params,
        meta=meta
    )
    
    # Save large outputs
    output_manager.save(tool_name, result)
    
    return {
        "tool_id": tool_name,
        "action": "run",
        "status": "success",
        "result": result,
        "execution_time_ms": elapsed_time
    }
```

### 4. Execute: Sign (ToolHandler._sign_tool)

```python
async def _sign_tool(tool_name: str, location: str, category: str = None):
    # Resolve tool
    file_path = resolver.resolve(tool_name)
    if not file_path:
        return {"error": f"Tool '{tool_name}' not found"}
    
    # Read content
    content = file_path.read_text()
    
    # Validate metadata
    meta = extract_tool_metadata(file_path, project_path)
    validate_tool_metadata(meta)
    
    # Calculate hash (content without signature line)
    content_lines = content.split('\n')
    body = '\n'.join(content_lines[1:])  # Skip signature line
    hash_value = hashlib.sha256(body.encode()).hexdigest()
    
    # Create signature
    timestamp = datetime.utcnow().isoformat() + "Z"
    signature = f"# kiwi-mcp:validated:{timestamp}:{hash_value}"
    
    # Update file
    new_content = f"{signature}\n{body}"
    file_path.write_text(new_content)
    
    return {
        "tool_id": tool_name,
        "action": "sign",
        "status": "signed",
        "signature": signature,
        "hash": hash_value
    }
```

---

## PrimitiveExecutor

Located in: `kiwi_mcp/primitives/executor.py`

### How It Works

1. **Resolve Tool Chain**
   ```python
   def build_chain(tool_id: str) -> list[Tool]:
       chain = []
       current = tool_id
       
       while current:
           tool = resolve(current)
           chain.append(tool)
           current = tool.executor_id  # Next in chain
       
       return chain  # [my_tool, python_runtime, subprocess]
   ```

2. **Get Primitive Type**
   ```python
   primitive = chain[-1]  # Last in chain
   
   if primitive.tool_id == "subprocess":
       return await execute_via_subprocess(chain, params)
   elif primitive.tool_id == "http_client":
       return await execute_via_http(chain, params)
   ```

3. **Execute**
   - For subprocess: Spawn Python interpreter with tool's main()
   - For http_client: Make HTTP request with tool's CONFIG

---

## Signature Validation

### Signature Format

```
# kiwi-mcp:validated:{TIMESTAMP}Z:{SHA256_HASH}
```

**Example:**
```
# kiwi-mcp:validated:2026-01-28T12:34:56Z:abc123def456...
```

### Hash Calculation

```python
import hashlib

# Read file content (excluding signature line)
content = file_path.read_text()
lines = content.split('\n')
body = '\n'.join(lines[1:])  # Skip first line (signature)

# Calculate SHA256
hash_value = hashlib.sha256(body.encode()).hexdigest()
```

### Validation During Execution

```python
def validate_signature(file_path: Path, expected_hash: str) -> bool:
    """Validate file integrity."""
    content = file_path.read_text()
    lines = content.split('\n')
    
    # Extract hash from signature
    signature_line = lines[0]
    # Regex: kiwi-mcp:validated:.*:([a-f0-9]{64})
    stored_hash = extract_hash_from_signature(signature_line)
    
    # Calculate current hash
    body = '\n'.join(lines[1:])
    current_hash = hashlib.sha256(body.encode()).hexdigest()
    
    # Compare
    return stored_hash == current_hash
```

---

## Tool Resolution

Located in: `kiwi_mcp/utils/resolvers.py`

### ToolResolver Algorithm

```python
class ToolResolver:
    def __init__(self, project_path: Path):
        self.project_tools = project_path / ".ai" / "tools"
        self.user_tools = get_user_space() / "tools"
    
    def resolve(self, tool_name: str) -> Optional[Path]:
        """Resolve tool file path."""
        
        # Search in project first
        path = self._search_in_directory(self.project_tools, tool_name)
        if path:
            return path
        
        # Fall back to user space
        path = self._search_in_directory(self.user_tools, tool_name)
        if path:
            return path
        
        return None  # Not found
    
    def _search_in_directory(self, dir_path: Path, tool_name: str) -> Optional[Path]:
        """Search for tool in directory."""
        
        # Try exact match in root
        if (dir_path / f"{tool_name}.py").exists():
            return dir_path / f"{tool_name}.py"
        
        # Try in subdirectories
        for subdir in dir_path.rglob("*"):
            if subdir.name == f"{tool_name}.py":
                return subdir
        
        return None
```

### Resolution Examples

```
resolve("hello_world")
  → Search: .ai/tools/hello_world.py ✓ Found
  → Return: .ai/tools/hello_world.py

resolve("http_test")
  → Search: .ai/tools/http_test.py ✓ Found
  → Return: .ai/tools/http_test.py

resolve("my_tool")
  → Search: .ai/tools/my_tool.py ✗ Not found
  → Search: .ai/tools/*/my_tool.py ✗ Not found
  → Search: ~/.ai/tools/my_tool.py ✓ Found
  → Return: ~/.ai/tools/my_tool.py
```

---

## Metadata Validation

Located in: `kiwi_mcp/utils/validators.py`

### ValidationManager

```python
class ValidationManager:
    @staticmethod
    def validate_tool_metadata(meta: dict) -> dict:
        """Validate tool metadata."""
        
        required_fields = ["name", "version", "tool_type", "executor_id", "category"]
        
        for field in required_fields:
            if field not in meta or not meta[field]:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate version format (semver)
        if not re.match(r'^\d+\.\d+\.\d+$', meta["version"]):
            raise ValueError(f"Invalid version format: {meta['version']}")
        
        # Validate tool_type
        if meta["tool_type"] not in ["primitive", "python", "api", "mcp_tool"]:
            raise ValueError(f"Invalid tool_type: {meta['tool_type']}")
        
        return meta
```

---

## Output Management

Located in: `kiwi_mcp/utils/output_manager.py`

### OutputManager

```python
class OutputManager:
    def __init__(self, project_path: Path):
        self.output_dir = project_path / ".ai" / "outputs" / "tools"
    
    def save(self, tool_name: str, result: dict) -> str:
        """Save tool output to file."""
        
        tool_dir = self.output_dir / tool_name
        tool_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = tool_dir / f"output_{timestamp}.json"
        
        # Write result
        output_file.write_text(json.dumps(result, indent=2))
        
        # Keep only last 10 outputs
        all_outputs = sorted(tool_dir.glob("output_*.json"))
        for old_file in all_outputs[:-10]:
            old_file.unlink()
        
        return str(output_file)
```

---

## Dependencies

### Auto-Detection

Python imports are detected and tracked:

```python
# This import is auto-detected
import requests
from datetime import datetime
from mylib import helper

# Auto-detected dependencies:
# - requests
# - datetime (stdlib, skipped)
# - mylib (local, skipped)
```

### Detection Algorithm

```python
def extract_imports(file_path: Path) -> set[str]:
    """Extract all imports from Python file."""
    
    import ast
    tree = ast.parse(file_path.read_text())
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                imports.add(module)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]
                imports.add(module)
    
    # Filter out stdlib and local imports
    return imports - STDLIB_MODULES - {"lib"}
```

---

## Performance Considerations

### Search Performance

- **Current:** O(n) - Linear scan of all files
- **Bottleneck:** Parsing metadata from every file
- **Future:** Vector embeddings for semantic search

### Execution Performance

- **Chain Resolution:** O(depth) where depth = executor chain depth
- **Typical:** 2-3 resolves (tool → runtime → primitive)
- **Overhead:** < 10ms per execution

### Memory Usage

- **Per Tool:** ~100KB (file content + metadata)
- **Per Search:** ~10MB (indexes all tools in RAM)
- **Future:** Use database + vector indexes

---

## Limitations & TODOs

### Current

1. ❌ **No Database** - Files only, not scalable
2. ❌ **No Auto-Dependency Install** - Manual management
3. ❌ **No Venv Isolation** - Runs in system Python
4. ❌ **No Registry Support** - Local only
5. ❌ **No Tool Creation API** - Manual file creation

### Planned (Future Phases)

1. ✅ Database tables (tools, tool_versions, tool_version_files)
2. ✅ Registry sync (publish, download)
3. ✅ Venv management per tool
4. ✅ Auto-dependency installation
5. ✅ Tool creation via API

---

## See Also

- `kiwi_mcp/handlers/tool/handler.py` - ToolHandler implementation
- `kiwi_mcp/primitives/executor.py` - Executor logic
- `kiwi_mcp/schemas.py` - Metadata extraction
- `kiwi_mcp/utils/resolvers.py` - Tool resolution
- `kiwi_mcp/utils/validators.py` - Validation
