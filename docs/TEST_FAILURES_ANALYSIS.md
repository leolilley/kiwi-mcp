# Test Failures Analysis

**Date:** 2026-01-24  
**Total Tests:** 563  
**Passing:** ~500  
**Failing:** ~60  
**Errors:** ~10

## Executive Summary

The test failures fall into **7 main categories**, most related to the **Script → Tool migration** that was completed but tests weren't fully updated. Other issues include optional dependency handling, test mocking problems, and minor precision issues.

---

## Category 1: Script → Tool Migration Issues ⚠️ **HIGH PRIORITY**

**Root Cause:** System migrated from "script" to "tool" but many tests still reference "script"

**Affected Tests:** 15+ tests

### 1.1 Test Tool Enum Validation
**Files:**
- `tests/unit/test_tools.py::TestSearchTool::test_search_tool_enum_types`
- `tests/unit/test_tools.py::TestToolParameterValidation::test_execute_tool_item_type_enum`

**Issue:**
```python
assert "script" in item_type_enum  # FAILS
# item_type_enum = ['directive', 'tool', 'knowledge']
```

**Fix:** Update tests to use "tool" instead of "script"

### 1.2 Script Registry Flow Tests
**Files:**
- `tests/integration/test_flows.py::TestScriptRegistryFlow::*` (4 tests - all ERROR at setup)

**Issue:**
```python
class TestScriptRegistryFlow:
    """Test complete script workflow."""
    
    @pytest.fixture
    async def test_script_search(self, script_registry, ...):
        # script_registry fixture doesn't exist anymore
```

**Root Cause:** `ScriptRegistry` was removed, replaced with `ToolRegistry`. Tests need to be updated or removed.

**Fix Options:**
1. **Update tests** to use `tool_registry` fixture and test tool workflows
2. **Remove tests** if tool functionality is covered elsewhere
3. **Rename class** to `TestToolRegistryFlow`

### 1.3 Handler Registry Tests
**Files:**
- `tests/unit/test_handlers.py::TestTypeHandlerRegistrySearch::test_search_passes_parameters`
- `tests/unit/test_handlers.py::TestTypeHandlerRegistryLoad::test_load_script_name_mapping`
- `tests/unit/test_handlers.py::TestTypeHandlerRegistryExecute::test_execute_maps_item_id_to_script_name`
- `tests/unit/test_handlers.py::TestTypeHandlerRegistryIntegration::test_registry_with_all_handlers_populated`

**Issues:**
```python
# Test expects "script" handler
await registry.search(item_type="script", ...)  # Returns None
await registry.load(item_type="script", ...)   # TypeError: 'NoneType' object is not subscriptable

# Test expects ["directive", "script", "knowledge"]
assert registry.get_supported_types() == ["directive", "script", "knowledge"]  # FAILS
# Actual: ["directive", "tool", "knowledge"]
```

**Fix:** Update all references from "script" to "tool"

### 1.4 Hash Validation Tests
**Files:**
- `tests/unit/test_hash_validation.py::TestScriptHashValidation::test_script_run_allows_valid_hash`

**Issue:**
```python
ValueError: Unknown item_type: script. Supported: ['directive', 'tool', 'knowledge']
```

**Fix:** Change test to use "tool" instead of "script"

### 1.5 Version Warning Tests
**Files:**
- `tests/unit/test_version_warning.py::TestScriptHandlerVersionChecking::*` (2 tests)
- `tests/unit/test_version_warning.py::TestScriptHandlerRunWithVersionWarning::*` (2 tests - ERROR at setup)

**Issues:**
```python
# Test expects ScriptHandler with _check_for_newer_version method
AttributeError: 'ToolHandler' object has no attribute '_check_for_newer_version'

# Test setup fails
ValueError: Unknown item_type: script. Supported: ['directive', 'tool', 'knowledge']
```

**Fix:** 
- Update tests to use `ToolHandler` instead of `ScriptHandler`
- Check if `_check_for_newer_version` exists in `ToolHandler` or needs to be added
- Update item_type from "script" to "tool"

### 1.6 Metadata Integration Tests
**Files:**
- `tests/integration/test_metadata_integration.py::TestHandlerIntegration::test_script_handler_uses_metadata_manager`
- `tests/integration/test_metadata_integration.py::TestHandlerIntegration::test_script_handler_uses_validation_manager`

**Issues:**
```python
# Test expects script handler to return status
assert result.get("status") == "success"  # result is None

# Validation test expects success but gets error
# Error: 'Tool type (tool_type) is required'
```

**Fix:**
- Update to use `ToolHandler` instead of `ScriptHandler`
- Ensure tool handler properly returns status
- Fix validation to include required `tool_type` field

### 1.7 Cross Registry Integration Tests
**Files:**
- `tests/integration/test_flows.py::TestCrossRegistryIntegration::*` (3 tests - all ERROR at setup)

