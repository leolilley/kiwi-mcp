# Kiwi MCP Implementation Roadmap

**Project:** Harness & Execution Model + Knowledge System Refactor
**Created:** 2026-01-28
**Status:** Planning

---

## Overview

This roadmap implements two complementary systems using GSD's spec-driven development workflow:

1. **Knowledge System Refactor** - Simpler, lower risk, enables better retrieval
2. **Harness & Execution Model** - Complex runtime architecture for directive execution

Each phase follows: `Discuss → Plan → Execute → Verify → Complete`

---

## Phase 1: Knowledge System Foundation

**Goal:** Rename `zettel_id` → `id`, verify parser, establish clean knowledge primitives

### 1.1 Discuss

- [ ] Confirm `id` as universal identifier (aligns with `directive_name`, `tool_name`)
- [ ] Confirm frontmatter schema changes
- [ ] Confirm backward compatibility strategy

### 1.2 Plan

**Tasks:**

| Task | File(s)                                  | Description                                                  |
| ---- | ---------------------------------------- | ------------------------------------------------------------ |
| 1.1  | `kiwi_mcp/primitives/integrity.py`       | Rename `zettel_id` → `id` in `compute_knowledge_integrity()` |
| 1.2  | `kiwi_mcp/handlers/knowledge/handler.py` | Rename all `zettel_id` references to `id`                    |
| 1.3  | `kiwi_mcp/utils/parsers.py`              | Update frontmatter parser, schema, error messages            |
| 1.4  | `.ai/directives/*_knowledge*.md`         | Update directive parameter names                             |
| 1.5  | `.ai/knowledge/*.md`                     | Migrate existing entries (zettel_id → id)                    |
| 1.6  | `tests/`                                 | Update tests for new naming                                  |

**Verification:**

- All knowledge entries parse correctly
- `make test` passes
- Search/load/run operations work

### 1.3 Execute

Parallel tasks: 1.1, 1.2, 1.3 (core refactor)
Sequential: 1.4, 1.5, 1.6 (depends on core)

### 1.4 Verify

- [ ] Run full test suite
- [ ] Test knowledge search, load, sign, run
- [ ] Verify existing knowledge entries work

### 1.5 Complete

- [ ] Atomic commit: "refactor(knowledge): rename zettel_id to id"
- [ ] Update CHANGELOG

---

## Phase 2: Knowledge Parser Enhancement

**Goal:** Robust frontmatter parsing, enhanced schema, attachment support

### 2.1 Discuss

- [ ] Confirm attachment storage strategy (separate files + frontmatter refs)
- [ ] Confirm backlink syntax (`[[id]]` vs `[[id|label]]`)
- [ ] Confirm additional frontmatter fields

### 2.2 Plan

**Tasks:**

| Task | File(s)                                  | Description                               |
| ---- | ---------------------------------------- | ----------------------------------------- |
| 2.1  | `kiwi_mcp/utils/parsers.py`              | Add `attachments` schema to frontmatter   |
| 2.2  | `kiwi_mcp/utils/parsers.py`              | Add `source_url`, `source_type` schema    |
| 2.3  | `kiwi_mcp/utils/parsers.py`              | Add `created_at`, `updated_at` support    |
| 2.4  | `kiwi_mcp/utils/parsers.py`              | Extract `[[id]]` backlinks during parsing |
| 2.5  | `kiwi_mcp/handlers/knowledge/handler.py` | Store backlinks in frontmatter on save    |
| 2.6  | `kiwi_mcp/handlers/knowledge/handler.py` | Add `get_backlinks()` query               |

**Verification:**

- Attachments parsed correctly
- Backlinks extracted and stored
- `get_backlinks()` returns correct results

### 2.3 Execute

Parallel: 2.1, 2.2, 2.3, 2.4 (parser enhancements)
Sequential: 2.5, 2.6 (depends on parser)

### 2.4 Verify

- [ ] Test complex frontmatter with attachments
- [ ] Test backlink extraction and resolution
- [ ] Test bidirectional linking

### 2.5 Complete

- [ ] Atomic commit: "feat(knowledge): enhanced frontmatter with attachments and backlinks"

---

## Phase 3: Harness Architecture Foundation

**Goal:** Establish kernel/harness separation, implement core harness primitives

### 3.1 Discuss

- [ ] Confirm "kernel is dumb" principle (JSON responses only)
- [ ] Confirm harness placement (outside kernel, wraps LLM calls)
- [ ] Confirm thread spawning strategy

### 3.2 Plan

**Tasks:**

| Task | File(s)                           | Description                                           |
| ---- | --------------------------------- | ----------------------------------------------------- |
| 3.1  | `kiwi_mcp/harness/__init__.py`    | Create harness module                                 |
| 3.2  | `kiwi_mcp/harness/base.py`        | Base `SafetyHarness` class with permission/cost hooks |
| 3.3  | `kiwi_mcp/harness/context.py`     | `ExecutionContext` for tracking state across threads  |
| 3.4  | `kiwi_mcp/harness/permissions.py` | Permission validation layer                           |
| 3.5  | `kiwi_mcp/harness/costs.py`       | Cost tracking and budget enforcement                  |
| 3.6  | `safety_harness/` (existing)      | Integrate or migrate existing safety harness code     |

