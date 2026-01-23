# Tool Implementation Status & Completion Plan

**Date:** 2026-01-21  
**Status:** Phase 1-2 Partial Implementation  
**Related:** [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md)

---

## Executive Summary

The tool system migration from scripts to tools is **partially complete**. Phase 1 (Foundation) is ~90% done, Phase 2 (Bash & API Executors) is ~80% done. Core execution works, but CRUD operations (`create`, `update`, `delete`, `publish`) are not implemented.

**Critical Gap:** `_update_tool` needs rename detection (same as directive/knowledge/script handlers) to prevent incorrect rename flows.

---

## Current Implementation Status

### ✅ Phase 1: Tool Foundation (Weeks 1-2) - ~90% Complete

| Component | Status | Notes |
|-----------|--------|-------|
| **ToolManifest dataclass** | ✅ Complete | `kiwi_mcp/handlers/tool/manifest.py` - Full implementation with YAML loading and virtual manifest generation |
| **ToolHandler** | ✅ Complete | `kiwi_mcp/handlers/tool/handler.py` - Renamed from ScriptHandler, executor routing works |
| **PythonExecutor** | ✅ Complete | `kiwi_mcp/handlers/tool/executors/python.py` - Extracted from handler, venv logic, output management |
| **ExecutorRegistry** | ✅ Complete | `kiwi_mcp/handlers/tool/executors/__init__.py` - Registry pattern working |
| **Backward compatibility** | ✅ Complete | `TypeHandlerRegistry` maps both "tool" and "script" to `ToolHandler` |
| **Virtual manifest generation** | ✅ Complete | Legacy `.py` files get virtual manifests automatically |

**Missing:**
- ❌ `_create_tool` - Returns error "Tool creation not yet implemented"
- ❌ `_update_tool` - Returns error "Tool updates not yet implemented" (also needs rename detection)
- ❌ `_delete_tool` - Returns error "Tool deletion not yet implemented"
- ❌ `_publish_tool` - Returns error "Tool publishing not yet implemented"

### ✅ Phase 2: Bash & API Executors (Weeks 3-4) - ~80% Complete

| Component | Status | Notes |
|-----------|--------|-------|
| **BashExecutor** | ✅ Complete | `kiwi_mcp/handlers/tool/executors/bash.py` - Parameter injection, timeout, output capture |
| **APIExecutor** | ✅ Complete | `kiwi_mcp/handlers/tool/executors/api.py` - HTTP requests, auth handling |
| **Tool manifest examples** | ⚠️ Partial | Manifest structure exists, but no example tool.yaml files in repo |
| **Validation updates** | ❌ Missing | No BashValidator or APIValidator in `kiwi_mcp/utils/validators.py` |

**Missing:**
- ❌ BashValidator - Check shebang, syntax validation
- ❌ APIValidator - Check endpoint, auth config validation
- ❌ Example tool.yaml manifests in `.ai/scripts/` or docs

---

## Implementation Gaps

### 1. CRUD Operations (Critical)

All four CRUD operations return placeholder errors:

```python
# Current state in ToolHandler
async def _create_tool(...) -> Dict[str, Any]:
    return {"error": "Tool creation not yet implemented"}

async def _update_tool(...) -> Dict[str, Any]:
    return {"error": "Tool updates not yet implemented"}

async def _delete_tool(...) -> Dict[str, Any]:
    return {"error": "Tool deletion not yet implemented"}

async def _publish_tool(...) -> Dict[str, Any]:
    return {"error": "Tool publishing not yet implemented"}
```

**Required Implementation:**

#### `_create_tool`
- Similar to `ScriptHandler._create_script` but:
  - Support `tool.yaml` manifest creation
  - Validate tool_type matches executor availability
  - Generate virtual manifest if no tool.yaml provided
  - Use `ValidationManager.validate("script", ...)` (still using "script" type for now)
  - Sign content with `MetadataManager.sign_content("script", ...)`

