# Data-Driven Validation: Implementation Decision Analysis

**Date**: 2026-01-23  
**Status**: ✅ Implemented - Two-Layer Architecture  
**Context**: Implementation of `implement_data_driven_validation` directive  
**Superseded by**: `implement_two_layer_validation` directive

---

## Implementation Outcome (2026-01-23)

**Decision: Two-Layer Validation Architecture**

After analysis, we determined that the original data-driven approach conflated two
fundamentally different validation use cases. The correct architecture separates them:

### Layer 1: Definition-Time Validation (ToolValidator)
- **Purpose**: Validates tool manifest structure at create/update/load time
- **Location**: `kiwi_mcp/utils/validators.py` → `ToolValidator` class
- **Characteristics**:
  - Hardcoded rules: tool_id, tool_type, version, executor_id
  - No database calls, synchronous, fast
  - This is a stable engine contract, not data-driven
- **When**: Called by `ValidationManager.validate("tool", ...)`

### Layer 2: Runtime Parameter Validation (PrimitiveExecutor + SchemaValidator)
- **Purpose**: Validates execution parameters at runtime before running primitives
- **Location**: `kiwi_mcp/primitives/executor.py` → `PrimitiveExecutor._validate_runtime_params()`
- **Characteristics**:
  - Uses tool's own `config_schema` from manifest (data-driven)
  - THIS is where "everything else is data" applies
  - Each tool/primitive defines its own parameter schema
- **When**: Called during `PrimitiveExecutor.execute()` before routing to subprocess/http_client

### Why This Is Correct

The database `config_schema` fields describe **runtime execution parameters**:
- subprocess: command, args, env, cwd, timeout
- http_client: method, url, headers, body, retry

These are NOT for validating tool manifest structure. The original approach incorrectly
tried to use runtime schemas for definition validation, which was architecturally wrong.

### Files Changed

- `kiwi_mcp/utils/validators.py`: Added `ToolValidator` class, simplified `ValidationManager`
- `kiwi_mcp/primitives/executor.py`: Added `_validate_runtime_params()` method
- `kiwi_mcp/utils/data_driven_validator.py`: Removed (replaced by ToolValidator)

---

## Executive Summary

During implementation of the data-driven validation directive, we discovered that the proposed JSON Schema-based approach may be over-engineered for the current system needs. This document analyzes the trade-offs and proposes a simpler alternative.

## Background Context

### Original Problem Statement

The `implement_data_driven_validation` directive was created to address:

1. **Hardcoded validation rules** in the current system
2. **Tool Handler validation mismatch** (using "script" validation instead of "tool")
3. **Desire for database-driven schemas** to make validation more flexible

### Current Validation System

The existing system uses three hardcoded validators:

- `DirectiveValidator`: Complex XML and metadata validation
- `ScriptValidator`: Python script validation with version checks
- `KnowledgeValidator`: Markdown frontmatter validation

These validators are mature, well-tested, and handle complex validation scenarios effectively.

### Identified Issue

In `kiwi_mcp/handlers/tool/handler.py` (lines 411-413):

```python
validation_result = ValidationManager.validate(
    "script", file_path, script_meta
)  # Still using "script" type
```

The ToolHandler uses "script" validation instead of "tool" validation, which was the primary driver for this directive.

## Proposed Solution Analysis

### Option 1: Full JSON Schema Implementation (Current Direction)

**What was initially implemented (later removed):**

- `DataDrivenValidator` class with database schema loading (removed, replaced by ToolValidator)
- `SchemaValidator` with JSON Schema validation engine (still used in PrimitiveExecutor for runtime validation)
- Async registry integration for schema retrieval (removed)
- Complex caching system with TTL and performance metrics (removed)
- Comprehensive test suites (removed)

**Complexity Metrics:**

- **New files**: 4 major files (~1,200 lines of code)
- **Dependencies**: Added `jsonschema>=4.0.0`
- **Test files**: 3 comprehensive test suites (~800 lines)
- **Integration points**: ValidationManager, ToolHandler, ToolRegistry

**Benefits:**

- ✅ Fully data-driven validation
- ✅ Schemas stored in database
- ✅ Runtime schema updates without code changes
- ✅ Supports complex JSON Schema validation rules
- ✅ Performance optimizations with caching

**Drawbacks:**

- ❌ **High complexity**: 2,000+ lines of new code
- ❌ **New dependency**: jsonschema library
- ❌ **Async complexity**: Registry calls during validation
- ❌ **Over-engineering**: Solves problems we don't currently have
- ❌ **Database dependency**: Validation fails if database unavailable
- ❌ **Schema confusion**: Database schemas are for runtime config, not tool validation

### Option 2: Simple Tool Validator Extension (Alternative)

**Proposed implementation:**

```python
class ToolValidator(ScriptValidator):
    """Validator for unified tools - extends script validation."""

    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        # Call parent script validation
        result = super().validate_metadata(parsed_data)

        # Add tool-specific validation
        tool_type = parsed_data.get("tool_type")
        valid_types = {"primitive", "runtime", "mcp_server", "mcp_tool", "script", "api"}

        if tool_type and tool_type not in valid_types:
            result["issues"].append(
                f"Invalid tool_type '{tool_type}'. Valid types: {', '.join(valid_types)}"
            )

        # Validate executor_id for non-primitives
        if tool_type != "primitive" and not parsed_data.get("executor_id"):
            result["issues"].append(
                f"Tool type '{tool_type}' requires executor_id field"
            )

        return result

# Update ValidationManager
VALIDATORS = {
    "directive": DirectiveValidator(),
    "script": ScriptValidator(),
    "tool": ToolValidator(),  # New tool validator
    "knowledge": KnowledgeValidator(),
}
```