**Verification:**

- Harness wraps MCP calls correctly
- Permissions checked before execution
- Costs tracked per-thread

### 3.3 Execute

Parallel: 3.1, 3.2, 3.3 (base structures)
Sequential: 3.4, 3.5, 3.6 (depends on base)

### 3.4 Verify

- [ ] Unit tests for harness components
- [ ] Integration test: harness wraps directive execution
- [ ] Permission denied scenarios work

### 3.5 Complete

- [ ] Atomic commit: "feat(harness): core safety harness architecture"

---

## Phase 4: Thread Management

**Goal:** Implement `spawn_thread` and `thread_directive` tools

### 4.1 Discuss

- [ ] Confirm thread isolation model
- [ ] Confirm context injection strategy
- [ ] Confirm model tier selection

### 4.2 Plan

**Tasks:**

| Task | File(s)                                  | Description                               |
| ---- | ---------------------------------------- | ----------------------------------------- |
| 4.1  | `kiwi_mcp/harness/threading.py`          | `spawn_thread()` raw primitive            |
| 4.2  | `kiwi_mcp/harness/threading.py`          | `thread_directive()` high-level tool      |
| 4.3  | `kiwi_mcp/harness/injection.py`          | Deterministic injection (call + response) |
| 4.4  | `kiwi_mcp/harness/models.py`             | Model tier registry and fallback logic    |
| 4.5  | `kiwi_mcp/handlers/directive/handler.py` | Wire threading to directive handler       |

**Verification:**

- Threads spawn with correct model/prompt
- Directive injection works deterministically
- Results returned to caller correctly

### 4.3 Execute

Sequential: 4.1 → 4.2 → 4.3 → 4.4 → 4.5

### 4.4 Verify

- [ ] Test thread spawning
- [ ] Test directive execution on spawned thread
- [ ] Test injection determinism

### 4.5 Complete

- [ ] Atomic commit: "feat(harness): thread spawning and directive execution"

---

## Phase 5: Hook System

**Goal:** Implement deterministic hooks triggered by conditions

### 5.1 Discuss

- [ ] Confirm hook metadata format (`<hooks>` element)
- [ ] Confirm condition evaluation strategy
- [ ] Confirm action types (retry, continue, skip, fail, abort)

### 5.2 Plan

**Tasks:**

| Task | File(s)                     | Description                                           |
| ---- | --------------------------- | ----------------------------------------------------- |
| 5.1  | `kiwi_mcp/utils/parsers.py` | Parse `<hooks>` element from directive metadata       |
| 5.2  | `kiwi_mcp/harness/hooks.py` | `Hook` dataclass and condition evaluation             |
| 5.3  | `kiwi_mcp/harness/hooks.py` | Template variable substitution (`${directive.name}`)  |
| 5.4  | `kiwi_mcp/harness/hooks.py` | Hook execution (spawn thread, inject, evaluate)       |
| 5.5  | `kiwi_mcp/harness/hooks.py` | Action execution (retry, continue, skip, fail, abort) |
| 5.6  | `kiwi_mcp/harness/base.py`  | Integrate hooks into harness flow                     |

**Standard Hooks to Implement:**

- `on_permission_denied` → Request elevated token, retry
- `on_cost_exceeded` → Simplify request, retry
- `on_model_unavailable` → Select fallback tier
- `on_execution_failure` → Log, attempt recovery

**Verification:**

- Hooks parsed from metadata correctly
- Conditions evaluate deterministically
- Actions execute correctly

### 5.3 Execute

Sequential: 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6

### 5.4 Verify

- [ ] Test permission denied hook
- [ ] Test cost exceeded hook
- [ ] Test model fallback
- [ ] Test hook chaining

### 5.5 Complete

- [ ] Atomic commit: "feat(harness): deterministic hook system"

---

## Phase 6: Recursive Enforcement

**Goal:** Safety harness attached to all threads throughout execution tree

### 6.1 Discuss

- [ ] Confirm harness attachment strategy
- [ ] Confirm cost budgeting across tree
- [ ] Confirm hook recursion limits

### 6.2 Plan

**Tasks:**

| Task | File(s)                         | Description                  |
| ---- | ------------------------------- | ---------------------------- |
| 6.1  | `kiwi_mcp/harness/threading.py` | Harness auto-attach on spawn |
| 6.2  | `kiwi_mcp/harness/costs.py`     | Hierarchical cost tracking   |
| 6.3  | `kiwi_mcp/harness/hooks.py`     | Hook recursion depth limits  |
| 6.4  | `kiwi_mcp/harness/base.py`      | Aggregate error propagation  |

**Verification:**

- Every spawned thread has harness
- Costs tracked at all levels
- No infinite hook loops

