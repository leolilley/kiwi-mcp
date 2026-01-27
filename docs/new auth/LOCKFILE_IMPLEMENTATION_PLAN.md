# Lockfile Implementation Plan

**Date:** 2026-01-26  
**Status:** Approved for Implementation  
**Goal:** Implement kernel-level lockfile store for reproducible tool execution

---

## Executive Summary

**Recommendation**: **Implement lockfiles as a kernel-level store** (similar to AuthStore), with a **narrower scope** than originally planned.

**Architecture**: Kernel-level `LockfileStore` with local-first storage  
**Storage Strategy**: Hybrid - local primary, optional registry sync  
**Rationale**: Lockfiles solve different problems than hash validation and align with the local-first, offline-capable architecture

---

## 1. Necessity Analysis: Hash Validation vs Lockfiles

### What Hash Validation Provides
- **Integrity**: Content hasn't been tampered with
- **Immediate verification**: Detects corruption/modification
- **Security**: Prevents malicious code injection

### What Hash Validation Doesn't Provide
- **Reproducibility**: Same tool name might resolve to different versions
- **Chain stability**: `python_runtime` could update between runs
- **Dependency freezing**: No guarantee same chain resolves tomorrow
- **Audit trail**: No record of what executed in production

### Real-World Scenarios Where Lockfiles Matter

**Scenario 1: Production Deployment**
```
Day 1: Tool "data_processor" resolves to chain:
  data_processor@1.2.0 → python_runtime@3.11 → subprocess@1.0

Day 30: python_runtime@3.12 released with breaking changes
  data_processor now resolves to:
  data_processor@1.2.0 → python_runtime@3.12 → subprocess@1.0
  
Result: Production breaks despite hash validation passing
```

**Scenario 2: Team Collaboration**
```
Developer A: Has python_runtime@3.11 locally
Developer B: Has python_runtime@3.12 locally

Same tool, same version, different execution chains
Hash validation: ✓ Both valid
Reproducibility: ✗ Different behavior
```

**Scenario 3: Regulatory/Audit Requirements**
```
Need to prove: "This exact code ran on these exact dates"

Hash validation: Proves content integrity
Lockfile: Proves entire execution chain, with timestamps
```

**Verdict**: **Lockfiles are necessary** for reproducibility, which is distinct from integrity. Hash validation and lockfiles are complementary, not redundant.

---

## 2. Architecture Decision: Kernel-Level vs Tool-Level

### Analysis Framework

| Aspect | Kernel-Level (AuthStore pattern) | Tool-Level (Registry pattern) |
|--------|----------------------------------|-------------------------------|
| **Availability** | Always available | Optional, can be disabled |
| **Offline support** | Yes, built-in | Depends on implementation |
| **Execution** | Direct API calls | Requires chain execution |
| **Access control** | Kernel-only | Exposed to agents |
| **Consistency** | Guaranteed | Depends on tool implementation |

### Lockfile Characteristics

**Similar to AuthStore:**
- ✓ Core system functionality (reproducibility is foundational)
- ✓ Should always work offline
- ✓ Sensitive to consistency (corrupted lockfiles break reproducibility)
- ✓ Not agent-facing (kernel decision, not user choice)

**Similar to Registry:**
- ✓ Can benefit from sharing (teams want shared lockfiles)
- ✓ Optional sync capability (can work purely locally)

### Decision: **Kernel-Level Store**

**Rationale:**
1. **Reproducibility is core**: Can't make it optional without breaking guarantees
2. **Offline-first**: Must work without network, like AuthStore
3. **Consistency critical**: Lockfile corruption has severe consequences
4. **Registry can enhance**: Kernel store can optionally sync via registry tool

**Architecture Pattern:**
```python
# Kernel-level store (always available)
kiwi_mcp/runtime/lockfile_store.py

# Optional registry sync (via tool)
.ai/tools/core/lockfile_sync.py  # Uses lockfile_store + http_client
```

---

## 3. Storage Strategy: Local-First with Optional Sync

### Proposed Structure

