# Kiwi MCP Execution Pipeline - Current State & Issues

## Context
Kiwi MCP uses a chain-based execution model where tools resolve to chains like:
- `hello_world → python_runtime → subprocess` (Python scripts)
- `http_test → http_client` (HTTP requests)

The executor resolves chains from the registry, merges configs, validates integrity/schemas, then routes to the appropriate primitive (subprocess or http_client).

---

## ✅ FIXED: Subprocess/Python Execution Stall

### Problem
**Symptoms:**
- `execute` action with `action: "run"` hung indefinitely
- No timeout, no error, just "Aborted"
- Direct Python execution worked: `python hello_world.py --name "Test"`
- Chain resolution, validation, all succeeded
- But actual execution stalled forever

**Root Cause:**
The merged config for subprocess was: `{command: 'python3', args: []}`

When subprocess executed `python3` with NO script file path:
```bash
python3  # ← Started Python REPL, waited for input forever
```

The handler had the local file path but never passed it to the executor. The executor only had registry metadata (tool_id, version, manifest) but no file system path.

### Solution
**Files Modified:**
1. `/home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/tool/handler.py` (line ~460)
2. `/home/leo/projects/kiwi-mcp/kiwi_mcp/primitives/executor.py` (lines ~365-530)

**Changes:**

**1. Handler injects file path** (handler.py:458-463):
```python
# Before
result = await self.primitive_executor.execute(tool_meta["name"], params)

# After
exec_params = params.copy()
exec_params["_file_path"] = str(file_path)  # ← Inject local file path
result = await self.primitive_executor.execute(tool_meta["name"], exec_params)
```

**2. Executor builds subprocess config** (executor.py:493-530):
Added `_build_subprocess_config()` method that:
- Takes the file path from `params["_file_path"]`
- Inserts it as first arg: `args.insert(0, file_path)`
- Converts user params to CLI args: `--name TestUser` → `['--name', 'TestUser']`
- Filters out internal params (those starting with `_`)

**3. Executor routes to subprocess** (executor.py:366-372):
```python
if primitive_type == "subprocess":
    exec_config = self._build_subprocess_config(config, params)
    exec_params = {k: v for k, v in params.items() if not k.startswith("_")}
    result = await self.subprocess_primitive.execute(exec_config, exec_params)
```

### Result
✅ **Python/subprocess execution now works perfectly:**
```json
{
  "status": "success",
  "data": {
    "stdout": "Hello, KiwiMCP!\n",
    "stderr": "",
    "return_code": 0
  },
  "metadata": {
    "duration_ms": 64,
    "tool_type": "python",
    "primitive_type": "subprocess"
  }
}
```

---

## ❌ CURRENT ISSUE: HTTP Execution Failing

### Problem
**Symptoms:**
- HTTP tool execution fails with: `'NoneType' object has no attribute 'get'`
- Error occurs somewhere in the executor pipeline
- Chain resolves correctly: `http_test → http_client`
- Both tools have valid content hashes and are published

**Test Tool:**
```python
# /home/leo/projects/kiwi-mcp/.ai/tools/utility/http_test.py
__version__ = "1.0.0"
__tool_type__ = "api"
__executor_id__ = "http_client"

CONFIG = {
    "method": "GET",
    "url": "https://httpbin.org/json",
    "timeout": 10,
    "retry": {"max_attempts": 2, "backoff": "exponential"}
}
```

**Chain Resolution:**
```
0: http_test (type=api)
   version: 1.0.0
   content_hash: c712684b4624e03f...
1: http_client (type=primitive)
   version: 1.0.1
   content_hash: df09ac7813626251...
```

**Error Response:**
```json
{
  "status": "error",
  "error": "Execution failed: 'NoneType' object has no attribute 'get'",
  "metadata": {
    "duration_ms": 230,
    "tool_type": "api",
    "primitive_type": "unknown"
  }
}
```

### Current Code State
**Executor HTTP path** (executor.py:373-376):
```python
elif primitive_type == "http_client":
    # Remove internal params for HTTP (like _file_path)
    exec_params = {k: v for k, v in params.items() if not k.startswith("_")}
    result = await self.http_client_primitive.execute(config or {}, exec_params)
    exec_result = self._convert_http_result(result)
```

