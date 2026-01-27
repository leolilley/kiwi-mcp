# Phase 8.10: Capability Token System

**Estimated Time:** 1-2 days  
**Dependencies:** Phase 8.5  
**Status:** 📋 Planning

## Overview

Implement the capability token system for permission enforcement. Includes capability discovery, token minting, validation, and attenuation.

See [PERMISSION_MODEL.md](../../../docs/PERMISSION_MODEL.md) for complete design.

## What This Phase Accomplishes

- `.ai/tools/capabilities/` structure (fs.py, net.py, db.py, etc.)
- Capability discovery (same pattern as extractors)
- `CapabilityToken` dataclass with signing
- `requires` field in tool YAML schema
- Harness token minting from directive permissions
- Token attenuation on thread spawn (intersection)
- `<orchestration>` tag in permissions schema

## Core Concepts

### CapabilityToken Dataclass

```python
@dataclass
class CapabilityToken:
    caps: List[str]              # Granted capabilities (e.g., ["fs.read", "tool.bash"])
    aud: str                     # Audience (prevents cross-service replay)
    exp: datetime                # Expiry time
    parent_id: Optional[str]     # Parent token ID (for delegation chains)
    directive_id: str            # Which directive this was minted from
    thread_id: str               # Which thread this token belongs to
```

**Signing:** Use PASETO (JWT alternative) or Ed25519 signatures. Token must be signed and verifiable by tools.

### Capability Naming Convention

```
<resource>.<action>

Examples:
- fs.read        (filesystem read)
- fs.write       (filesystem write)
- net.call       (network calls)
- db.query       (database queries)
- git.push       (git operations)
- spawn.thread   (spawn threads)
- tool.bash      (use bash tool)
- tool.pytest    (use pytest tool)
- kiwi-mcp.execute  (call kiwi-mcp)
- registry.write (access thread registry)
```

### Tool YAML `requires` Field

```yaml
tool_id: write_file
executor_id: python

# Required capabilities to use this tool
requires:
  - fs.write

parameters:
  - name: path
    type: string
  - name: content
    type: string
```

### Directive Permissions → Capabilities

Conversion rules (in `permissions_to_caps()`):

| Permission XML | Capability |
|---|---|
| `<read resource="filesystem" path="**/*"/>` | `fs.read` |
| `<write resource="filesystem" path="**/*"/>` | `fs.write` |
| `<execute resource="tool" id="bash"/>` | `tool.bash` |
| `<execute resource="spawn" action="thread"/>` | `spawn.thread` |
| `<execute resource="registry" action="write"/>` | `registry.write` |
| `<execute resource="kiwi-mcp" action="execute"/>` | `kiwi-mcp.execute` |

### Token Attenuation (Thread Spawning)

When parent thread spawns child thread:

```python
parent_caps = ["fs.read", "fs.write", "spawn.thread"]
child_declared = ["fs.write", "tool.bash"]

# Intersection = what child actually gets
attenuated = set(parent_caps) & set(child_declared)
# Result: ["fs.write"]

# Child does NOT inherit fs.read or spawn.thread, even if it asks
```

**Key point:** Child can only use capabilities parent has AND child declares.

## Files to Create

- `.ai/tools/capabilities/` (new directory)
  - `__init__.py` - Capability discovery registry
  - `fs.py` - Filesystem capabilities (read, write)
  - `net.py` - Network capabilities (call, spawn)
  - `db.py` - Database capabilities
  - `git.py` - Git operations
  - `process.py` - Process/spawn capabilities
  - `mcp.py` - MCP framework capabilities
- `safety_harness/capabilities.py` (new)
  - `CapabilityToken` dataclass
  - `mint_token(caps, aud, exp, directive_id, thread_id)`
  - `verify_token(token_str)`
  - `permissions_to_caps(permissions)`
  - `attenuate_token(parent_token, child_permissions)`
- `kiwi_mcp/utils/parsers.py` (extend)
  - Add `<orchestration>` tag parsing for directive metadata
- `tests/harness/test_capability_tokens.py` (new)
  - Test token minting
  - Test token verification
  - Test permission→capability conversion
  - Test attenuation
  - Test discovery

## Task Breakdown

1. Create capability tool structure & discovery registry
2. Implement `CapabilityToken` dataclass with signing
3. Implement `mint_token()` and `verify_token()`
4. Implement `permissions_to_caps()` converter
5. Implement `attenuate_token()` for thread spawning
6. Add `requires` field to tool YAML schema validation
7. Add `<orchestration>` tag parsing to directive parser
8. Write comprehensive tests

## Success Criteria

- [ ] Capability tools exist and are discoverable via `CapabilityRegistry`
- [ ] Tokens are signed, serializable, and verifiable
- [ ] `permissions_to_caps()` correctly maps all permission types
- [ ] `attenuate_token()` implements intersection correctly
- [ ] Tool YAML `requires` field is validated
- [ ] Harness calls `mint_token()` when spawning threads
- [ ] `<orchestration>` tag is parsed from directives
- [ ] All components tested with >95% coverage

## Related Docs

- [PERMISSION_MODEL.md](../../../docs/PERMISSION_MODEL.md) - Complete design
- [THREAD_AND_STREAMING_ARCHITECTURE.md](../../../docs/THREAD_AND_STREAMING_ARCHITECTURE.md) - Integration points
- Phase 8.5 - Safety harness foundation
