# Centralized Verification Architecture

## Summary

Successfully refactored the integrity verification system to centralize ALL verification logic in `IntegrityVerifier` while simplifying `MetadataManager` to handle ONLY signature formatting.

## Architecture Changes

### Before: Split Verification
```
MetadataManager.verify_signature() - Did BOTH format checking AND content verification
├─ Extract signature
├─ Parse hash
├─ Compute integrity ❌ (verification logic)
└─ Compare hashes ❌ (verification logic)

LocalChainResolver - Called verify_signature for verification
Handlers - Called verify_signature for verification
```

### After: Centralized Verification
```
MetadataManager - Format handling ONLY
├─ get_signature_hash() - Extract hash from signature
├─ get_signature_info() - Extract full signature metadata  
└─ sign_content_with_hash() - Add signature to content

IntegrityVerifier - ALL verification logic ✅
├─ verify_single_file() - Verify one file's integrity
│   ├─ Compute unified integrity
│   ├─ Compare with stored hash
│   └─ Cache results
└─ verify_chain() - Verify entire execution chain

LocalChainResolver - Hash extraction, NO verification
└─ Uses get_signature_hash() to build chain

Handlers - Use IntegrityVerifier for verification
├─ Run: verify_single_file() before execution
└─ Create/Update: compute_unified_integrity() + sign
```

## Benefits

1. **Single Source of Truth** - All verification logic in one place (`IntegrityVerifier`)
2. **Clear Separation of Concerns**
   - `MetadataManager`: Format/parse signatures
   - `IntegrityVerifier`: Verify content integrity
3. **Simpler Code** - No more split verification logic
4. **Better Caching** - Verification cache centralized in `IntegrityVerifier`
5. **Easier Testing** - Single verification interface to test

## Files Modified

### Core Verification
- `kiwi_mcp/utils/metadata_manager.py`
  - Removed: `verify_signature()` method
  - Added: `get_signature_hash()` method
  - Kept: `get_signature_info()`, `sign_content_with_hash()`

- `kiwi_mcp/primitives/integrity_verifier.py`
  - Added: `verify_single_file()` method for single-file verification
  - Kept: `verify_chain()` for chain verification

- `kiwi_mcp/primitives/local_chain_resolver.py`
  - Changed: Use `get_signature_hash()` instead of `verify_signature()`
  - Behavior: Extract hash, don't verify (verification happens later)

### Handlers (All Updated)
- `kiwi_mcp/handlers/tool/handler.py`
  - `_run_tool()`: Use `IntegrityVerifier.verify_single_file()`
  - `_publish_tool()`: Use `get_signature_hash()` + `IntegrityVerifier.verify_single_file()`
  - `_create_tool()`: Use `get_signature_info()` for response
  - `_update_tool()`: Use `get_signature_info()` for response

- `kiwi_mcp/handlers/directive/handler.py`
  - `_run_directive()`: Use `IntegrityVerifier.verify_single_file()`
  - `_publish_directive()`: Use `get_signature_hash()`
  - Load methods: Use `get_signature_info()` for warnings

- `kiwi_mcp/handlers/knowledge/handler.py`
  - `_run_knowledge()`: Use `IntegrityVerifier.verify_single_file()`
  - `_publish_knowledge()`: Use `get_signature_hash()`
  - Load methods: Use `get_signature_info()` for warnings

## API Changes

### Removed
```python
# OLD - REMOVED
MetadataManager.verify_signature(
    item_type, file_content, file_path=None, 
    project_path=None, item_id=None, version=None, metadata=None
) -> Optional[Dict]
```

### Added
```python
# NEW - Format handling only
MetadataManager.get_signature_hash(
    item_type, file_content, file_path=None, project_path=None
) -> Optional[str]

# NEW - Verification logic
IntegrityVerifier.verify_single_file(
    item_type, item_id, version, file_path, 
    stored_hash, project_path=None
) -> VerificationResult
```

## Migration Path

### For External Callers
If you were calling `MetadataManager.verify_signature()`:

```python
# OLD
signature_status = MetadataManager.verify_signature("tool", content, file_path=path)
if signature_status and signature_status["status"] == "valid":
    # use it

# NEW - For format checking only
stored_hash = MetadataManager.get_signature_hash("tool", content, file_path=path)
if stored_hash:
    # have a signature

# NEW - For content verification
verifier = IntegrityVerifier()
result = verifier.verify_single_file(
    item_type="tool",
    item_id=tool_id,
    version=version,
    file_path=path,
    stored_hash=stored_hash
)
if result.success:
    # verified
```

## Testing

Run `test_centralized_verification.py` to verify the architecture:

```bash
python test_centralized_verification.py
```

The test demonstrates:
1. ✅ MetadataManager extracts hashes (format handling)
2. ✅ IntegrityVerifier verifies content (verification logic)
3. ✅ LocalChainResolver builds chains (hash extraction)
4. ✅ Modification detection works (security)

## Status

- ✅ All verification centralized in `IntegrityVerifier`
- ✅ `MetadataManager` simplified to format-only
- ✅ All handlers updated
- ✅ `LocalChainResolver` updated
- ✅ No `verify_signature()` calls remain in codebase
- ⚠️  Tools need re-validation with new unified integrity system

## Next Steps

Tools signed with the old system need re-validation:

```python
execute(
    item_type='tool',
    action='update',
    item_id='tool_name',
    parameters={'location': 'project'},
    project_path='/path/to/project'
)
```

This will re-sign them with the new unified integrity hashing.