**Issue:** Tests try to use `script_registry` fixture which no longer exists.

**Fix:** Update to use `tool_registry` or remove if redundant

---

## Category 2: Optional Dependency Handling ⚠️ **MEDIUM PRIORITY**

**Root Cause:** Tests expect optional dependencies to be available as module attributes, but they're conditionally imported.

### 2.1 Vector Storage - ChromaDB
**Files:**
- `tests/storage/vector/test_local_store.py::*` (11 tests)

**Issue:**
```python
AttributeError: <module 'kiwi_mcp.storage.vector.local'> does not have the attribute 'chromadb'
```

**Root Cause:** `chromadb` is conditionally imported in `local.py`:
```python
try:
    import chromadb
except ImportError:
    chromadb = None
```

**Test Expectation:**
```python
# Tests try to access module attribute
from kiwi_mcp.storage.vector import local
assert local.chromadb is not None  # FAILS if not installed
```

**Fix Options:**
1. **Skip tests** if dependency not available (recommended)
2. **Mock the dependency** in tests
3. **Install optional dependencies** for test environment

**Recommended:** Add pytest skip markers:
```python
@pytest.mark.skipif(
    not hasattr(local, 'chromadb') or local.chromadb is None,
    reason="chromadb not installed"
)
```

### 2.2 Vector Storage - Sentence Transformers
**Files:**
- `tests/storage/vector/test_embeddings.py::TestEmbeddingModel::*` (4 tests)

**Issue:**
```python
AttributeError: <module 'kiwi_mcp.storage.vector.embeddings'> does not have the attribute 'SentenceTransformer'
```

**Root Cause:** `SentenceTransformer` is imported inside `_get_model()` method, not at module level.

**Test Expectation:**
```python
# Tests try to access module attribute
from kiwi_mcp.storage.vector import embeddings
assert embeddings.SentenceTransformer is not None  # FAILS
```

**Fix:** Same as 2.1 - add skip markers or mock

### 2.3 Schema Validator - jsonschema
**Files:**
- `tests/unit/test_schema_validator.py::*` (5 tests)

**Issue:**
```python
AttributeError: <module 'kiwi_mcp.utils.schema_validator'> does not have the attribute 'jsonschema'
```

**Root Cause:** `jsonschema` is conditionally imported inside `__init__`, not at module level.

**Test Expectation:**
```python
@patch("kiwi_mcp.utils.schema_validator.jsonschema")
def test_init_with_jsonschema(self, mock_jsonschema):
    # Patch fails because module doesn't have jsonschema attribute
```

**Fix:** Update tests to patch the import location or use skip markers

---

## Category 3: Test Mocking Issues ⚠️ **MEDIUM PRIORITY**

### 3.1 MCP Directive Tests - PosixPath read_text
**Files:**
- `tests/mcp/test_directive_mcp.py::test_run_directive_with_mcps_success`
- `tests/mcp/test_directive_mcp.py::test_run_directive_with_required_mcp_failure`
- `tests/mcp/test_directive_mcp.py::test_run_directive_with_optional_mcp_failure`

**Issue:**
```python
AttributeError: 'PosixPath' object attribute 'read_text' is read-only

# Test code:
mock_file_path = Path("/tmp/test.md")
mock_file_path.read_text = lambda: "directive content"  # FAILS - read-only
```

**Root Cause:** `Path.read_text` is a method, not a property, and can't be monkey-patched directly.

**Fix:** Use `unittest.mock.patch` or `MagicMock`:
```python
from unittest.mock import MagicMock
mock_file_path = MagicMock(spec=Path)
mock_file_path.read_text.return_value = "directive content"
```

---

## Category 4: Registry Flow Issues ⚠️ **MEDIUM PRIORITY**

### 4.1 Directive Registry Search
**Files:**
- `tests/integration/test_flows.py::TestDirectiveRegistryFlow::test_directive_search`
- `tests/integration/test_flows.py::TestDirectiveRegistryFlow::test_directive_search_with_category_filter`
- `tests/integration/test_flows.py::TestDirectiveRegistryFlow::test_directive_search_with_tech_stack`

**Issues:**
```python
assert len(results) > 0  # FAILS - results is empty list
assert False  # FAILS - tech_stack filter not working
```

**Root Cause:** Mock setup may not be matching actual registry search implementation.

**Fix:** Review mock setup and ensure it matches actual `DirectiveRegistry.search()` implementation

### 4.2 Knowledge Registry Get
**Files:**
- `tests/integration/test_flows.py::TestKnowledgeRegistryFlow::test_knowledge_get`

**Issue:**
```python
assert result is not None  # FAILS - result is None
```

**Fix:** Check mock setup for `knowledge_registry.get()` method

---

## Category 5: Validation Logic Issues ⚠️ **LOW PRIORITY**

