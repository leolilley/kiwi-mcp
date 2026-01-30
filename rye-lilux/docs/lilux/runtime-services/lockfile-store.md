**Source:** Original implementation: `kiwi_mcp/runtime/lockfile_store.py` in kiwi-mcp

# LockfileStore Service

## Purpose

Manage lockfile storage with hierarchical project/user scopes. LockfileStore handles the persistence layer for reproducible tool execution.

## Storage Hierarchy

LockfileStore maintains two levels of storage:

```
Project-level (highest priority)
.ai/lockfiles/
├── category/
│   └── tool_name@version.lock.json
│   └── tool_name@version.{chain_hash}.lock.json
└── .index.json

User-level (fallback)
~/.ai/lockfiles/
├── category/
│   └── tool_name@version.lock.json
└── .index.json
```

**Resolution:** Project lockfiles override user lockfiles.

## Key Classes

### LockfileStore

The lockfile storage service:

```python
class LockfileStore:
    def __init__(
        self,
        project_root: Optional[Path] = None,
        userspace_root: Optional[Path] = None
    ):
        """Initialize with project and user root paths."""
    
    def freeze_chain(
        self,
        root_tool: Dict[str, Any],
        resolved_chain: List[Dict[str, Any]],
        category: str
    ) -> Lockfile:
        """Create and save lockfile from resolved chain."""
    
    def get_lockfile(
        self,
        tool_id: str,
        version: str,
        category: str
    ) -> Optional[Lockfile]:
        """Retrieve lockfile (project takes precedence)."""
    
    def validate_lockfile(
        self,
        lockfile: Lockfile,
        resolved_chain: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Verify lockfile against current resolved chain."""
    
    def list_lockfiles(
        self,
        category: Optional[str] = None
    ) -> List[LockfileMetadata]:
        """List all available lockfiles."""
```

### LockfileMetadata

Metadata about a stored lockfile:

```python
@dataclass
class LockfileMetadata:
    tool_id: str              # Tool identifier
    version: str              # Tool version
    category: str             # Category (e.g., "runtimes")
    chain_hash: str           # Hash of the resolved chain
    path: Path                # Full path to lockfile
    scope: Literal["project", "user"]  # Where stored
    created_at: str           # ISO timestamp
    last_validated: Optional[str] = None  # Last validation time
```

### ValidationResult

Result of lockfile validation:

```python
@dataclass
class ValidationResult:
    is_valid: bool                    # Whether lockfile is valid
    issues: List[str] = []            # Validation errors
    lockfile: Optional[Lockfile] = None
```

## File Format

### Lockfile Structure

```json
{
  "lockfile_version": 1,
  "generated_at": "2026-01-30T12:00:00Z",
  "root": {
    "tool_id": "python_runtime",
    "version": "1.0.0",
    "integrity": "abc123..."
  },
  "resolved_chain": [
    {
      "tool_id": "system_python",
      "version": "3.9.0",
      "integrity": "def456...",
      "executor": "subprocess"
    }
  ],
  "registry": {
    "url": "https://registry.example.com",
    "fetched_at": "2026-01-30T12:00:00Z"
  }
}
```

### Index Structure

```json
{
  "project": {
    "runtimes": {
      "python": {
        "v1.0.0": {
          "chain_hash": "xyz789",
          "created_at": "2026-01-30T12:00:00Z",
          "last_validated": "2026-01-30T12:00:00Z"
        }
      }
    }
  },
  "user": {
    "runtimes": { ... }
  }
}
```

## Usage Pattern

### Freeze a Chain (Create Lockfile)

```python
from lilux.runtime import LockfileStore

store = LockfileStore(project_root="/home/user/project")

# Define root tool
root_tool = {
    "tool_id": "python_runtime",
    "version": "1.0.0",
    "manifest": {...}
}

# Define resolved chain
resolved_chain = [
    {
        "tool_id": "system_python",
        "version": "3.9.0",
        "executor": "subprocess"
    }
]

# Freeze the chain (creates + saves lockfile)
lockfile = store.freeze_chain(
    root_tool=root_tool,
    resolved_chain=resolved_chain,
    category="runtimes"
)

# Lockfile saved to: .ai/lockfiles/runtimes/python_runtime@1.0.0.lock.json
```