```
# Project-level lockfiles
.ai/lockfiles/
  {category}/
    {tool_name}@{version}.lock.json
    {tool_name}@{version}.{chain_hash}.lock.json  # Multiple chains if needed
  
# Userspace lockfiles (for global tools)
~/.ai/lockfiles/
  {category}/
    {tool_name}@{version}.lock.json

# Index for quick lookup
.ai/lockfiles/.index.json
```

### Hierarchical Storage Benefits

1. **Matches tool structure**: Lockfile next to tool concept (category-scoped)
2. **Handles versioning**: Multiple versions explicitly named
3. **Scales well**: Hundreds of tools organized by category
4. **No conflicts**: Category namespace prevents collisions
5. **Works offline**: Pure filesystem, no database

### Chain Hash Suffix (Optional)

For cases where same tool+version has multiple valid chains:

```
.ai/lockfiles/mcp/
  mcp_discover@1.0.0.lock.json                    # Default chain
  mcp_discover@1.0.0.abc123.lock.json            # Alternative chain
```

**Use case**: Environment-specific chains (Docker vs native, different Python versions)

### Index File Format

```json
{
  "version": "1",
  "lockfiles": {
    "mcp/mcp_discover@1.0.0": {
      "path": "mcp/mcp_discover@1.0.0.lock.json",
      "chain_hash": "abc123...",
      "created_at": "2025-01-26T10:00:00Z",
      "last_validated": "2025-01-26T12:00:00Z"
    }
  }
}
```

**Benefits**: Fast lookup without scanning filesystem

---

## 4. Implementation Design

### Core Components

#### 4.1 LockfileStore (Kernel-Level)

**File**: `kiwi_mcp/runtime/lockfile_store.py`

```python
class LockfileStore:
    """Kernel-level lockfile management (local-first)."""
    
    def __init__(self, project_root: Path, userspace_root: Path):
        self.project_lockfiles = project_root / ".ai/lockfiles"
        self.user_lockfiles = userspace_root / ".ai/lockfiles"
        self.index = self._load_index()
    
    # Core operations
    def freeze(self, tool_id: str, version: str, chain: ResolvedChain) -> Lockfile:
        """Create lockfile from resolved chain."""
        
    def save(self, lockfile: Lockfile, scope: Literal["project", "user"]) -> None:
        """Save lockfile to filesystem."""
        
    def load(self, tool_id: str, version: str, category: str) -> Optional[Lockfile]:
        """Load lockfile (project takes precedence over user)."""
        
    def validate_chain(self, lockfile: Lockfile, resolved_chain: ResolvedChain) -> ValidationResult:
        """Validate resolved chain matches lockfile."""
    
    # Advanced operations
    def list_lockfiles(self, category: Optional[str] = None) -> List[LockfileMetadata]:
        """List all lockfiles, optionally filtered by category."""
        
    def prune_stale(self, max_age_days: int = 90) -> int:
        """Remove lockfiles not validated recently."""
```

**Key Features:**
- Project and userspace support (project takes precedence)
- Index-based fast lookup
- Category-scoped organization
- Chain hash support for multiple chains per tool+version

#### 4.2 Integration with PrimitiveExecutor

**File**: `kiwi_mcp/primitives/executor.py` (update)

```python
class PrimitiveExecutor:
    def __init__(self, lockfile_store: LockfileStore, ...):
        self.lockfile_store = lockfile_store
    
    def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        use_lockfile: bool = False,  # Opt-in for now
        strict_mode: bool = False,   # Fail if validation fails
    ) -> ExecutionResult:
        
        # Resolve chain
        resolved_chain = self.resolve_chain(tool_name)
        
        # Lockfile validation (if enabled)
        if use_lockfile:
            lockfile = self.lockfile_store.load(
                tool_id=resolved_chain.root_tool_id,
                version=resolved_chain.root_version,
                category=resolved_chain.category
            )
            
            if lockfile:
                validation = self.lockfile_store.validate_chain(lockfile, resolved_chain)
                
                if not validation.is_valid:
                    if strict_mode:
                        raise LockfileValidationError(validation.errors)
                    else:
                        logger.warning(f"Lockfile mismatch: {validation.errors}")
                        # Continue with current chain
        
        # Execute chain (existing logic)
        return self._execute_chain(resolved_chain, params)
```