#### `_update_tool` ⚠️ **NEEDS RENAME DETECTION**
- Similar to `ScriptHandler._update_script` but:
  - **CRITICAL:** Add rename detection (extract tool name from manifest/metadata before parsing)
  - Check if tool name matches filename
  - If mismatch, reject with guidance to use `create` + `delete` flow
  - Validate using `ValidationManager`
  - Re-sign content after validation
  - Follow same pattern as directive/knowledge/script handlers

#### `_delete_tool`
- Similar to `ScriptHandler._delete_script` but:
  - Delete tool.yaml manifest if exists
  - Delete script file
  - Support `source` parameter (local, registry, all)
  - Require `confirm=true` parameter

#### `_publish_tool`
- Similar to `ScriptHandler._publish_script` but:
  - Publish to `ScriptRegistry` (still using script registry for now)
  - Include tool_type in metadata
  - Include manifest data if available

### 2. Validation Extensions

**Missing Validators:**

```python
# kiwi_mcp/utils/validators.py

class BashValidator(BaseValidator):
    """Validator for bash tools."""
    
    def validate_filename_match(self, file_path, parsed_data):
        # Check .sh extension matches tool_id
        ...
    
    def validate_metadata(self, parsed_data):
        # Check shebang
        # Check syntax (basic shellcheck if available)
        ...

class APIValidator(BaseValidator):
    """Validator for API tools."""
    
    def validate_filename_match(self, file_path, parsed_data):
        # Check tool.yaml exists
        ...
    
    def validate_metadata(self, parsed_data):
        # Check executor_config has endpoint
        # Check auth config is valid
        # Check method is valid (GET, POST, etc.)
        ...
```

**Update ValidationManager:**
```python
VALIDATORS = {
    "directive": DirectiveValidator(),
    "script": ScriptValidator(),
    "knowledge": KnowledgeValidator(),
    "bash": BashValidator(),  # NEW
    "api": APIValidator(),     # NEW
}
```

### 3. Registry Integration

**Current State:**
- Still using `ScriptRegistry` and `ScriptResolver` (backward compatibility)
- Tool manifests not stored in registry yet

**Future Migration:**
- Phase 1 roadmap suggests adding `tool_type` column to existing `scripts` table
- No migration needed yet, but should be planned

---

## Completion Checklist

### Immediate (Required for Basic Functionality)

- [ ] Implement `_create_tool` with manifest support
- [ ] Implement `_update_tool` **with rename detection** (critical for consistency)
- [ ] Implement `_delete_tool` with source parameter
- [ ] Implement `_publish_tool` to registry
- [ ] Add BashValidator to ValidationManager
- [ ] Add APIValidator to ValidationManager
- [ ] Update ValidationManager to route by tool_type when validating tools

### Short-term (Phase 2 Completion)

- [ ] Create example tool.yaml manifests in docs or `.ai/scripts/`
- [ ] Add integration tests for bash executor
- [ ] Add integration tests for API executor
- [ ] Add unit tests for BashValidator
- [ ] Add unit tests for APIValidator
- [ ] Document tool.yaml schema in DIRECTIVE_AUTHORING.md or new TOOL_AUTHORING.md

### Medium-term (Phase 3+ Dependencies)

- [ ] Migrate from ScriptRegistry to ToolRegistry (or add tool_type column)
- [ ] Update resolver to support tool.yaml-based resolution
- [ ] Add tool manifest schema validation (JSON Schema)
- [ ] Support tool.yaml in `.ai/tools/` directory structure (future)

---

## Rename Detection Implementation

**Critical:** `_update_tool` must follow the same rename detection pattern as directive/knowledge/script handlers.

### Pattern to Follow

