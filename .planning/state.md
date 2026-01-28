# Project State

**Project:** Kiwi MCP - Harness & Knowledge Implementation
**Updated:** 2026-01-28
**Current Phase:** 1 (Planning)

---

## Current Position

- [x] Created roadmap with 8 phases
- [ ] Phase 1: Knowledge System Foundation - **PENDING**
- [ ] Phase 2: Knowledge Parser Enhancement
- [ ] Phase 3: Harness Architecture Foundation
- [ ] Phase 4: Thread Management
- [ ] Phase 5: Hook System
- [ ] Phase 6: Recursive Enforcement
- [ ] Phase 7: GSD Directive Set
- [ ] Phase 8: Integration & Documentation

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Implementation order | Knowledge first, then Harness | Knowledge is simpler, lower risk, enables harness to use knowledge |
| ID naming | `id` universally | Consistent with `directive_name`, `tool_name` |
| Backlink syntax | `[[id]]` | Simple, wiki-standard |
| Attachment storage | Separate files + frontmatter refs | Keeps knowledge entries clean |
| Hook metadata | `<hooks>` element | Metadata-driven, not hardcoded |
| Harness placement | Outside kernel | Kernel stays dumb, harness is smart |

---

## Open Questions

1. **Hook recursion limits:** Max depth for hooks spawning hooks?
2. **Cost budgeting:** Shared vs separate budgets for parent/child threads?
3. **Model fallback:** Multiple fallback tiers or single fallback?

---

## Blockers

None currently.

---

## Next Actions

1. Run `gsd:discuss-phase 1` to confirm Phase 1 decisions
2. Begin Phase 1 execution after discussion