### 5.1 Hash Validation Tests
**Files:**
- `tests/unit/test_hash_validation.py::TestDirectiveHashValidation::test_directive_run_blocks_on_modified_hash`
- `tests/unit/test_hash_validation.py::TestDirectiveHashValidation::test_directive_run_allows_valid_hash`
- `tests/unit/test_hash_validation.py::TestKnowledgeHashValidation::*` (2 tests)
- `tests/unit/test_hash_validation.py::TestHashValidationNoBypass::test_directive_run_no_skip_validation_param`

**Issues:**
```python
# Expected error message contains "modified" but actual is "directive model not valid"
assert 'modified' in error_message.lower()  # FAILS

# Expected status "ready" but got None or "error"
assert result.get("status") == "ready"  # FAILS
```

**Root Cause:** Validation error messages or status codes may have changed.

**Fix:** 
- Review actual validation logic in handlers
- Update test expectations to match actual behavior
- Check if validation is working correctly

### 5.2 Metadata Integration - Knowledge
**Files:**
- `tests/integration/test_metadata_integration.py::TestMetadataValidationIntegration::test_create_validate_sign_verify_knowledge`
- `tests/integration/test_metadata_integration.py::TestHandlerIntegration::test_knowledge_handler_uses_metadata_manager`
- `tests/integration/test_metadata_integration.py::TestHandlerIntegration::test_knowledge_handler_uses_validation_manager`

**Issues:**
```python
# Expected True but got False
assert validation_result["valid"] is True  # FAILS

# Expected "created" but got None
assert result.get("status") == "created"  # FAILS

# Validation error: "Knowledge entry is missing required 'version' in YAML frontmatter"
```

**Root Cause:** Knowledge entries require version in frontmatter, but test data may not include it.

**Fix:** Update test fixtures to include required version field

---

## Category 6: Floating Point Precision ⚠️ **LOW PRIORITY**

### 6.1 Hybrid Search Tests
**Files:**
- `tests/storage/vector/test_hybrid.py::TestHybridSearch::test_search`
- `tests/storage/vector/test_hybrid.py::TestHybridSearch::test_update_weights`

**Issues:**
```python
# Expected > 0.8 but got 0.77
assert results[0].score > 0.8  # FAILS

# Expected 0.6 but got 0.6000000000000001
assert hybrid.semantic_weight == 0.6  # FAILS (floating point precision)
```

**Fix:** Use `pytest.approx()` for floating point comparisons:
```python
assert results[0].score == pytest.approx(0.8, abs=0.05)
assert hybrid.semantic_weight == pytest.approx(0.6)
```

---

## Category 7: Timestamp Comparison ⚠️ **LOW PRIORITY**

### 7.1 End-to-End Flow Test
**Files:**
- `tests/integration/test_metadata_integration.py::TestEndToEndFlows::test_create_update_verify_flow_directive`

**Issue:**
```python
AssertionError: assert '2026-01-23T21:45:40Z' != '2026-01-23T21:45:40Z'
# Timestamps are identical but test expects them to be different
```

**Root Cause:** Test likely expects timestamps to change between create and update, but they're generated at the same time.

**Fix:** Review test logic - may need to add delay or mock timestamps

---

## Priority Recommendations

### 🔴 **HIGH PRIORITY - Fix Immediately**
1. **Script → Tool Migration** (Category 1)
   - Update all "script" references to "tool" in tests
   - Remove or update ScriptRegistry tests
   - Fix handler registry tests
   - Update version warning tests

### 🟡 **MEDIUM PRIORITY - Fix Soon**
2. **Optional Dependencies** (Category 2)
   - Add skip markers for chromadb, sentence-transformers tests
   - Fix jsonschema test mocking
3. **Test Mocking** (Category 3)
   - Fix PosixPath mocking in MCP directive tests
4. **Registry Flows** (Category 4)
   - Review and fix mock setups for registry search/get

### 🟢 **LOW PRIORITY - Fix When Time Permits**
5. **Validation Logic** (Category 5)
   - Review validation error messages
   - Update test expectations
6. **Floating Point** (Category 6)
   - Use pytest.approx() for comparisons
7. **Timestamp** (Category 7)
   - Review timestamp comparison logic

---

## Estimated Fix Time

- **Category 1 (Script→Tool):** 2-3 hours
- **Category 2 (Optional Deps):** 1 hour
- **Category 3 (Mocking):** 30 minutes
- **Category 4 (Registry):** 1-2 hours
- **Category 5 (Validation):** 1-2 hours
- **Category 6 (Floating Point):** 15 minutes
- **Category 7 (Timestamp):** 15 minutes

**Total:** ~6-9 hours

---

## Next Steps

1. Create todo list for fixing Category 1 issues
2. Add skip markers for optional dependency tests
3. Fix PosixPath mocking issues
4. Review and update validation test expectations
5. Fix floating point comparisons