```python
async def _update_tool(self, tool_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update tool with rename detection."""
    # Find existing file
    file_path = self.resolver.resolve(tool_name)
    if not file_path:
        return {"error": f"Tool '{tool_name}' not found"}
    
    # Read content
    content = file_path.read_text()
    
    # Extract tool name from manifest/metadata BEFORE parsing
    # Check for tool.yaml manifest
    manifest_path = file_path.parent / "tool.yaml"
    if manifest_path.exists():
        manifest = ToolManifest.from_yaml(manifest_path)
        manifest_tool_id = manifest.tool_id
        
        # RENAME DETECTION: Check if manifest tool_id doesn't match requested name
        if manifest_tool_id != tool_name:
            return {
                "error": "Cannot update: rename detected",
                "problem": {
                    "message": "Update action cannot be used for renaming tools",
                    "filename": file_path.name,
                    "manifest_tool_id": manifest_tool_id,
                    "requested_name": tool_name,
                },
                "solution": {
                    "correct_flow": "To rename a tool, use create + delete actions",
                    "steps": [
                        f"1. Ensure file is renamed: {file_path.name} → {manifest_tool_id}.py",
                        f"2. Ensure manifest tool_id matches: tool_id: {manifest_tool_id}",
                        f"3. Run create action: execute(action='create', item_id='{manifest_tool_id}')",
                        f"4. Run delete action: execute(action='delete', item_id='{tool_name}', params={{'confirm': True}})",
                    ],
                }
            }
    
    # For legacy scripts without manifest, extract name from metadata
    # Parse metadata to get script name
    script_meta = parse_script_metadata(file_path)
    script_name = script_meta.get("name")
    
    if script_name and script_name != tool_name:
        # Rename detected - same error pattern
        ...
    
    # Continue with normal update flow
    # Validate, sign, update file
    ...
```

**Reference Implementation:**
- See `DirectiveHandler._update_directive` (after rename detection is added)
- See `KnowledgeHandler._update_knowledge` (lines 714-747)
- See `ScriptHandler._update_script` (needs rename detection added too)

---

## Testing Requirements

### Unit Tests

- [ ] `test_tool_handler_create` - Create tool with/without manifest
- [ ] `test_tool_handler_update` - Update tool, reject rename attempts
- [ ] `test_tool_handler_delete` - Delete tool with confirm
- [ ] `test_tool_handler_publish` - Publish to registry
- [ ] `test_bash_validator` - Validate bash tool manifests
- [ ] `test_api_validator` - Validate API tool manifests

### Integration Tests

- [ ] `test_bash_executor_with_manifest` - Run bash tool from tool.yaml
- [ ] `test_api_executor_with_manifest` - Run API tool from tool.yaml
- [ ] `test_tool_rename_flow` - Complete rename flow (create + delete)

---

## Migration Notes

### Backward Compatibility

✅ **Current State:** Fully backward compatible
- `item_type="script"` aliases to `ToolHandler`
- Legacy `.py` files work without manifests
- Virtual manifests generated automatically

### Future Migration Path

When ready to fully migrate:
1. Add `tool_type` column to `scripts` table (Phase 1 roadmap suggests this)
2. Update `ScriptRegistry` to handle tool_type
3. Optionally rename `ScriptRegistry` → `ToolRegistry` (or keep alias)
4. Update resolver to prefer `tool.yaml` over `.py` files
5. Support `.ai/tools/` directory structure (optional)

**No breaking changes required** - current approach allows gradual migration.

---

## Related Documents

- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Full roadmap (Phases 1-13)
- [TOOLS_EVOLUTION_PROPOSAL.md](./TOOLS_EVOLUTION_PROPOSAL.md) - Original design proposal
- [fix_directive_rename_validation_e311aab9.plan.md](../.cursor/plans/fix_directive_rename_validation_e311aab9.plan.md) - Rename detection plan (applies to tools too)

---

## Next Steps

1. **Immediate:** Implement `_update_tool` with rename detection (follow directive/knowledge pattern)
2. **Immediate:** Implement `_create_tool`, `_delete_tool`, `_publish_tool`
3. **Short-term:** Add BashValidator and APIValidator
4. **Short-term:** Create example tool.yaml manifests
5. **Documentation:** Document tool.yaml schema and usage

**Priority:** Rename detection in `_update_tool` is critical for consistency across all item types.
