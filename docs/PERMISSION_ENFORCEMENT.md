# Directive Permission Enforcement

## Overview

Directive permissions are now enforced consistently across all directive actions: `run`, `create`, and `update`.

## Implementation Details

### Permission Validation Method

**Location:** `kiwi_mcp/handlers/directive/handler.py:333-367`

```python
def _check_permissions(self, permissions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate directive permissions.
    Checks that required permissions are satisfied.
    Current implementation validates permission structure.

    Returns:
        {"valid": bool, "issues": list[str]}
    """
```

**Validation Rules:**

1. Permissions list must NOT be empty
2. Each permission must be a dict with:
   - `tag` field (required)
   - `attrs` field with at least one attribute (required)

### Enforcement Points

#### 1. **run action** - `_run_directive()`

**File:** `kiwi_mcp/handlers/directive/handler.py:272-331`

- **When:** Before returning directive for execution to agent
- **Check:** Calls `_check_permissions()` immediately after parsing
- **Failure:** Returns error dict, does NOT load directive
- **Effect:** Agents cannot run directives with invalid permissions

```python
# Check permissions - run action requires valid permissions
permission_check = self._check_permissions(directive_data.get("permissions", []))
if not permission_check["valid"]:
    return {
        "error": "Directive permissions not satisfied",
        "details": permission_check["issues"],
        "path": str(file_path),
        "permissions_required": directive_data.get("permissions", [])
    }
```

#### 2. **create action** - `_create_directive()`

**File:** `kiwi_mcp/handlers/directive/handler.py:484-607`

- **When:** After XML validation, before signing directive
- **Check:** Parses file and calls `_check_permissions()`
- **Failure:** Returns error dict, does NOT sign/save directive
- **Effect:** Invalid directives cannot be created/validated

```python
# Parse and check permissions
try:
    directive_data = parse_directive_file(file_path)
    permission_check = self._check_permissions(directive_data.get("permissions", []))
    if not permission_check["valid"]:
        return {
            "error": "Directive permissions not satisfied",
            "details": permission_check["issues"],
            "path": str(file_path),
            "permissions_required": directive_data.get("permissions", [])
        }
except Exception as e:
    return {
        "error": "Failed to validate directive permissions",
        "details": str(e),
        "file": str(file_path)
    }
```

#### 3. **update action** - `_update_directive()`

**File:** `kiwi_mcp/handlers/directive/handler.py:610-686`

- **When:** After XML validation, before signing updated content
- **Check:** Creates temp file to parse and validate permissions
- **Failure:** Returns error dict, does NOT update directive
- **Effect:** Invalid directive updates are rejected

```python
# Validate permissions on updated content
try:
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    tmp_file = Path(tmp_path)
    directive_data = parse_directive_file(tmp_file)
    permission_check = self._check_permissions(directive_data.get("permissions", []))
    tmp_file.unlink()  # Clean up temp file

    if not permission_check["valid"]:
        return {
            "error": "Directive permissions not satisfied",
            "details": permission_check["issues"],
            "path": str(file_path),
            "permissions_required": directive_data.get("permissions", [])
        }
```

## Error Response Format

When permissions are not satisfied, all three actions return consistent error responses:

```json
{
    "error": "Directive permissions not satisfied",
    "details": [
        "Issue 1",
        "Issue 2"
    ],
    "path": "/path/to/directive.md",
    "permissions_required": [
        {"tag": "permission_type", "attrs": {...}}
    ]
}
```

## Permission Structure in Directives

Directives must include a `<permissions>` section **inside `<metadata>`**:

```xml
<directive name="example" version="1.0.0">
  <metadata>
    <description>Example directive</description>
    <category>core</category>
    <permissions>
      <read resource="files" path="src/**/*.ts" />
      <write resource="api" endpoint="POST /users" />
    </permissions>
  </metadata>

  <process>
    <!-- Process steps -->
  </process>
</directive>
```

## Testing

Permission enforcement is tested in:

- `tests/unit/test_handlers.py` - Handler routing tests
- Permission validation can be tested via:

```python
from kiwi_mcp.handlers.directive.handler import DirectiveHandler

handler = DirectiveHandler()

# Valid permissions
valid = [{"tag": "read", "attrs": {"resource": "files"}}]
result = handler._check_permissions(valid)
# Returns: {"valid": True, "issues": []}

# Invalid permissions (empty)
result = handler._check_permissions([])
# Returns: {"valid": False, "issues": ["No permissions defined in directive"]}

# Invalid permissions (missing attrs)
invalid = [{"tag": "read"}]
result = handler._check_permissions(invalid)
# Returns: {"valid": False, "issues": ["Permission 'read' missing attributes"]}
```

## Summary

| Action    | Enforcement                  | Since   |
| --------- | ---------------------------- | ------- |
| `run`     | ✅ Enforced                  | Current |
| `create`  | ✅ Enforced                  | Current |
| `update`  | ✅ Enforced                  | Current |
| `publish` | Not enforced (registry-side) | -       |
| `delete`  | Not enforced (file deletion) | -       |
| `link`    | Not enforced (metadata only) | -       |

Permission enforcement ensures directives have properly declared permissions before being used, created, or updated.