### Investigation Needed

**Hypothesis 1: Config merge returns None or empty dict**
- HTTP tools might not have configs in their manifests
- The `merge_configs()` might return `{}` or `None`
- HTTP primitive expects `config.get("url")` but config might be None

**Hypothesis 2: Manifest structure issue**
- Registry might not be returning manifest with `config` key
- The `terminal_manifest.get("config")` might be None
- This breaks the merge or validation step

**Hypothesis 3: NoneType is elsewhere**
- Could be in `_validate_runtime_params()`
- Could be in `_convert_http_result()` if result.metadata is None
- Could be in handler trying to access tool metadata

### Debug Steps Required

1. **Check merged config for http_test:**
   ```python
   chain = await resolver.resolve('http_test')
   merged = resolver.merge_configs(chain)
   # What is merged? {} or None or has 'url'?
   ```

2. **Check per-tool configs in chain:**
   ```python
   for tool in chain:
       manifest = tool.get('manifest', {})
       config = manifest.get('config')
       # Does http_test have CONFIG in manifest?
   ```

3. **Add logging to executor:**
   ```python
   logger.info(f"Config: {config}")
   logger.info(f"Config type: {type(config)}")
   logger.info(f"Primitive type: {primitive_type}")
   ```

4. **Run with traceback:**
   ```python
   try:
       result = await executor.execute('http_test', {})
   except Exception as e:
       traceback.print_exc()
   ```

---

## Files to Reference

### Key Files Modified
- `/home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/tool/handler.py` (858 lines)
- `/home/leo/projects/kiwi-mcp/kiwi_mcp/primitives/executor.py` (580 lines)

### Test Tools
- `/home/leo/projects/kiwi-mcp/.ai/tools/utility/hello_world.py` (✅ working)
- `/home/leo/projects/kiwi-mcp/.ai/tools/utility/http_test.py` (❌ failing)

### Primitives
- `/home/leo/projects/kiwi-mcp/.ai/tools/primitives/subprocess.py` (✅ working)
- `/home/leo/projects/kiwi-mcp/.ai/tools/primitives/http_client.py` (❌ not tested)

### Supporting Code
- `/home/leo/projects/kiwi-mcp/kiwi_mcp/primitives/subprocess.py` (176 lines)
- `/home/leo/projects/kiwi-mcp/kiwi_mcp/primitives/http_client.py` (206 lines)
- `/home/leo/projects/kiwi-mcp/kiwi_mcp/api/tool_registry.py` (507 lines)

---

## MCP Server Credentials (for testing)
```python
SUPABASE_URL = "https://mrecfyfjpwzrzxoiooew.supabase.co"
SUPABASE_SECRET_KEY = "sb_secret_OjHCg6z6kUo7MO49zzb4Xw_pBtPAQW8"
```

---

## Test Commands

### Working: Python/Subprocess
```python
# Via MCP
CallMcpTool(
    server="user-kiwi-mcp",
    toolName="execute",
    arguments={
        "item_type": "tool",
        "action": "run",
        "item_id": "hello_world",
        "parameters": {"name": "Test"},
        "project_path": "/home/leo/projects/kiwi-mcp"
    }
)
```

### Failing: HTTP
```python
# Via MCP
CallMcpTool(
    server="user-kiwi-mcp",
    toolName="execute",
    arguments={
        "item_type": "tool",
        "action": "run",
        "item_id": "http_test",
        "parameters": {},
        "project_path": "/home/leo/projects/kiwi-mcp"
    }
)
# Returns: 'NoneType' object has no attribute 'get'
```

---

## Next Steps

1. Debug the NoneType error - find the exact line
2. Check if http_test's CONFIG is being extracted and stored in manifest
3. Verify the merge_configs() returns proper data for HTTP tools
4. Fix any issues with HTTP config handling
5. Test end-to-end HTTP execution
6. Clean up test files

---

## Success Criteria

✅ Python subprocess execution works
❌ HTTP client execution fails with NoneType error
🎯 **Goal:** Both primitives working end-to-end with full integrity verification
