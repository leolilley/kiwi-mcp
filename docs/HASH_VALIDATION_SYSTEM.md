# Hash Validation System

**Date**: 2026-01-26  
**Status**: ✅ Implemented (path-based validation in progress)  
**Purpose**: Content-addressed integrity verification for tools, directives, and knowledge entries

---

## Overview

The hash validation system provides tamper-resistant integrity verification for all Kiwi MCP items (tools, directives, and knowledge entries). Each item is signed with a cryptographic hash that changes if the content or location is modified, requiring revalidation before execution.

### Key Principles

1. **Content-Addressed Identity**: The hash uniquely identifies the item's content and metadata
2. **Tamper Detection**: Any modification invalidates the signature
3. **Location Awareness**: File location is included in the hash (planned)
4. **Revalidation Required**: Modified or moved items must be re-signed before use

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Hash Validation Flow                        │
└─────────────────────────────────────────────────────────────┘

Sign Operation:
  File Content → compute_unified_integrity() → Hash
                ↓
  MetadataManager.sign_content_with_hash() → Signed File

Run Operation:
  Signed File → Extract stored hash
                ↓
  compute_unified_integrity() → Compute current hash
                ↓
  Compare hashes → Pass/Fail validation
```

### Core Modules

| Module | Responsibility |
|--------|---------------|
| `kiwi_mcp/primitives/integrity.py` | Canonical hash computation functions |
| `kiwi_mcp/utils/metadata_manager.py` | Signature formatting and hash extraction |
| `kiwi_mcp/primitives/integrity_verifier.py` | Verification logic and caching |
| `kiwi_mcp/handlers/*/handler.py` | Sign and verify operations per item type |

---

## Hash Computation

### Unified Integrity Function

All items use `compute_unified_integrity()` which delegates to type-specific functions:

```python
def compute_unified_integrity(
    item_type: str,
    item_id: str,
    version: str,
    file_content: str,
    file_path: Path,
    metadata: Optional[Dict] = None
) -> str:
    """Compute SHA256 integrity hash (64 characters)"""
```

### What's Included in Hashes

#### Tools

**Current State:**
- `tool_id`: Tool identifier
- `version`: Semver version string
- `manifest`: Tool manifest (executor, parameters, etc.)
- `files`: List of `{path: filename, sha256: content_hash}`

**Note**: Currently only filename is included, not full path.

**Planned**: Include relative path from base directory (e.g., `"core/api/my_tool.py"`).

#### Directives

**Current State:**
- `directive_name`: Directive identifier
- `version`: Semver version string
- `xml_hash`: SHA256 of XML directive content
- `metadata`: Optional metadata dict (currently `None`)

**Note**: File path is not currently included.

**Planned**: Include relative path from base directory (e.g., `"core/orchestration/my_directive.md"`).

#### Knowledge

**Current State:**
- `zettel_id`: Knowledge entry identifier
- `version`: Semver version string
- `content_hash`: SHA256 of markdown content
- `metadata`: Dict with `category`, `entry_type`, `tags`

**Note**: Category is extracted from file path, but full relative path is not included.

**Planned**: Include full relative path from base directory (e.g., `"architecture/patterns/api-design.md"`).

### Hash Computation Process

1. **Extract Content**: Remove existing signature before hashing
2. **Build Payload**: Create canonical JSON with sorted keys
3. **Compute Hash**: SHA256 of canonical JSON string
4. **Return**: 64-character hex digest

```python
# Example payload structure
payload = {
    "tool_id": "my_tool",
    "version": "1.0.0",
    "manifest": {...},
    "files": [{"path": "my_tool.py", "sha256": "abc123..."}],
    "location_path": "core/api/my_tool.py"  # Planned
}

canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
hash = hashlib.sha256(canonical.encode()).hexdigest()
```

---

## Signatures

### Signature Format

Signatures are embedded in files using item-type-specific formats:

**Directives** (XML in Markdown):
```markdown
<!-- kiwi-mcp:validated:2026-01-26T12:00:00Z:96440106d21b93926bd00feca333b138871a2ec959f2fe5a444d86bf0e5c58e0 -->
```

**Tools** (Python/YAML):
```python
# kiwi-mcp:validated:2026-01-26T12:00:00Z:96440106d21b93926bd00feca333b138871a2ec959f2fe5a444d86bf0e5c58e0
```

**Knowledge** (HTML comment at top, before frontmatter):
```markdown
<!-- kiwi-mcp:validated:2026-01-26T12:00:00Z:96440106d21b93926bd00feca333b138871a2ec959f2fe5a444d86bf0e5c58e0 -->
---
title: Entry Title
zettel_id: 20260126-example
---
Content here...
```

### Signature Structure

```
kiwi-mcp:validated:TIMESTAMP:HASH
```

- `TIMESTAMP`: ISO 8601 UTC timestamp (e.g., `2026-01-26T12:00:00Z`)
- `HASH`: 64-character SHA256 integrity hash

### Signing Process

1. **Validate Content**: Ensure item structure is valid
2. **Remove Old Signature**: Strip existing signature from content
3. **Compute Hash**: Call `compute_unified_integrity()` on content without signature
4. **Add Signature**: Insert new signature at top of file
5. **Write File**: Save signed content

```python
# Remove existing signature
content_without_sig = strategy.remove_signature(file_content)

# Compute integrity hash
content_hash = compute_unified_integrity(
    item_type="tool",
    item_id=tool_name,
    version=version,
    file_content=content_without_sig,
    file_path=file_path
)

# Add signature
signed_content = MetadataManager.sign_content_with_hash(
    "tool", content_without_sig, content_hash, file_path=file_path
)
```

---

## Verification

### Verification Flow

When an item is executed (run action):

1. **Extract Stored Hash**: Read signature from file
2. **Compute Current Hash**: Recompute integrity hash
3. **Compare**: If hashes match, validation passes
4. **Fail if Mismatch**: Return error requiring re-signing

```python
# Extract stored hash from signature
stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=file_path)

# Compute current hash
computed_hash = compute_unified_integrity(
    item_type="tool",
    item_id=tool_name,
    version=version,
    file_content=file_content,
    file_path=file_path
)

# Verify
if computed_hash != stored_hash:
    return {
        "error": "Content has been modified since last validation",
        "solution": "Run execute(action='sign', ...) to re-validate"
    }
```

### Integrity Verifier

The `IntegrityVerifier` class provides centralized verification:

```python
from kiwi_mcp.primitives.integrity_verifier import IntegrityVerifier

verifier = IntegrityVerifier()
result = verifier.verify_single_file(
    item_type="tool",
    item_id="my_tool",
    version="1.0.0",
    file_path=file_path,
    stored_hash=stored_hash
)

if result.success:
    # Validation passed
    pass
else:
    # Validation failed
    print(result.error)
```

**Features:**
- **Caching**: Previously verified hashes are cached
- **Fail-Fast**: Known-bad hashes are tracked
- **Chain Verification**: Can verify entire execution chains

---

## Path-Based Validation (Planned)

### Current Behavior

| Item Type | Path Included | Behavior |
|-----------|---------------|----------|
| Tools | Filename only | Moving to different directory with same filename = same hash |
| Directives | None | Moving anywhere = same hash |
| Knowledge | Category only | Moving to different category = different hash |

### Planned Behavior

All item types will include **relative path from base directory** in the hash:

- **Tools**: `"core/api/my_tool.py"` → Moving anywhere = different hash
- **Directives**: `"core/orchestration/my_directive.md"` → Moving anywhere = different hash
- **Knowledge**: `"architecture/patterns/api-design.md"` → Moving anywhere = different hash

### Implementation

1. **Add `extract_location_path()` helper** in `kiwi_mcp/utils/paths.py`
   - Returns relative path from `.ai/{type}/` or `~/.ai/{type}/`
   - Normalizes to forward slashes

2. **Update integrity functions** in `kiwi_mcp/primitives/integrity.py`
   - Add `location_path: Optional[str]` parameter
   - Include in canonical payload

3. **Update `compute_unified_integrity()`** in `kiwi_mcp/utils/metadata_manager.py`
   - Extract location path using helper
   - Pass to integrity computation functions

### Benefits

- **Location Locking**: Items are tied to their location
- **Move Detection**: Any file move requires revalidation
- **Security**: Prevents unauthorized relocation of items
- **Consistency**: All item types behave the same way

---

## Revalidation

### When Revalidation is Required

1. **Content Modified**: Any change to file content
2. **Metadata Changed**: Version, category, tags, etc. updated
3. **File Moved**: Item relocated to different directory (planned)
4. **Signature Missing**: Item has no signature

### Revalidation Process

```python
# Re-sign an item
execute(
    item_type="tool",
    action="sign",
    item_id="my_tool",
    parameters={"location": "project"},
    project_path="/path/to/project"
)
```

The sign operation:
1. Validates content structure
2. Computes new integrity hash
3. Adds/updates signature
4. Saves file

### Backward Compatibility

- **Existing Signatures**: Will fail validation after path-based update (expected)
- **Graceful Handling**: System handles missing/invalid signatures gracefully
- **No Migration**: Items are re-validated on next sign operation

---

## Security Model

### Protection Against

1. **Tampering**: Content modifications are detected
2. **Unauthorized Changes**: Signature prevents direct file edits
3. **Location Spoofing**: Path-based validation prevents relocation (planned)
4. **Version Mismatch**: Version changes require re-signing

### Limitations

- **Signature Format**: Must be preserved (comments/frontmatter)
- **File System**: Relies on filesystem integrity
- **Clock Skew**: Timestamps are informational only (not validated)

---

## Usage Examples

### Signing a Tool

```python
# Tool handler automatically signs during create/update
execute(
    item_type="tool",
    action="create",
    item_id="my_tool",
    parameters={
        "content": "# Tool code...",
        "location": "project"
    },
    project_path="/path/to/project"
)
```

### Verifying Before Execution

```python
# Handlers automatically verify before run
execute(
    item_type="tool",
    action="run",
    item_id="my_tool",
    parameters={...},
    project_path="/path/to/project"
)

# If validation fails:
# {
#     "error": "Content has been modified since last validation",
#     "solution": "Run execute(action='sign', ...) to re-validate"
# }
```

### Manual Verification

```python
from kiwi_mcp.primitives.integrity_verifier import IntegrityVerifier
from kiwi_mcp.utils.metadata_manager import MetadataManager

file_content = file_path.read_text()
stored_hash = MetadataManager.get_signature_hash("tool", file_content, file_path=file_path)

verifier = IntegrityVerifier()
result = verifier.verify_single_file(
    item_type="tool",
    item_id="my_tool",
    version="1.0.0",
    file_path=file_path,
    stored_hash=stored_hash
)
```

---

## Testing

### Test Coverage

- **Unit Tests**: `tests/primitives/test_directive_knowledge_integrity.py`
- **Validation Tests**: `tests/unit/test_hash_validation.py`
- **Integration Tests**: `tests/integration/test_metadata_integration.py`

### Test Scenarios

1. ✅ Same content produces same hash
2. ✅ Content changes produce different hash
3. ✅ Version changes produce different hash
4. ✅ Signature extraction and formatting
5. ✅ Verification success/failure cases
6. 🔄 Path changes produce different hash (planned)

---

## Related Documentation

- [Centralized Verification Architecture](./CENTRALIZED_VERIFICATION.md) - Verification system design
- [Tool Chain Validation Design](./TOOL_CHAIN_VALIDATION_DESIGN.md) - Chain validation for tool execution
- [Permission Enforcement](./PERMISSION_ENFORCEMENT.md) - Directive permission system

---

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Hash computation | ✅ Complete | All item types supported |
| Signature formatting | ✅ Complete | Type-specific formats |
| Verification logic | ✅ Complete | Centralized in IntegrityVerifier |
| Path-based validation | 🔄 Planned | See plan: path-based_hash_validation |
| Chain verification | ✅ Complete | Tool execution chains |
| Caching | ✅ Complete | Verification result caching |

---

## Future Enhancements

1. **Path-Based Validation**: Include file location in all hashes
2. **Signature Chains**: Support chained signatures for dependencies
3. **Registry Sync**: Validate registry items match local signatures
4. **Batch Verification**: Verify multiple items efficiently
5. **Signature Revocation**: Support for invalidating signatures
