**Source:** Original implementation: `kiwi_mcp/primitives/lockfile.py` in kiwi-mcp

# Lockfile Primitive

## Purpose

Manage reproducible tool execution with pinned versions and integrity hashes. Lockfiles enable "lock dependencies" similar to package managers like npm or pip.

## Key Classes

### LockfileEntry

Single resolved entry in the chain:

```python
@dataclass
class LockfileEntry:
    tool_id: str              # Tool identifier
    version: str              # Semantic version (e.g., "1.2.3")
    integrity: str            # SHA256 hash of tool content
    executor: Optional[str]   # Executor type (subprocess, http_client, etc.)
```

### LockfileRoot

The root tool being locked:

```python
@dataclass
class LockfileRoot:
    tool_id: str              # Root tool identifier
    version: str              # Root version
    integrity: str            # Root integrity hash
```

### Lockfile

Complete lockfile structure:

```python
@dataclass
class Lockfile:
    lockfile_version: int                    # Format version
    generated_at: str                        # ISO timestamp
    root: LockfileRoot                       # Root tool
    resolved_chain: List[LockfileEntry]     # Full dependency chain
    registry: Optional[LockfileRegistry]    # Where tools came from
```

### LockfileManager

The executor:

```python
class LockfileManager:
    def create_lockfile(
        self,
        root_tool: Dict[str, Any],
        resolved_chain: List[Dict[str, Any]]
    ) -> Lockfile:
        """Create a lockfile from resolved chain."""
    
    def save_lockfile(self, lockfile: Lockfile, path: str) -> None:
        """Save lockfile to disk."""
    
    def load_lockfile(self, path: str) -> Lockfile:
        """Load lockfile from disk."""
    
    def verify_lockfile(self, lockfile: Lockfile) -> bool:
        """Verify all entries exist and have correct integrity."""
```

## The Problem: Version Drift

Without lockfiles:

```
Day 1: Run tool v1.0.0 → Works
Day 30: Tool upgraded to v1.1.0
Day 30: Run same tool → Different behavior!
```

With lockfiles:

```
Day 1: Create lockfile with v1.0.0
Day 30: Run tool with lockfile → Forces v1.0.0
Day 30: Same behavior guaranteed
```

## Example Lockfile Structure

```json
{
  "lockfile_version": 1,
  "generated_at": "2026-01-30T12:00:00Z",
  "root": {
    "tool_id": "data_pipeline",
    "version": "2.3.1",
    "integrity": "abc123def456abc123def456abc123def456abc123def456abc123def456abcd"
  },
  "resolved_chain": [
    {
      "tool_id": "csv_reader",
      "version": "1.0.0",
      "integrity": "xyz789abc123xyz789abc123xyz789abc123xyz789abc123xyz789abc123xyzd",
      "executor": "subprocess"
    },
    {
      "tool_id": "json_validator",
      "version": "2.1.0",
      "integrity": "pqr456stu789pqr456stu789pqr456stu789pqr456stu789pqr456stu789pqrd",
      "executor": "http_client"
    }
  ],
  "registry": {
    "url": "https://registry.example.com",
    "fetched_at": "2026-01-30T12:00:00Z"
  }
}
```

## Usage Pattern

### Create a Lockfile

```python
from lilux.primitives import LockfileManager
from lilux.primitives import compute_tool_integrity

manager = LockfileManager()

# Define root tool
root_tool = {
    "tool_id": "my_pipeline",
    "version": "1.0.0",
    "manifest": {...}
}

# Define resolved chain (all dependencies)
resolved_chain = [
    {
        "tool_id": "reader",
        "version": "1.0.0",
        "executor": "subprocess"
    },
    {
        "tool_id": "processor",
        "version": "2.1.0",
        "executor": "http_client"
    }
]

# Create lockfile
lockfile = manager.create_lockfile(root_tool, resolved_chain)

# Save to disk
manager.save_lockfile(lockfile, "my_pipeline.lock")
```

### Use a Lockfile

```python
# Load existing lockfile
lockfile = manager.load_lockfile("my_pipeline.lock")

# Verify all entries are valid
if not manager.verify_lockfile(lockfile):
    raise ValueError("Lockfile is stale or invalid")

# Use the lockfile to enforce versions
print(f"Must use {lockfile.root.tool_id} v{lockfile.root.version}")
for entry in lockfile.resolved_chain:
    print(f"  → {entry.tool_id} v{entry.version}")
```

### Verify Integrity

