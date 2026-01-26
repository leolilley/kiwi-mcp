# Phase 8.10: Capability Token System

**Estimated Time:** 1-2 days  
**Dependencies:** Phase 8.5  
**Status:** 📋 Planning

## Overview

Implement the capability token system for permission enforcement. Includes capability discovery, token minting, validation, and attenuation.

## What This Phase Accomplishes

- `.ai/tools/capabilities/` structure (fs.py, net.py, db.py, etc.)
- Capability discovery (same pattern as extractors)
- `CapabilityToken` dataclass with signing
- `requires` field in tool YAML schema
- Harness token minting from directive permissions
- Token attenuation on thread spawn (intersection)
- `<orchestration>` tag in permissions schema

## Files to Create

- `.ai/tools/capabilities/*.py` (new - fs, net, db, git, process, mcp)
- `safety_harness/capabilities.py` (new)
- `kiwi_mcp/utils/parsers.py` (extend for orchestration tag)
- `tests/harness/test_capability_tokens.py` (new)

## Task Breakdown

1. Create capability tool structure
2. Implement capability discovery
3. Implement token minting
4. Implement token validation
5. Add requires field to tool schema
6. Implement token attenuation
7. Add orchestration tag parsing
8. Write comprehensive tests

## Success Criteria

- [ ] Capability tools exist and are discoverable
- [ ] Tokens are minted correctly from permissions
- [ ] Token validation works
- [ ] Tool requires field is validated
- [ ] Token attenuation works on spawn
- [ ] Orchestration tag is parsed
- [ ] Tests cover all scenarios

## Related Sections

- Doc lines 3921-3937: Phase 8.10 description
- Doc lines 4491-5122: Appendix A.2 (Permission Enforcement Architecture)
