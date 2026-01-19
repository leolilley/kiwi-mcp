# Model Metadata Enforcement

## Overview

Model metadata (using the `<model>` tag) is enforced consistently across all directive actions: `run`, `create`, and `update`. The legacy `<model_class>` tag is supported for backwards compatibility but will generate warnings.

## Implementation Details

### Validation Method

**Location:** `kiwi_mcp/handlers/directive/handler.py` (after _check_permissions method)

```python
def _check_model_class(self, model_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate directive model metadata (supports both 'model' and legacy 'model_class').
    Checks that model has required tier attribute with valid value.
    
    Returns:
        {"valid": bool, "issues": list[str], "warnings": list[str]}
    """
```

**Validation Rules:**

1. Model must NOT be None (required in metadata)
2. Must have `tier` attribute with a non-empty string value (any string allowed for flexibility)
3. If `fallback` provided, must be a non-empty string (any string allowed, including "none")
4. If `parallel` provided, must be: true|false
5. If `id` provided, must be a non-empty string (optional agent identifier)

**Note:** Tier and fallback values are intentionally flexible to support future fine-tuned or specialized models. Standard recommended tiers are: `fast`, `balanced`, `reasoning`, `expert`.

### Enforcement Points

#### 1. **run action** - `_run_directive()`

- **When:** Before returning directive for execution
- **Check:** Calls `_check_model_class()` after permissions check
- **Failure:** Returns error dict, does NOT load directive
- **Effect:** Agents cannot run directives with invalid model
- **Warning:** If legacy `<model_class>` tag is detected, a non-blocking warning is included in the response

#### 2. **create action** - `_create_directive()`

- **When:** After XML validation, before signing directive
- **Check:** Parses file and calls `_check_model_class()`
- **Failure:** Returns error dict, does NOT sign/save directive
- **Effect:** Invalid directives cannot be created
- **Warning:** If legacy `<model_class>` tag is detected, a non-blocking warning is included in the response

#### 3. **update action** - `_update_directive()`

- **When:** After XML validation, before signing updated content
- **Check:** Parses file and validates model
- **Failure:** Returns error dict, does NOT update directive
- **Effect:** Invalid directive updates are rejected
- **Warning:** If legacy `<model_class>` tag is detected, a non-blocking warning is included in the response

## Error Response Format

When model is not valid, all three actions return:

```json
{
    "error": "Directive model not valid",
    "details": [
        "Issue 1",
        "Issue 2"
    ],
    "path": "/path/to/directive.md",
    "model_provided": {
        "tier": "...",
        "fallback": "...",
        "parallel": "...",
        "id": "...",
        "reasoning": "..."
    }
}
```

## Warning Response Format

When legacy `<model_class>` tag is detected, a warning is included (non-blocking):

```json
{
    "status": "ready",
    "warning": {
        "message": "Directive uses legacy 'model_class' tag. Please update to 'model' tag.",
        "solution": "Run directive 'edit_directive' with directive_name='directive_name' to update"
    }
}
```

## Model Structure

Must be inside `<metadata>`:

```xml
<metadata>
  <description>...</description>
  <category>...</category>
  <author>...</author>
  <model tier="balanced" fallback="fast" parallel="true" id="optional-agent-id">
    Explanation of reasoning requirements
  </model>
  <permissions>...</permissions>
</metadata>
```

**Backwards Compatibility:** The legacy `<model_class>` tag is still supported but will generate warnings. Use `<model>` for new directives.

## Summary

| Action | Enforcement | Effect |
|--------|-------------|--------|
| `run` | ✅ Enforced | Cannot execute invalid directives |
| `create` | ✅ Enforced | Cannot create invalid directives |
| `update` | ✅ Enforced | Cannot update to invalid state |
| `publish` | Not enforced | Registry-side validation |
| `delete` | Not enforced | File deletion only |
