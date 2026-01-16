# Model Class Metadata Enforcement

## Overview

Model class metadata is enforced consistently across all directive actions: `run`, `create`, and `update`.

## Implementation Details

### Validation Method

**Location:** `kiwi_mcp/handlers/directive/handler.py` (after _check_permissions method)

```python
def _check_model_class(self, model_class: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate directive model_class metadata.
    Checks that model_class has required tier attribute with valid value.
    
    Returns:
        {"valid": bool, "issues": list[str]}
    """
```

**Validation Rules:**

1. Model class must NOT be None (required in metadata)
2. Must have `tier` attribute with a non-empty string value (any string allowed for flexibility)
3. If `fallback` provided, must be a non-empty string (any string allowed, including "none")
4. If `parallel` provided, must be: true|false

**Note:** Tier and fallback values are intentionally flexible to support future fine-tuned or specialized models. Standard recommended tiers are: `fast`, `balanced`, `reasoning`, `expert`.

### Enforcement Points

#### 1. **run action** - `_run_directive()`

- **When:** Before returning directive for execution
- **Check:** Calls `_check_model_class()` after permissions check
- **Failure:** Returns error dict, does NOT load directive
- **Effect:** Agents cannot run directives with invalid model_class

#### 2. **create action** - `_create_directive()`

- **When:** After XML validation, before signing directive
- **Check:** Parses file and calls `_check_model_class()`
- **Failure:** Returns error dict, does NOT sign/save directive
- **Effect:** Invalid directives cannot be created

#### 3. **update action** - `_update_directive()`

- **When:** After XML validation, before signing updated content
- **Check:** Creates temp file to parse and validate model_class
- **Failure:** Returns error dict, does NOT update directive
- **Effect:** Invalid directive updates are rejected

## Error Response Format

When model_class is not valid, all three actions return:

```json
{
    "error": "Directive model_class not valid",
    "details": [
        "Issue 1",
        "Issue 2"
    ],
    "path": "/path/to/directive.md",
    "model_class_provided": {
        "tier": "...",
        "fallback": "...",
        "parallel": "...",
        "reasoning": "..."
    }
}
```

## Model Class Structure

Must be inside `<metadata>`:

```xml
<metadata>
  <description>...</description>
  <category>...</category>
  <author>...</author>
  <model_class tier="balanced" fallback="fast" parallel="true">
    Explanation of reasoning requirements
  </model_class>
  <permissions>...</permissions>
</metadata>
```

## Summary

| Action | Enforcement | Effect |
|--------|-------------|--------|
| `run` | ✅ Enforced | Cannot execute invalid directives |
| `create` | ✅ Enforced | Cannot create invalid directives |
| `update` | ✅ Enforced | Cannot update to invalid state |
| `publish` | Not enforced | Registry-side validation |
| `delete` | Not enforced | File deletion only |
