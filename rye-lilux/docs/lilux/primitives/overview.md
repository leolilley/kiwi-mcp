**Source:** Original implementation: `kiwi_mcp/primitives/` in kiwi-mcp

# Lilux Primitives Overview

## What are Primitives?

The `primitives/` module contains the **core execution and support modules** of the Lilux microkernel.

**Important distinction:**
- **Execution Primitives** (2) - Actually execute tools via shell or HTTP
- **Support Modules** (3) - Help the execution pipeline (validation, integrity, locking)

## Execution Primitives (2)

These are the **only modules that execute code**. All tools eventually route to one of these:

### 1. **SubprocessPrimitive** (`subprocess.py`)

Execute shell commands and scripts.

**What it does:**
- Run shell commands (bash, python, node, etc.)
- Capture stdout/stderr
- Handle timeouts
- Resolve environment variables

**Example:**
```python
result = await subprocess.execute({
    "command": "python",
    "args": ["script.py", "--verbose"],
    "env": {"DEBUG": "1"},
    "cwd": "/home/user/project",
    "timeout": 300
})
# SubprocessResult(success=True, stdout="Hello", return_code=0)
```

**See:** [[subprocess]]

### 2. **HttpClientPrimitive** (`http_client.py`)

Make HTTP requests with retry logic.

**What it does:**
- Send GET, POST, PUT, DELETE requests
- Handle retries with exponential backoff
- Authenticate (API keys, OAuth)
- Support streaming responses

**Example:**
```python
result = await http_client.execute({
    "method": "POST",
    "url": "https://api.example.com/data",
    "headers": {"Authorization": "Bearer token"},
    "body": {"key": "value"},
    "timeout": 30
})
# HttpResult(success=True, status_code=200, body={...})
```

**See:** [[http-client]]

## Support Modules (3)

These modules **help the execution pipeline** but don't execute tools themselves:

### 3. **ChainValidator** (`chain_validator.py`)

Validate executor chains before execution.

**What it does:**
- Check parent→child schema compatibility
- Detect invalid tool chains
- Provide validation errors before execution

**See:** [[chain-validator]]

### 4. **IntegrityVerifier** (`integrity.py`)

Hash and verify content integrity.

**What it does:**
- Compute SHA256 hashes
- Verify tools haven't been modified
- Enable content-addressed validation

**See:** [[integrity]]

### 5. **Lockfile** (`lockfile.py`)

Manage reproducible execution with pinned versions.

**What it does:**
- Pin exact tool versions
- Store resolved chains
- Enable reproducible execution

**See:** [[lockfile]]

## Architecture Summary

```
Tool Execution
    │
    └─→ PrimitiveExecutor
        │
        ├─→ ChainValidator     (support: validates chain)
        ├─→ IntegrityVerifier  (support: checks hashes)
        │
        └─→ Execute via:
            ├─→ SubprocessPrimitive  (execution)
            └─→ HttpClientPrimitive  (execution)
```

## Module Summary Table

| Module | Type | Purpose |
|--------|------|---------|
| `subprocess.py` | **Execution** | Run shell commands |
| `http_client.py` | **Execution** | Make HTTP requests |
| `chain_validator.py` | Support | Validate executor chains |
| `integrity.py` | Support | Verify content hashes |
| `lockfile.py` | Support | Pin versions for reproducibility |

## Key Design Principles

1. **Only 2 execution paths:** Everything routes to subprocess or http_client
2. **Support modules don't execute:** They validate, verify, and track
3. **Minimal by design:** Primitives are intentionally simple
4. **Structured results:** All return dataclasses, no exceptions

## Standard Interface

All modules follow consistent patterns:

```python
# Execution primitives
class SubprocessPrimitive:
    async def execute(self, config: dict) -> SubprocessResult:
        pass

# Support modules
class ChainValidator:
    def validate_chain(self, chain: list) -> ValidationResult:
        pass
```

## Related Documentation

- [[subprocess]] - Shell execution details
- [[http-client]] - HTTP client details
- [[chain-validator]] - Chain validation
- [[integrity]] - Integrity verification
- [[lockfile]] - Version locking
- [[../runtime-services/overview]] - Runtime services (env resolver, auth)