**Integration Points:**
- Opt-in validation (`use_lockfile` parameter)
- Warn-by-default, fail-on-strict mode
- Non-blocking (warnings don't stop execution)

#### 4.3 CLI Commands

**File**: `kiwi_mcp/cli/commands/lockfile.py` (new)

```python
@click.group()
def lockfile():
    """Manage tool lockfiles."""
    pass

@lockfile.command()
@click.argument('tool_name')
@click.option('--category', '-c', help='Tool category')
@click.option('--scope', type=click.Choice(['project', 'user']), default='project')
def freeze(tool_name: str, category: str, scope: str):
    """Create lockfile for a tool."""
    # Resolve chain
    # Create lockfile
    # Save to appropriate scope

@lockfile.command()
@click.argument('tool_name')
@click.option('--category', '-c')
def validate(tool_name: str, category: str):
    """Validate lockfile against current resolution."""
    # Load lockfile
    # Resolve current chain
    # Compare and report differences

@lockfile.command()
@click.option('--category', '-c')
def list(category: str):
    """List all lockfiles."""
    # Show lockfiles with metadata

@lockfile.command()
@click.option('--older-than', type=int, default=90)
def prune(older_than: int):
    """Remove stale lockfiles."""
    # Clean up old lockfiles
```

**Commands:**
- `kiwi lockfile freeze <tool>` - Create lockfile
- `kiwi lockfile validate <tool>` - Validate against current chain
- `kiwi lockfile list` - List all lockfiles
- `kiwi lockfile prune` - Remove stale lockfiles

#### 4.4 Optional Registry Sync (Future)

**File**: `.ai/tools/core/lockfile_sync.py` (future)

```python
"""
Tool that syncs lockfiles to/from registry.
Uses: lockfile_sync → http_client chain
"""

def sync_to_registry(lockfile_path: str) -> Dict[str, Any]:
    """Upload lockfile to registry."""
    # Uses http_client primitive
    # Stores in registry database
    
def sync_from_registry(tool_id: str, version: str) -> Optional[Lockfile]:
    """Download lockfile from registry."""
    # Uses http_client primitive
    # Returns lockfile data
```

**Future Enhancement**: Registry sync tool (post-registry decoupling)

---

## 5. Addressing Scaling Concerns

### Resolution of Each Concern

1. **Naming Conflicts** ✅  
   Solved by category hierarchy: `.ai/lockfiles/{category}/{tool}@{version}.lock.json`

2. **Versioning** ✅  
   Explicit in filename: `tool_name@1.2.0.lock.json`

3. **Chain Variations** ✅  
   Optional chain hash suffix: `tool@1.0.0.abc123.lock.json`

4. **Dependency Cascade** ⚠️  
   **Mitigation**: 
   - Validation warns (doesn't fail by default)
   - CLI command to bulk-update lockfiles
   - Index tracks last validation date

5. **Directory Structure** ✅  
   Category hierarchy prevents flat directory bloat

6. **Tool Location Disconnect** ✅  
   Same category structure as tools, easy mental model

7. **Registry Optional** ✅  
   Fully local-first, registry sync is enhancement

---

## 6. Use Cases and Benefits

### Primary Use Cases

1. **Production Deployments**
   - Freeze exact chain for production
   - Validate before deployment
   - Audit trail for compliance

2. **Team Collaboration**
   - Share lockfiles in version control
   - Ensure consistent execution across team
   - Onboarding: new developers get exact setup

3. **CI/CD Pipelines**
   - Strict mode for test reproducibility
   - Prevent flaky tests from dependency drift
   - Deterministic builds

4. **Debugging**
   - Reproduce bug reports: "Run with this lockfile"
   - Compare lockfiles: "What changed between v1 and v2?"

5. **Security Audits**
   - Prove exact code that ran
   - Detect unauthorized chain changes
   - Compliance with regulations (SOC2, HIPAA, etc.)

---

## 7. Implementation Phases

### Phase 1: Core Kernel Store (Week 1-2)
- [ ] Implement `LockfileStore` in `kiwi_mcp/runtime/lockfile_store.py`
- [ ] Filesystem storage with hierarchical structure
- [ ] Index management (`.index.json`)
- [ ] Unit tests for store operations
- [ ] Integration with existing `LockfileManager` code

**Deliverable**: Working kernel-level store with save/load operations

### Phase 2: Executor Integration (Week 2-3)
- [ ] Add `LockfileStore` to `PrimitiveExecutor.__init__()`
- [ ] Add `use_lockfile` parameter to `PrimitiveExecutor.execute()`
- [ ] Validation logic (warn-by-default, fail-on-strict)
- [ ] Integration tests with real chains
- [ ] Error handling and logging

**Deliverable**: Executor validates chains against lockfiles

### Phase 3: CLI Commands (Week 3-4)
- [ ] Create `kiwi_mcp/cli/commands/lockfile.py`
- [ ] Implement `kiwi lockfile freeze <tool>`
- [ ] Implement `kiwi lockfile validate <tool>`
- [ ] Implement `kiwi lockfile list`
- [ ] Implement `kiwi lockfile prune`
- [ ] CLI tests

**Deliverable**: Full CLI interface for lockfile management

### Phase 4: Documentation & Best Practices (Week 4)
- [ ] User guide: When to use lockfiles
- [ ] Team workflow documentation
- [ ] Migration guide from current state
- [ ] Examples for common scenarios
- [ ] Troubleshooting guide

**Deliverable**: Complete user documentation

### Phase 5: Registry Sync (Future - Post-Registry Decoupling)
- [ ] Design registry database schema for lockfiles
- [ ] Implement `lockfile_sync` tool in `.ai/tools/core/`
- [ ] HTTP API endpoints for lockfile upload/download
- [ ] CLI integration: `kiwi lockfile push/pull`
- [ ] Conflict resolution for shared lockfiles

**Deliverable**: Optional registry sync capability

---

## 8. Risks and Mitigations

### Risk 1: Lockfile Staleness
**Problem**: Lockfiles become outdated as dependencies update  
**Mitigation**: 
- Warn-by-default (don't fail)
- Index tracks last validation
- CLI command to update lockfiles in bulk
- Documentation on when to refresh

### Risk 2: Storage Bloat
**Problem**: Many lockfiles accumulate over time  
**Mitigation**:
- Prune command removes stale lockfiles
- Lockfiles are small (~1-5KB each)
- Category hierarchy keeps organized
- Index enables efficient queries

### Risk 3: Complexity Overhead
**Problem**: Another system to manage  
**Mitigation**:
- Opt-in for most use cases
- Only required for production/CI
- Simple CLI interface
- Clear documentation on when needed

### Risk 4: Merge Conflicts (Git)
**Problem**: Team lockfile changes conflict  
**Mitigation**:
- JSON format (easier to merge than binary)
- Category structure reduces overlap
- Tool to regenerate lockfiles
- Documentation on conflict resolution

---

## 9. Alternatives Considered

### Alternative A: Remove Lockfile Code
**Pros**: Simpler system, less maintenance  
**Cons**: No reproducibility guarantees, production risk  
**Verdict**: ❌ Insufficient for production use cases

### Alternative B: Registry-Only Storage
**Pros**: Centralized, queryable, deduplication  
**Cons**: Breaks offline-first principle, requires registry  
**Verdict**: ❌ Conflicts with architecture goals

### Alternative C: Single Project Lockfile (npm/pip style)
**Pros**: Simple, like package managers  
**Cons**: All tools share one file, harder to manage at scale  
**Verdict**: ❌ Doesn't match tool-per-file architecture

### Alternative D: Content-Addressed Storage
**Pros**: Perfect deduplication, no conflicts  
**Cons**: Hard to find lockfiles, poor UX  
**Verdict**: ⚠️ Good for future optimization, not primary

---

## 10. Technical Details

### Lockfile Format

Uses existing `Lockfile` dataclass from `kiwi_mcp/primitives/lockfile.py`:

```python
@dataclass
class Lockfile:
    lockfile_version: int
    generated_at: str
    root: LockfileRoot
    resolved_chain: List[LockfileEntry]
    registry: Optional[LockfileRegistry] = None
```

**Enhancements:**
- Add `category` field to `LockfileRoot`
- Add `chain_hash` field for multiple chains
- Preserve existing format for compatibility

### File Naming Convention

```
{category}/{tool_name}@{version}.lock.json
{category}/{tool_name}@{version}.{chain_hash}.lock.json  # Optional
```

**Examples:**
- `mcp/mcp_discover@1.0.0.lock.json`
- `mcp/mcp_discover@1.0.0.abc123def456.lock.json` (alternative chain)

### Index Schema

```json
{
  "version": "1",
  "updated_at": "2025-01-26T12:00:00Z",
  "lockfiles": {
    "mcp/mcp_discover@1.0.0": {
      "path": "mcp/mcp_discover@1.0.0.lock.json",
      "chain_hash": "abc123...",
      "created_at": "2025-01-26T10:00:00Z",
      "last_validated": "2025-01-26T12:00:00Z",
      "scope": "project"
    }
  }
}
```

### Integration with Existing Code

**Preserve**: `kiwi_mcp/primitives/lockfile.py` (263 lines)
- `LockfileManager` class remains
- `Lockfile` dataclass remains
- Tests remain valid

**Enhance**: Add `LockfileStore` wrapper
- Uses `LockfileManager` internally
- Adds filesystem management
- Adds index management
- Adds category/version handling

---

## 11. Migration Plan

### From Current State

**Current State:**
- `LockfileManager` exists but unused
- `PrimitiveExecutor.execute()` has unused `lockfile` parameter
- Tests exist and pass

**Migration Steps:**

1. **Week 1-2**: Implement kernel store
   - Create `LockfileStore` wrapper
   - No user impact (internal only)

2. **Week 3**: Add executor integration
   - Opt-in validation (default: off)
   - No breaking changes

3. **Week 4**: Add CLI commands
   - Users can start using lockfiles
   - Documentation available

4. **Week 5+**: General availability
   - Opt-in becomes recommended for production
   - Best practices documented

**Cleanup**: Existing `lockfile.py` code is **preserved and enhanced**, not removed. Tests already exist and pass.

---

## 12. Success Criteria

### Phase 1 (Core Store)
- ✅ `LockfileStore` saves/loads lockfiles correctly
- ✅ Hierarchical structure works
- ✅ Index management functional
- ✅ All unit tests pass

### Phase 2 (Executor Integration)
- ✅ Executor validates chains against lockfiles
- ✅ Warn-by-default works correctly
- ✅ Strict mode fails on mismatch
- ✅ Integration tests pass

### Phase 3 (CLI)
- ✅ All CLI commands work
- ✅ Freeze creates valid lockfiles
- ✅ Validate reports differences correctly
- ✅ List and prune work as expected

### Phase 4 (Documentation)
- ✅ User guide complete
- ✅ Examples provided
- ✅ Best practices documented
- ✅ Troubleshooting guide available

### Overall
- ✅ Works offline (no registry required)
- ✅ Scales to hundreds of tools
- ✅ No breaking changes to existing code
- ✅ Clear value proposition for users

---

## 13. References

- [TOOL_CHAIN_VALIDATION_DESIGN.md](./TOOL_CHAIN_VALIDATION_DESIGN.md) - Original design
- [HASH_VALIDATION_SYSTEM.md](./HASH_VALIDATION_SYSTEM.md) - Hash validation system
- [SUPABASE_DECOUPLING_PLAN.md](./new%20auth/SUPABASE_DECOUPLING_PLAN.md) - Registry decoupling
- [AUTH_STORE_IMPLEMENTATION.md](./new%20auth/AUTH_STORE_IMPLEMENTATION.md) - AuthStore pattern

---

## Conclusion

Lockfiles are necessary and complementary to hash validation. The kernel-level store approach provides reproducibility guarantees while maintaining the local-first, offline-capable architecture. This aligns with the AuthStore pattern and enables future registry sync without creating a dependency on it.

The implementation leverages existing code, follows established patterns, and provides clear value for production deployments, team collaboration, and regulatory compliance—use cases that hash validation alone cannot address.

---

_Generated: 2026-01-26_
