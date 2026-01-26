# Phase 8.6: Help Tool Extensions

**Estimated Time:** 2 days  
**Dependencies:** Phase 8.5  
**Status:** 📋 Planning

## Overview

Extend the help tool with action parameter (guidance, stuck, escalate, checkpoint) and signal handlers for intervention.

## What This Phase Accomplishes

- Add `action` parameter to help tool
- Guidance topics (kiwi-overview, permissions, mcps, stuck)
- Signal handlers (route stuck/escalate to appropriate handlers)
- Integration with loop detector

## Files to Modify/Create

- `kiwi_mcp/tools/help.py` (extend)
- `kiwi_mcp/runtime/intervention.py` (new)
- `tests/tools/test_help_signals.py` (new)

## Task Breakdown

1. Extend help tool with action parameter
2. Implement guidance topics
3. Implement signal handlers
4. Integrate with loop detector
5. Write tests

## Success Criteria

- [ ] Help tool accepts action parameter
- [ ] All actions work (guidance, stuck, escalate, checkpoint)
- [ ] Signal handlers route correctly
- [ ] Loop detector integration works
- [ ] Tests cover all actions

## Related Sections

- Doc lines 3863-3875: Phase 8.6 description
- Doc lines 3610-3761: Layer 9 (Help Tool & Thread Intervention)