### Get Existing Lockfile

```python
# Retrieve lockfile (project takes precedence)
lockfile = store.get_lockfile(
    tool_id="python_runtime",
    version="1.0.0",
    category="runtimes"
)

if lockfile:
    print(f"Found lockfile with {len(lockfile.resolved_chain)} entries")
else:
    print("No lockfile found")
```

### Validate Lockfile

```python
# Get stored lockfile
lockfile = store.get_lockfile("python_runtime", "1.0.0", "runtimes")

# Validate against current chain
current_chain = [
    {
        "tool_id": "system_python",
        "version": "3.9.0",
        "executor": "subprocess"
    }
]

result = store.validate_lockfile(lockfile, current_chain)

if result.is_valid:
    print("✓ Lockfile valid")
else:
    for issue in result.issues:
        print(f"✗ {issue}")
```

### List All Lockfiles

```python
# List lockfiles in specific category
lockfiles = store.list_lockfiles(category="runtimes")

for metadata in lockfiles:
    print(f"{metadata.tool_id} v{metadata.version}")
    print(f"  Scope: {metadata.scope}")
    print(f"  Created: {metadata.created_at}")
    print(f"  Last validated: {metadata.last_validated}")
```

## Architecture Role

LockfileStore is part of the **persistence layer**:

1. **Lockfile storage** - Save and retrieve lockfiles
2. **Hierarchical scopes** - Project and user levels
3. **Index management** - Fast lookups
4. **Validation** - Verify lockfile freshness
5. **Stale cleanup** - Remove old lockfiles

## RYE Relationship

RYE uses LockfileStore when:
- Executing a tool that should be reproducible
- Need to lock specific versions
- Verify chain hasn't changed

**Pattern:**
```python
# RYE's executor
store = LockfileStore(project_root=project_path)

# Get lockfile if exists
lockfile = store.get_lockfile(
    tool_id=tool.id,
    version=tool.version,
    category="runtimes"
)

if lockfile:
    # Validate lockfile
    result = store.validate_lockfile(lockfile, resolved_chain)
    if result.is_valid:
        # Use locked versions
        pin_versions(lockfile.resolved_chain)
    else:
        # Lockfile is stale, regenerate
        lockfile = store.freeze_chain(root_tool, resolved_chain, category)
```

See `[[rye/universal-executor/overview]]` for executor integration.

## Scope Precedence

Project-level lockfiles take precedence:

```
Execution Flow:
1. Check .ai/lockfiles/ (project)
2. If found and valid, use it
3. If not found, check ~/.ai/lockfiles/ (user)
4. If found and valid, use it
5. If not found or invalid, generate new one
```

Example:

```python
store = LockfileStore(project_root="/home/user/project")

# Try to get lockfile
# 1. Checks: /home/user/project/.ai/lockfiles/runtimes/python@1.0.0.lock.json
# 2. If not found, checks: ~/.ai/lockfiles/runtimes/python@1.0.0.lock.json
# 3. Returns first match or None

lockfile = store.get_lockfile("python", "1.0.0", "runtimes")
```

## Chain Hashing

LockfileStore can store multiple lockfiles for same tool version:

```
python@1.0.0.lock.json                  # Default chain
python@1.0.0.xyz789abc.lock.json        # Alternative chain 1
python@1.0.0.def456ghi.lock.json        # Alternative chain 2
```

Each unique resolved chain gets a hash:

```python
chain_hash = compute_chain_hash([
    {"tool_id": "system_python", "version": "3.9.0"},
    {"tool_id": "subprocess_executor", "version": "1.0.0"}
])
# Returns: "xyz789abc" (first 9 chars)

lockfile_path = ".ai/lockfiles/runtimes/python@1.0.0.xyz789abc.lock.json"
```

This enables:
- Multiple valid chains for same tool
- Different execution environments
- Environment-specific lockfiles

## Index Caching

LockfileStore caches index in memory for speed:

```python
store = LockfileStore(project_root="/home/user/project")

# First call - loads index from disk
lockfiles = store.list_lockfiles()  # Slow

# Second call - uses cached index
lockfiles = store.list_lockfiles()  # Fast
```

