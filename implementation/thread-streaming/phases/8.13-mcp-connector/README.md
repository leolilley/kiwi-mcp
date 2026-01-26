# Phase 8.13: MCP Connector Pattern

**Estimated Time:** 1-2 days  
**Dependencies:** Phases 8.4, 8.10  
**Status:** 📋 Planning

## Overview

Implement the MCP connector pattern that discovers external MCP tools and generates child tool schemas with proper capability requirements.

## What This Phase Accomplishes

- `mcp_connector` tool type
- Connector tool that runs `tools/list` and generates child tool schemas
- Generated tools include proper `requires` capabilities
- Auto-signing of generated tools
- Example connector for one MCP (e.g., Supabase)

## Files to Create

- `.ai/tools/mcp/supabase_connector.yaml` (new - example connector)
- `kiwi_mcp/primitives/mcp_connector.py` (new)
- `tests/primitives/test_mcp_connector.py` (new)

## Task Breakdown

1. Implement mcp_connector tool type
2. Create connector discovery logic
3. Implement tool schema generation
4. Add capability requirements to generated tools
5. Implement auto-signing
6. Create example Supabase connector
7. Write comprehensive tests

## Success Criteria

- [ ] Connector tool type works
- [ ] Tool discovery works (tools/list)
- [ ] Generated tools have correct structure
- [ ] Capability requirements are correct
- [ ] Tools are auto-signed
- [ ] Example connector works end-to-end
- [ ] Tests cover all scenarios

## Related Sections

- Doc lines 3964-3977: Phase 8.13 description
- Doc lines 5625-5773: Appendix A.6 (External MCP Integration & Tool Discovery)
