# Task: Add Recursive Body Templating

## Context
Implement recursive body templating that walks dict/list/str structures to replace `{param_name}` placeholders with actual parameter values. This enables dynamic request body construction.

## Dependencies
- Must complete: `06-implement-sse-parsing.md`

## Files to Modify
- `kiwi_mcp/primitives/http_client.py`

## Implementation Steps

1. Create `_template_body` helper method
2. Handle three cases: dict (recursive), list (recursive), str (template)
3. Use `.format()` or f-string for string templating
4. Apply to both sync and stream modes
5. Handle missing parameters gracefully (raise clear error)

## Code Snippet

```python
def _template_body(self, body: Any, params: Dict[str, Any]) -> Any:
    """Recursively template body with parameters.
    
    Walks dict/list/str structures and replaces {param_name} with values.
    """
    if isinstance(body, dict):
        return {k: self._template_body(v, params) for k, v in body.items()}
    elif isinstance(body, list):
        return [self._template_body(item, params) for item in body]
    elif isinstance(body, str):
        # Replace {param} with values from params
        try:
            return body.format(**params)
        except KeyError as e:
            raise ValueError(f"Missing parameter for template: {e}")
    else:
        # Primitive types (int, bool, None) - return as-is
        return body
```

**Usage in execute methods:**

```python
# In _execute_sync and _execute_stream:
body_config = config.get("body", {})
body = self._template_body(body_config, params)
```

## Success Criteria
- [ ] `_template_body` handles dict, list, and str
- [ ] Recursive templating works for nested structures
- [ ] Missing parameters raise clear errors
- [ ] Primitive types (int, bool, None) pass through unchanged
- [ ] Works in both sync and stream modes
- [ ] Tests cover nested structures

## Verification Command
```bash
python -c "
from kiwi_mcp.primitives.http_client import HttpClient

client = HttpClient()
params = {'model': 'claude-3', 'max_tokens': 4096}

# Test dict
body = {'model': '{model}', 'max_tokens': '{max_tokens}'}
result = client._template_body(body, params)
assert result == {'model': 'claude-3', 'max_tokens': 4096}

# Test nested
body = {'messages': [{'role': 'user', 'content': '{message}'}]}
params = {'message': 'Hello'}
result = client._template_body(body, params)
assert result == {'messages': [{'role': 'user', 'content': 'Hello'}]}

print('Body templating test passed!')
"
```

## Notes
- This enables dynamic request construction from YAML configs
- Error messages should be clear about which parameter is missing
- Consider using `string.Template` for safer templating (prevents injection)
- Nested structures are common in LLM API requests