Invalidate cache when needed:

```python
# After creating/modifying lockfile
store.freeze_chain(...)

# Index is automatically updated
lockfiles = store.list_lockfiles()  # Fresh
```

## Validation Errors

### Entry Not Found

```python
result = store.validate_lockfile(lockfile, resolved_chain)

# Lockfile entry has tool that's no longer available
result.is_valid  # False
result.issues  # ["Tool 'old_tool' v1.0.0 not in resolved chain"]
```

### Version Mismatch

```python
result = store.validate_lockfile(lockfile, resolved_chain)

# Lockfile specifies v1.0.0, but resolved chain has v1.1.0
result.is_valid  # False
result.issues  # ["Tool 'python' version mismatch: locked 1.0.0 vs 1.1.0"]
```

### Integrity Changed

```python
result = store.validate_lockfile(lockfile, resolved_chain)

# Tool content changed since lockfile created
result.is_valid  # False
result.issues  # ["Tool 'python' integrity hash mismatch"]
```

## Stale Lockfile Pruning

LockfileStore can remove old lockfiles:

```python
# Remove lockfiles not validated in 30 days
store.prune_stale(max_age_days=30)

# Logs what was removed
# Deleted: .ai/lockfiles/runtimes/old_tool@1.0.0.lock.json
```

## Testing

```python
import pytest
from lilux.runtime import LockfileStore
from pathlib import Path

def test_freeze_and_retrieve(tmp_path):
    """Test creating and retrieving lockfile."""
    store = LockfileStore(project_root=tmp_path)
    
    root = {
        "tool_id": "test",
        "version": "1.0.0",
        "manifest": {"a": 1}
    }
    
    chain = [
        {"tool_id": "dep", "version": "1.0.0", "executor": "subprocess"}
    ]
    
    # Freeze
    lockfile = store.freeze_chain(root, chain, "test")
    
    # Retrieve
    retrieved = store.get_lockfile("test", "1.0.0", "test")
    
    assert retrieved is not None
    assert retrieved.root.tool_id == "test"
    assert len(retrieved.resolved_chain) == 1

def test_project_takes_precedence(tmp_path, home_path):
    """Project lockfiles override user lockfiles."""
    # User has old lockfile
    user_store = LockfileStore(userspace_root=home_path)
    user_store.freeze_chain(
        root={"tool_id": "test", "version": "1.0.0", "manifest": {}},
        resolved_chain=[],
        category="test"
    )
    
    # Project has newer lockfile
    project_store = LockfileStore(project_root=tmp_path, userspace_root=home_path)
    project_store.freeze_chain(
        root={"tool_id": "test", "version": "1.0.0", "manifest": {}},
        resolved_chain=[],
        category="test"
    )
    
    # Retrieve - should get project version
    lockfile = project_store.get_lockfile("test", "1.0.0", "test")
    
    assert lockfile.lockfile_version == 1
```

## Best Practices

### 1. Always Create Lockfiles for Reproducibility

```python
# When deploying or sharing tool chains
lockfile = store.freeze_chain(
    root_tool=tool,
    resolved_chain=chain,
    category="runtimes"
)
```

### 2. Validate Before Use

```python
lockfile = store.get_lockfile(tool_id, version, category)
if lockfile:
    result = store.validate_lockfile(lockfile, current_chain)
    if not result.is_valid:
        # Regenerate
        lockfile = store.freeze_chain(...)
```

### 3. Commit Project Lockfiles

```bash
# Version control
git add .ai/lockfiles/
git commit -m "Lock tool dependencies"
```

## Limitations and Design

### By Design (Not a Bug)

1. **Local storage only**
   - No network sync
   - Project and user directories only

2. **Manual validation**
   - Doesn't auto-validate on load
   - Call `validate_lockfile()` explicitly

3. **No automatic cleanup**
   - Call `prune_stale()` manually
   - Or use separate maintenance job

## Next Steps

- See auth store: `[[lilux/runtime-services/auth-store]]`
- See env resolver: `[[lilux/runtime-services/env-resolver]]`
- See primitives: `[[lilux/primitives/overview]]`