```python
lockfile = manager.load_lockfile("my_pipeline.lock")

# Get current tool from registry/cache
current_tool = get_tool("reader", "1.0.0")

# Compute current integrity
current_integrity = compute_tool_integrity(
    tool_id="reader",
    version="1.0.0",
    manifest=current_tool.manifest
)

# Verify against lockfile
stored_integrity = next(
    e.integrity for e in lockfile.resolved_chain 
    if e.tool_id == "reader"
)

if current_integrity != stored_integrity:
    raise ValueError("Tool has been modified since lockfile was created!")
```

## Architecture Role

Lockfiles are part of the **reproducibility layer**:

1. **Version pinning** - Lock exact versions
2. **Integrity verification** - Detect changes
3. **Provenance tracking** - Know where tools came from
4. **Chain verification** - Ensure all dependencies are available

## RYE Relationship

RYE uses lockfiles when:
- Executing a tool that has a `.lock` file
- Need to guarantee reproducibility
- Prevent accidental version upgrades

**Pattern:**
```python
# RYE checks for lockfile
lockfile_path = tool_path.with_suffix(".lock")
if lockfile_path.exists():
    lockfile = manager.load_lockfile(lockfile_path)
    # Enforce versions from lockfile
    for entry in lockfile.resolved_chain:
        pin_version(entry.tool_id, entry.version)
```

See `[[rye/universal-executor/overview]]` for executor integration.

## Lockfile vs Package Manager Analogy

| Aspect | npm | Lilux |
|--------|-----|-------|
| **Lock format** | package-lock.json | tool.lock |
| **What's locked** | npm packages | tool versions |
| **Integrity** | npm sha512 | SHA256 |
| **Generated** | `npm install` | `lilux lock create` |
| **Used** | `npm install` | RYE executor |

## File Format

Lockfiles are JSON:

```json
{
  "lockfile_version": 1,          // Format version
  "generated_at": "2026-01-30...",  // When created
  "root": { ... },                 // Root tool
  "resolved_chain": [ ... ],       // All dependencies
  "registry": { ... }              // Provenance
}
```

Key design:
- Human-readable (not binary)
- Version-forward compatible
- Can be committed to git
- Can be inspected manually

## Integrity Hashing

Integrity hashes are **deterministic SHA256**:

```python
# Same input = same hash (always)
hash1 = compute_tool_integrity(
    tool_id="my_tool",
    version="1.0.0",
    manifest={...},
    files=[...]
)

hash2 = compute_tool_integrity(
    tool_id="my_tool",
    version="1.0.0",
    manifest={...},
    files=[...]
)

assert hash1 == hash2  # Always true
```

Any change produces different hash:
- Change manifest? → Different hash
- Change version? → Different hash
- Change tool name? → Different hash
- Change file list? → Different hash

This enables detecting modifications.

## Best Practices

### 1. Commit Lockfiles

```bash
# DO: Commit to version control
git add my_tool.lock
git commit -m "Lock tool dependencies"

# This ensures reproducible builds
```

### 2. Regenerate Periodically

```python
# 1. Update tools
tool = update_tool("reader", "1.1.0")

# 2. Regenerate lockfile
lockfile = manager.create_lockfile(
    root_tool=tool,
    resolved_chain=[...]  # With new versions
)
manager.save_lockfile(lockfile, "my_tool.lock")

# 3. Commit new lockfile
```

### 3. Verify Before Use

```python
# Always verify lockfile before execution
if not manager.verify_lockfile(lockfile):
    raise ValueError("Lockfile is invalid")

# Then use it to pin versions
```

## Error Handling

### Stale Lockfile

```python
lockfile = manager.load_lockfile("my_tool.lock")

# Entry points to version that doesn't exist
if not manager.verify_lockfile(lockfile):
    raise ValueError("Lockfile is stale - entries no longer available")
```

### Missing Entry

```python
# Tool was added after lockfile created
try:
    entry = next(
        e for e in lockfile.resolved_chain 
        if e.tool_id == "new_tool"
    )
except StopIteration:
    raise ValueError("Tool not in lockfile - regenerate")
```

## Testing

```python
import pytest
from lilux.primitives import LockfileManager

def test_create_and_load_lockfile():
    manager = LockfileManager()
    
    root = {"tool_id": "test", "version": "1.0.0", "integrity": "abc123"}
    chain = [
        {"tool_id": "dep1", "version": "1.0.0", "integrity": "def456"}
    ]
    
    lockfile = manager.create_lockfile(root, chain)
    
    # Save and reload
    manager.save_lockfile(lockfile, "test.lock")
    loaded = manager.load_lockfile("test.lock")
    
    assert loaded.root.tool_id == "test"
    assert len(loaded.resolved_chain) == 1
```

## Next Steps

- See integrity: `[[lilux/primitives/integrity]]`
- See chain validator: `[[lilux/primitives/chain-validator]]`
- See RYE executor: `[[rye/universal-executor/overview]]`