**Complexity Metrics:**

- **New code**: ~50 lines
- **Dependencies**: None
- **Test additions**: ~100 lines
- **Integration points**: ValidationManager only

**Benefits:**

- ✅ **Minimal complexity**: Extends existing proven patterns
- ✅ **No new dependencies**: Uses existing validation framework
- ✅ **Backward compatible**: Doesn't change existing validators
- ✅ **Addresses core issue**: Proper tool validation
- ✅ **Fast and reliable**: No database calls during validation
- ✅ **Easy to maintain**: Simple, understandable code

**Drawbacks:**

- ❌ **Not data-driven**: Still hardcoded validation rules
- ❌ **Less flexible**: Can't update validation without code changes

## Database Schema Analysis

### Current Database Schema Usage

The unified tools system stores `config_schema` in tool manifests:

```sql
-- From 001_unified_tools.sql
CREATE TABLE tool_versions (
    manifest JSONB NOT NULL,  -- Contains config_schema
    ...
);
```

**Example config_schema (subprocess primitive):**

```json
{
  "config_schema": {
    "type": "object",
    "properties": {
      "command": { "type": "string", "description": "Command to execute" },
      "args": { "type": "array", "items": { "type": "string" } },
      "timeout": { "type": "integer", "default": 300 }
    },
    "required": ["command"]
  }
}
```

### Schema Purpose Clarification

These schemas are designed for **runtime parameter validation** (validating inputs when executing tools), not **tool definition validation** (validating the tool manifest itself).

**Runtime validation example:**

```python
# Validating parameters passed to subprocess tool
params = {"command": "ls", "args": ["-la"], "timeout": 30}
# config_schema validates these parameters
```

**Tool definition validation example:**

```python
# Validating the tool manifest structure
manifest = {"tool_id": "my_script", "tool_type": "script", "version": "1.0.0"}
# This is what our validators should handle
```

## Decision Framework

### When to Choose JSON Schema Approach

- ✅ **Frequent schema changes**: Validation rules change often
- ✅ **Complex validation needs**: Need advanced JSON Schema features
- ✅ **Multiple stakeholders**: Non-developers need to modify validation
- ✅ **Runtime flexibility**: Validation rules must change without deployments
- ✅ **Standardization**: Need to align with external JSON Schema standards

### When to Choose Simple Extension

- ✅ **Stable validation rules**: Tool validation requirements are well-defined
- ✅ **Development team control**: Validation changes go through code review
- ✅ **Simplicity preference**: Favor maintainable over flexible
- ✅ **Performance critical**: Validation happens frequently
- ✅ **Reliability focus**: Avoid external dependencies for core functionality

## Current System Assessment

### Validation Change Frequency

- **Directives**: Stable schema, changes are rare and significant
- **Scripts**: Very stable, just name/version validation
- **Knowledge**: Stable frontmatter format
- **Tools**: New system, but likely to stabilize quickly

### Complexity vs. Value Analysis

```
JSON Schema Approach:
Complexity: ████████████ (12/10)
Value:      ████░░░░░░░░ (4/10)
Risk:       ████████░░░░ (8/10)

Simple Extension:
Complexity: ██░░░░░░░░░░ (2/10)
Value:      ████████░░░░ (8/10)
Risk:       ██░░░░░░░░░░ (2/10)
```

## Recommendations

### Primary Recommendation: Simple Tool Validator

**Implement Option 2** - Simple ToolValidator extension

**Rationale:**

1. **Addresses the core issue**: Fixes ToolHandler validation mismatch
2. **Proportional response**: Solution complexity matches problem complexity
3. **Low risk**: Minimal changes to proven system
4. **Fast implementation**: Can be completed in 1-2 hours vs. days
5. **Easy maintenance**: Simple code is easier to debug and extend

### Implementation Plan

1. **Create ToolValidator** extending ScriptValidator
2. **Update ValidationManager** to include "tool" validator
3. **Fix ToolHandler** to use "tool" validation
4. **Add basic tests** for tool-specific validation
5. **Update documentation** with new validation approach

### Future Considerations

If we later need true data-driven validation:

1. **Start with specific use case**: Identify concrete need for database-driven schemas
2. **Incremental approach**: Add JSON Schema support to specific validators as needed
3. **Hybrid model**: Keep simple validation for stable cases, add complexity only where needed

## Alternative: Hybrid Approach

If we want some data-driven capabilities without full complexity:

```python
class ToolValidator(ScriptValidator):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry

    def validate_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().validate_metadata(parsed_data)

        # Basic tool validation (always runs)
        self._validate_tool_basics(parsed_data, result)

        # Optional enhanced validation (if registry available)
        if self.registry:
            self._validate_with_registry(parsed_data, result)

        return result
```

This provides:

- **Fallback reliability**: Works without database
- **Optional enhancement**: Uses database when available
- **Gradual adoption**: Can add data-driven features incrementally

## Conclusion

The full JSON Schema implementation, while technically impressive, represents a solution in search of a problem. The current validation system works well, and the primary issue (ToolHandler validation type) can be solved with a simple 50-line extension.

**Recommended action**: Pivot to the Simple Tool Validator approach, completing the directive's core objective with minimal complexity and maximum reliability.

This decision can be revisited if we encounter concrete use cases that require the flexibility of database-driven validation schemas.

---

**Next Steps:**

1. Get stakeholder approval for the simplified approach
2. Implement ToolValidator extension
3. Update tests and documentation
4. Archive the JSON Schema implementation for potential future use

