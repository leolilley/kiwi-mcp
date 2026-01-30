**Source:** Original implementation: `kiwi_mcp/primitives/subprocess.py` in kiwi-mcp

# SubprocessPrimitive

## Purpose

Execute shell commands and scripts in isolated environments with timeout protection, environment variable resolution, and comprehensive error handling.

## Key Classes

### SubprocessResult

Result of subprocess execution:

```python
@dataclass
class SubprocessResult:
    success: bool           # Whether exit code was 0
    stdout: str            # Standard output
    stderr: str            # Standard error
    return_code: int       # Process exit code
    duration_ms: int       # Total execution time
```

### SubprocessPrimitive

The executor primitive:

```python
class SubprocessPrimitive:
    async def execute(
        self, 
        config: Dict[str, Any], 
        params: Dict[str, Any]
    ) -> SubprocessResult:
        """Execute a subprocess command."""
```

## Configuration

### Required

- **`command`** (str): Executable name or path
  - Example: `"python"`, `"bash"`, `"/usr/bin/node"`

### Optional

- **`args`** (list): Command arguments
  - Example: `["script.py", "--verbose", "input.txt"]`
  
- **`env`** (dict): Environment variables
  - Will be merged with `os.environ` (unless >50 vars)
  - Supports `${VAR:-default}` syntax for defaults
  - Example: `{"DEBUG": "1", "LOG_LEVEL": "info"}`

- **`cwd`** (str): Working directory
  - Default: current working directory
  - Example: `"/home/user/project"`

- **`timeout`** (int): Timeout in seconds
  - Default: 300 seconds
  - Example: `30`

- **`capture_output`** (bool): Capture stdout/stderr
  - Default: `True`
  - If `False`, output goes to parent stdout/stderr

- **`input_data`** (str): Data to send to stdin
  - Default: None
  - Example: `"line1\nline2\n"`

## Example Usage

### Simple Command

```python
from lilux.primitives import SubprocessPrimitive

primitive = SubprocessPrimitive()

result = await primitive.execute(
    config={
        "command": "echo",
        "args": ["Hello world"]
    },
    params={}
)

assert result.success == True
assert result.stdout == "Hello world\n"
assert result.return_code == 0
```

### Python Script

```python
result = await primitive.execute(
    config={
        "command": "python",
        "args": ["script.py", "--input", "data.json"],
        "cwd": "/home/user/project",
        "env": {"DEBUG": "1"},
        "timeout": 60
    },
    params={}
)

if result.success:
    print(f"Output: {result.stdout}")
else:
    print(f"Error: {result.stderr}")
    print(f"Exit code: {result.return_code}")
```

### With Environment Variables

```python
result = await primitive.execute(
    config={
        "command": "bash",
        "args": ["-c", "echo $MESSAGE"],
        "env": {"MESSAGE": "Hello from env"}
    },
    params={}
)

assert result.stdout == "Hello from env\n"
```

### With Input Data (stdin)

```python
result = await primitive.execute(
    config={
        "command": "grep",
        "args": ["pattern"],
        "input_data": "line1\npattern\nline3"
    },
    params={}
)

assert "pattern" in result.stdout
```

## Architecture Role

SubprocessPrimitive is part of the **Lilux microkernel execution layer**:

1. **Dumb execution** - Just runs commands, no intelligence
2. **Async-first** - All execution is async (uses asyncio)
3. **Safe isolation** - Subprocess runs in separate process
4. **Comprehensive errors** - Never throws, returns structured results

## RYE Relationship

RYE's universal executor calls SubprocessPrimitive when:
- Tool's `executor` field is `"subprocess"`
- Tool's config defines a command to run

**Pattern:**
```python
# RYE does this
tool = get_tool("my_script_tool")
assert tool.executor == "subprocess"

result = await subprocess_primitive.execute(
    config=tool.config,
    params=rye_params
)
```

See `[[rye/categories/primitives]]` for tool definitions.

## Environment Variable Resolution

### Pattern: `${VAR:-default}`

SubprocessPrimitive resolves variables in commands and args:

```python
config = {
    "command": "python",
    "args": ["${SCRIPT_PATH:-script.py}"],
    "cwd": "${HOME}/projects"
}

# If SCRIPT_PATH not set, uses "script.py"
# If HOME="C:\Users\alice", uses "C:\Users\alice/projects"
```

### Variable Merging

- If `env` has <50 vars: merged with `os.environ`
- If `env` has >50 vars: used directly (assumed already complete from RYE's EnvResolver)

See `[[lilux/runtime-services/env-resolver]]` for how RYE provides environment.

## Error Handling

All errors are returned as `SubprocessResult`, never thrown:

### Command Not Found
```python
result = await subprocess.execute(
    config={"command": "nonexistent_command"},
    params={}
)

assert result.success == False
assert "not found" in result.stderr.lower()
assert result.return_code == -1
```

### Timeout
```python
result = await subprocess.execute(
    config={
        "command": "sleep",
        "args": ["30"],
        "timeout": 1
    },
    params={}
)

assert result.success == False
assert "timed out" in result.stderr.lower()
```

### Permission Denied
```python
result = await subprocess.execute(
    config={"command": "/root/private_script"},
    params={}
)

assert result.success == False
assert "Permission denied" in result.stderr
```

## Performance Metrics

`duration_ms` field tracks execution time:

```python
result = await subprocess.execute(config, params)
print(f"Execution took {result.duration_ms}ms")
```

Useful for:
- Performance monitoring
- SLA tracking
- Detecting slow operations

## Testing

SubprocessPrimitive is fully testable:

```python
import pytest
from lilux.primitives import SubprocessPrimitive

@pytest.mark.asyncio
async def test_echo_command():
    prim = SubprocessPrimitive()
    result = await prim.execute(
        config={"command": "echo", "args": ["test"]},
        params={}
    )
    assert result.success
    assert "test" in result.stdout
```

## Limitations and Design

### By Design (Not a Bug)

1. **No shell=True** 
   - Direct execution, not shell interpretation
   - Safer and more explicit

2. **No streaming**
   - Output captured after completion
   - For streaming, use `[[lilux/primitives/http-client]]`

3. **No shell pipes**
   - Use `bash -c "cmd1 | cmd2"` for pipes
   - Keeps primitive simple

4. **No interactive input**
   - Can only send stdin at start via `input_data`
   - For interactive tools, use `[[lilux/primitives/http-client]]` with WebSockets

### Security Notes

- Runs subprocess in separate process (OS-level isolation)
- No modification of parent process
- Can be sandboxed further by parent container
- RYE validates command before execution (trust model)

## Next Steps

- See runtime services: `[[lilux/runtime-services/env-resolver]]`
- See HTTP client: `[[lilux/primitives/http-client]]`
- See executor framework: `[[lilux/primitives/overview]]`