### 6.3 Execute

Parallel: 6.1, 6.2, 6.3, 6.4

### 6.4 Verify

- [ ] Test recursive thread spawning
- [ ] Test cost aggregation
- [ ] Test hook depth limits

### 6.5 Complete

- [ ] Atomic commit: "feat(harness): recursive enforcement throughout thread tree"

---

## Phase 7: GSD Directive Set

**Goal:** Implement GSD workflow as Kiwi directives

### 7.1 Discuss

- [ ] Confirm GSD command → directive mapping
- [ ] Confirm `.planning/` structure
- [ ] Confirm state tracking format

### 7.2 Plan

**Directives to Create:**

| Directive                | Purpose                                          |
| ------------------------ | ------------------------------------------------ |
| `gsd_new_project`        | Initialize project, questions, research, roadmap |
| `gsd_discuss_phase`      | Capture implementation decisions                 |
| `gsd_plan_phase`         | Research + plan generation + verification        |
| `gsd_execute_phase`      | Parallel task execution                          |
| `gsd_verify_work`        | User acceptance testing                          |
| `gsd_complete_milestone` | Release + archive                                |

**Tasks:**

| Task | File(s)                                        | Description                  |
| ---- | ---------------------------------------------- | ---------------------------- |
| 7.1  | `.ai/directives/gsd/gsd_new_project.md`        | Create new project directive |
| 7.2  | `.ai/directives/gsd/gsd_discuss_phase.md`      | Discuss phase directive      |
| 7.3  | `.ai/directives/gsd/gsd_plan_phase.md`         | Plan phase directive         |
| 7.4  | `.ai/directives/gsd/gsd_execute_phase.md`      | Execute phase directive      |
| 7.5  | `.ai/directives/gsd/gsd_verify_work.md`        | Verify work directive        |
| 7.6  | `.ai/directives/gsd/gsd_complete_milestone.md` | Complete milestone directive |

### 7.3 Execute

Parallel: All directives can be created in parallel

### 7.4 Verify

- [ ] Test full GSD workflow
- [ ] Test phase transitions
- [ ] Test state persistence

### 7.5 Complete

- [ ] Atomic commit: "feat(gsd): complete GSD directive set"

---

## Phase 8: Integration & Documentation

**Goal:** Wire everything together, document, test end-to-end

### 8.1 Plan

**Tasks:**

| Task | File(s)              | Description                   |
| ---- | -------------------- | ----------------------------- |
| 8.1  | `docs/harness.md`    | Document harness architecture |
| 8.2  | `docs/hooks.md`      | Document hook system          |
| 8.3  | `docs/knowledge.md`  | Document knowledge system     |
| 8.4  | `docs/gsd.md`        | Document GSD workflow         |
| 8.5  | `tests/integration/` | End-to-end integration tests  |
| 8.6  | `README.md`          | Update main documentation     |

### 8.2 Verify

- [ ] Full integration test passes
- [ ] Documentation complete
- [ ] Examples work

### 8.3 Complete

- [ ] Atomic commit: "docs: harness, hooks, knowledge, and GSD documentation"
- [ ] Tag release

---

## State Tracking

```
.planning/
├── config.json              (model profiles, settings)
├── state.md                 (current position, decisions, blockers)
├── ROADMAP.md               (this file)
├── research/
│   └── (generated by research phases)
├── phase-1-PLAN.md          (generated by plan-phase 1)
├── phase-1-SUMMARY.md       (generated after execute-phase 1)
└── ...
```

---

## Execution Order

```
Phase 1 (Knowledge Foundation)     ──┐
Phase 2 (Knowledge Enhancement)    ──┼── Can run in parallel
Phase 3 (Harness Foundation)       ──┘
                                     │
                                     ▼
Phase 4 (Thread Management)        ←─── Depends on Phase 3
                                     │
                                     ▼
Phase 5 (Hook System)              ←─── Depends on Phase 4
                                     │
                                     ▼
Phase 6 (Recursive Enforcement)    ←─── Depends on Phase 5
                                     │
                                     ▼
Phase 7 (GSD Directives)           ←─── Depends on Phases 1-6
                                     │
                                     ▼
Phase 8 (Integration & Docs)       ←─── Final phase
```

---

## Next Steps

1. **Run:** `gsd:discuss-phase 1` - Confirm Phase 1 decisions
2. **Run:** `gsd:plan-phase 1` - Generate detailed task breakdown
3. **Run:** `gsd:execute-phase 1` - Implement Phase 1 tasks
4. **Run:** `gsd:verify-work 1` - Verify Phase 1 complete
5. **Repeat** for each phase

---

## Success Criteria

- [ ] Knowledge system uses `id` universally
- [ ] Backlinks and attachments work
- [ ] Harness enforces permissions deterministically
- [ ] Threads spawn with safety harness attached
- [ ] Hooks trigger on conditions, execute actions
- [ ] GSD workflow runs end-to-end
- [ ] Full test coverage
- [ ] Documentation complete
