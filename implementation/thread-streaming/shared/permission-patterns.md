# Permission Patterns Reference

**Source:** `docs/THREAD_AND_STREAMING_ARCHITECTURE.md` Appendix A.2

## Capability Token Model

- Tokens are minted by harness from directive `<permissions>`
- Tokens are signed JWTs/PASETOs with caps, scopes, expiry
- All tool calls include token via `__auth` metadata
- Kernel forwards opaquely (does NOT validate)
- Tools validate token against their `requires:` declaration

## Token Structure

```python
{
    "caps": [
        {"cap": "fs.read", "scope": {"path": "src/**"}},
        {"cap": "fs.write", "scope": {"path": "dist/**"}},
    ],
    "aud": "kiwi-mcp",
    "exp": "2026-01-25T12:00:00Z",
    "directive_id": "deploy_staging",
    "thread_id": "deploy_staging_20260125_103045",
}
```

## Tool Validation Pattern

```python
async def tool_execute(params: dict, __auth: str) -> dict:
    token = verify_token(__auth)
    required_caps = tool_config["requires"]
    
    if not validate_token_has_caps(token, required_caps):
        return {"error": "Missing required capability"}
    
    # Proceed with execution
```

## Hierarchical Permissions

- Core system directives have broad permissions (registry.write, spawn.thread)
- User directives have limited, project-scoped permissions
- Child threads get intersection of parent caps and directive caps (attenuation)

See `docs/PERMISSION_MODEL.md` for complete details.
