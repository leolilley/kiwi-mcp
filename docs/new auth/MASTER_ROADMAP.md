# Kiwi MCP Kernel Implementation Roadmap

**Date:** 2026-01-27  
**Status:** Master Plan  
**Goal:** Complete kernel-level infrastructure before thread/streaming work

---

## Executive Summary

This roadmap consolidates all kernel-level work that must be completed before resuming the Thread & Streaming implementation (Phase 8.x). The kernel infrastructure provides the foundation for secure, data-driven, offline-capable tool execution.

**Total Estimated Time:** 3-4 weeks

---

## Work Streams Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KERNEL INFRASTRUCTURE                               │
│                         (Must complete first)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Stream A: EnvResolver          Stream B: AuthStore        Stream C: Lockfile│
│  (Environment Resolution)       (Token Management)         (Reproducibility) │
│                                                                             │
│  ┌─────────────────┐           ┌─────────────────┐        ┌──────────────┐ │
│  │ A1: EnvResolver │           │ B1: AuthStore   │        │ C1: Lockfile │ │
│  │     Service     │           │     Core        │        │    Store     │ │
│  └────────┬────────┘           └────────┬────────┘        └──────┬───────┘ │
│           │                             │                        │         │
│  ┌────────▼────────┐           ┌────────▼────────┐        ┌──────▼───────┐ │
│  │ A2: Runtime     │           │ B2: Executor    │        │ C2: Executor │ │
│  │     ENV_CONFIG  │           │     Integration │        │  Integration │ │
│  └────────┬────────┘           └────────┬────────┘        └──────┬───────┘ │
│           │                             │                        │         │
│  ┌────────▼────────┐           ┌────────▼────────┐        ┌──────▼───────┐ │
│  │ A3: Executor    │           │ B3: CLI Auth    │        │ C3: CLI      │ │
│  │     Integration │           │     Commands    │        │   Commands   │ │
│  └─────────────────┘           └─────────────────┘        └──────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE DECOUPLING                                 │
│                         (Depends on AuthStore)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ D1: Remove Supabase SDK from Core                                   │   │
│  └──────────────────────────────────┬──────────────────────────────────┘   │
│                                     │                                       │
│  ┌──────────────────────────────────▼──────────────────────────────────┐   │
│  │ D2: Implement Registry Tool (.ai/tools/core/registry.py)           │   │
│  └──────────────────────────────────┬──────────────────────────────────┘   │
│                                     │                                       │
│  ┌──────────────────────────────────▼──────────────────────────────────┐   │
│  │ D3: Integration Testing & Documentation                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THREAD & STREAMING                                  │
│                         (Resume existing Phase 8.x work)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  See: implementation/thread-streaming/README.md                             │
│  Phases: 8.1 → 8.2 → 8.3 → 8.4 → 8.5 → 8.7 → 8.8-8.13                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stream A: Environment Resolution

**Duration:** 4-5 days  
**Dependencies:** None (can start immediately)  
**Reference:** [ENVIROMENT_RESOLUTION_ARCHETECTURE.md](./ENVIROMENT_RESOLUTION_ARCHETECTURE.md)

### Phase A1: EnvResolver Kernel Service (2 days)

Create the kernel-level environment resolver with data-driven resolver types.

**Files to create:**

- `kiwi_mcp/runtime/env_resolver.py`

**Tasks:**

| ID   | Task                                              | Est. | Depends   |
| ---- | ------------------------------------------------- | ---- | --------- |
| A1.1 | Create `EnvResolver` class skeleton               | 1h   | -         |
| A1.2 | Implement `resolve()` main method                 | 2h   | A1.1      |
| A1.3 | Implement `venv_python` resolver type             | 2h   | A1.2      |
| A1.4 | Implement `node_modules` resolver type            | 1h   | A1.2      |
| A1.5 | Implement `system_binary` resolver type           | 1h   | A1.2      |
| A1.6 | Implement `version_manager` resolver type         | 2h   | A1.2      |
| A1.7 | Implement `_expand_value()` for `${VAR:-default}` | 1h   | A1.2      |
| A1.8 | Add OS portability (Windows/Linux/macOS)          | 1h   | A1.3-A1.6 |
| A1.9 | Write unit tests for all resolver types           | 3h   | A1.3-A1.7 |

**Verification:**

- [ ] All resolver types work in isolation
- [ ] No side effects (no venv creation)
- [ ] Works on Linux (primary), cross-platform design
- [ ] All unit tests pass

### Phase A2: Runtime ENV_CONFIG (1 day)

Add `ENV_CONFIG` declarations to runtimes and update extraction.

**Files to modify:**

- `.ai/tools/runtimes/python_runtime.py`
- `.ai/tools/runtimes/node_runtime.py`
- `.ai/tools/extractors/python_extractor.py`

**Tasks:**

| ID   | Task                                                  | Est. | Depends   |
| ---- | ----------------------------------------------------- | ---- | --------- |
| A2.1 | Add `env_config` to python_extractor EXTRACTION_RULES | 30m  | -         |
| A2.2 | Add `ENV_CONFIG` to `python_runtime.py`               | 1h   | A2.1      |
| A2.3 | Add `ENV_CONFIG` to `node_runtime.py`                 | 30m  | A2.1      |
| A2.4 | Update `CONFIG.command` to use `${KIWI_PYTHON}`       | 30m  | A2.2      |
| A2.5 | Update `CONFIG.command` to use `${KIWI_NODE}`         | 30m  | A2.3      |
| A2.6 | Test metadata extraction picks up ENV_CONFIG          | 1h   | A2.1-A2.3 |
| A2.7 | Bump runtime versions to 2.0.0                        | 30m  | A2.2-A2.5 |

**Verification:**

- [ ] Metadata extraction includes `env_config` field
- [ ] Both runtimes have valid `ENV_CONFIG`
- [ ] Runtimes still load and validate correctly

### Phase A3: Executor Integration (1-2 days)

Integrate EnvResolver into PrimitiveExecutor.

**Files to modify:**

- `kiwi_mcp/primitives/executor.py`

**Tasks:**

| ID   | Task                                                | Est. | Depends    |
| ---- | --------------------------------------------------- | ---- | ---------- |
| A3.1 | Add `EnvResolver` import and instantiation          | 30m  | A1.9       |
| A3.2 | Add `_get_env_config_from_chain()` method           | 1h   | A3.1       |
| A3.3 | Update `execute()` to call `env_resolver.resolve()` | 2h   | A3.1, A3.2 |
| A3.4 | Move templating to use resolved env                 | 1h   | A3.3       |
| A3.5 | Remove hardcoded `PROJECT_VENV_PYTHON` logic        | 30m  | A3.3       |
| A3.6 | Add backward compat alias in ENV_CONFIG             | 30m  | A3.5       |
| A3.7 | Write integration tests                             | 2h   | A3.1-A3.6  |
| A3.8 | Run full test suite, fix regressions                | 2h   | A3.7       |

**Verification:**

- [ ] Executor uses EnvResolver for all env resolution
- [ ] Python tools execute with correct interpreter
- [ ] Node tools execute with correct interpreter
- [ ] All existing tests pass
- [ ] No hardcoded runtime logic in executor

---

## Stream B: AuthStore

**Duration:** 4-5 days  
**Dependencies:** None (can run parallel to Stream A)  
**Reference:** [AUTH_STORE_IMPLEMENTATION.md](./AUTH_STORE_IMPLEMENTATION.md), [AGENT_CREDENTIAL_SECURITY.md](./AGENT_CREDENTIAL_SECURITY.md)

### Phase B1: Core AuthStore Class (1-2 days)

Create kernel-only token management with OS keychain.

**Files to create:**

- `kiwi_mcp/runtime/auth.py`

**Tasks:**

| ID    | Task                                             | Est. | Depends    |
| ----- | ------------------------------------------------ | ---- | ---------- |
| B1.1  | Add `keyring>=23.0.0` to pyproject.toml          | 15m  | -          |
| B1.2  | Create `AuthStore` class skeleton                | 30m  | B1.1       |
| B1.3  | Implement `set_token()` with keychain storage    | 1h   | B1.2       |
| B1.4  | Implement `get_token()` with cache check         | 2h   | B1.2       |
| B1.5  | Implement `clear_token()`                        | 30m  | B1.2       |
| B1.6  | Implement `is_authenticated()`                   | 30m  | B1.4       |
| B1.7  | Implement token expiry checking                  | 1h   | B1.4       |
| B1.8  | Add `AuthenticationRequired` exception           | 30m  | B1.2       |
| B1.9  | Add `RefreshError` exception                     | 15m  | B1.2       |
| B1.10 | Implement `_refresh_token()` stub (Supabase API) | 1h   | B1.4       |
| B1.11 | Add in-memory metadata caching                   | 1h   | B1.4       |
| B1.12 | Write unit tests                                 | 2h   | B1.3-B1.11 |
| B1.13 | Test on Linux (primary platform)                 | 1h   | B1.12      |

**Verification:**

- [ ] Tokens stored in OS keychain
- [ ] Token retrieval works
- [ ] Expiry checking works
- [ ] Cache behavior correct
- [ ] All unit tests pass

### Phase B2: Executor Integration (1-2 days)

Integrate AuthStore into PrimitiveExecutor for token injection.

**Files to modify:**

- `kiwi_mcp/primitives/executor.py`

**Tasks:**

| ID   | Task                                             | Est. | Depends    |
| ---- | ------------------------------------------------ | ---- | ---------- |
| B2.1 | Add `AuthStore` import and instantiation         | 30m  | B1.12      |
| B2.2 | Add `required_scope` extraction from tool config | 1h   | B2.1       |
| B2.3 | Implement token injection for HTTP requests      | 2h   | B2.1, B2.2 |
| B2.4 | Handle `AuthenticationRequired` gracefully       | 1h   | B2.3       |
| B2.5 | Add scope validation logic                       | 1h   | B2.2       |
| B2.6 | Write integration tests                          | 2h   | B2.1-B2.5  |

**Verification:**

- [ ] Authenticated tools get token injected
- [ ] Public tools work without auth
- [ ] Missing auth returns clear error message
- [ ] Integration tests pass

### Phase B3: CLI Auth Commands (1-2 days)

Implement user-facing authentication commands.

**Files to create:**

- `kiwi_mcp/cli/commands/auth.py`

**Tasks:**

| ID   | Task                             | Est. | Depends   |
| ---- | -------------------------------- | ---- | --------- |
| B3.1 | Create `kiwi auth` command group | 30m  | B2.6      |
| B3.2 | Implement `kiwi auth signin`     | 2h   | B3.1      |
| B3.3 | Implement `kiwi auth logout`     | 1h   | B3.1      |
| B3.4 | Implement `kiwi auth status`     | 1h   | B3.1      |
| B3.5 | Integrate with Supabase Auth API | 2h   | B3.2      |
| B3.6 | Handle token refresh lifecycle   | 1h   | B3.5      |
| B3.7 | Write E2E tests                  | 2h   | B3.2-B3.6 |
| B3.8 | User documentation               | 1h   | B3.7      |

**Verification:**

- [ ] `kiwi auth signin` works
- [ ] `kiwi auth logout` clears tokens
- [ ] `kiwi auth status` shows current state
- [ ] Token refresh works
- [ ] E2E tests pass

---

## Stream C: LockfileStore

**Duration:** 3-4 days  
**Dependencies:** None (can run parallel to A and B)  
**Reference:** [LOCKFILE_IMPLEMENTATION_PLAN.md](./LOCKFILE_IMPLEMENTATION_PLAN.md)

### Phase C1: Core LockfileStore (2 days)

Create kernel-level lockfile management.

**Files to create:**

- `kiwi_mcp/runtime/lockfile_store.py`

**Tasks:**

| ID    | Task                                                | Est. | Depends    |
| ----- | --------------------------------------------------- | ---- | ---------- |
| C1.1  | Create `LockfileStore` class skeleton               | 30m  | -          |
| C1.2  | Implement hierarchical storage structure            | 1h   | C1.1       |
| C1.3  | Implement `freeze()` method                         | 2h   | C1.1       |
| C1.4  | Implement `save()` method                           | 1h   | C1.3       |
| C1.5  | Implement `load()` with precedence (project > user) | 1h   | C1.1       |
| C1.6  | Implement `validate_chain()`                        | 2h   | C1.5       |
| C1.7  | Implement index management                          | 1h   | C1.4, C1.5 |
| C1.8  | Implement `list_lockfiles()`                        | 30m  | C1.7       |
| C1.9  | Implement `prune_stale()`                           | 1h   | C1.7       |
| C1.10 | Write unit tests                                    | 2h   | C1.1-C1.9  |

**Verification:**

- [ ] Lockfiles save/load correctly
- [ ] Hierarchical structure works
- [ ] Index updates correctly
- [ ] Validation logic works
- [ ] All unit tests pass

### Phase C2: Executor Integration (1 day)

Add lockfile validation to PrimitiveExecutor.

**Files to modify:**

- `kiwi_mcp/primitives/executor.py`

**Tasks:**

| ID   | Task                                         | Est. | Depends    |
| ---- | -------------------------------------------- | ---- | ---------- |
| C2.1 | Add `LockfileStore` import and instantiation | 30m  | C1.10      |
| C2.2 | Add `use_lockfile` parameter to `execute()`  | 30m  | C2.1       |
| C2.3 | Implement validation in execute flow         | 2h   | C2.1, C2.2 |
| C2.4 | Add warn-by-default mode                     | 1h   | C2.3       |
| C2.5 | Add strict mode (fail on mismatch)           | 30m  | C2.3       |
| C2.6 | Write integration tests                      | 1h   | C2.1-C2.5  |

**Verification:**

- [ ] Lockfile validation integrates cleanly
- [ ] Warn mode logs but doesn't fail
- [ ] Strict mode fails on mismatch
- [ ] Integration tests pass

### Phase C3: CLI Commands (1 day)

Implement lockfile management commands.

**Files to create:**

- `kiwi_mcp/cli/commands/lockfile.py`

**Tasks:**

| ID   | Task                                      | Est. | Depends   |
| ---- | ----------------------------------------- | ---- | --------- |
| C3.1 | Create `kiwi lockfile` command group      | 30m  | C2.6      |
| C3.2 | Implement `kiwi lockfile freeze <tool>`   | 1h   | C3.1      |
| C3.3 | Implement `kiwi lockfile validate <tool>` | 1h   | C3.1      |
| C3.4 | Implement `kiwi lockfile list`            | 30m  | C3.1      |
| C3.5 | Implement `kiwi lockfile prune`           | 30m  | C3.1      |
| C3.6 | Write CLI tests                           | 1h   | C3.2-C3.5 |
| C3.7 | User documentation                        | 1h   | C3.6      |

**Verification:**

- [ ] All CLI commands work
- [ ] Freeze creates valid lockfiles
- [ ] Validate reports differences
- [ ] List and prune work
- [ ] CLI tests pass

---

## Stream D: Supabase Decoupling

**Duration:** 4-5 days  
**Dependencies:** Stream B (AuthStore) must be complete  
**Reference:** [SUPABASE_DECOUPLING_PLAN.md](./SUPABASE_DECOUPLING_PLAN.md)

### Phase D1: Remove Supabase SDK (2 days)

Remove all Supabase Python SDK dependencies from core.

**Files to delete:**

- `kiwi_mcp/api/base.py`
- `kiwi_mcp/api/directive_registry.py`
- `kiwi_mcp/api/tool_registry.py`
- `kiwi_mcp/api/knowledge_registry.py`
- `kiwi_mcp/storage/vector/registry.py`

**Files to modify:**

- `kiwi_mcp/handlers/directive/handler.py`
- `kiwi_mcp/handlers/tool/handler.py`
- `kiwi_mcp/handlers/knowledge/handler.py`
- `kiwi_mcp/tools/search.py`
- `kiwi_mcp/tools/load.py`
- `kiwi_mcp/tools/execute.py`
- `kiwi_mcp/storage/vector/manager.py`
- `pyproject.toml`

**Tasks:**

| ID    | Task                                           | Est. | Depends   |
| ----- | ---------------------------------------------- | ---- | --------- |
| D1.1  | Delete registry API files (complete, no stubs) | 30m  | B2.6      |
| D1.2  | Remove `self.registry` from DirectiveHandler   | 1h   | D1.1      |
| D1.3  | Remove `self.registry` from ToolHandler        | 1h   | D1.1      |
| D1.4  | Remove `self.registry` from KnowledgeHandler   | 1h   | D1.1      |
| D1.5  | Delete publish/delete methods from handlers    | 1h   | D1.2-D1.4 |
| D1.6  | Update SearchTool (local-only)                 | 1h   | D1.1      |
| D1.7  | Update LoadTool (local-only)                   | 1h   | D1.1      |
| D1.8  | Update ExecuteTool (remove publish/delete)     | 1h   | D1.5      |
| D1.9  | Remove registry from vector manager            | 30m  | D1.1      |
| D1.10 | Remove `supabase>=2.0.0` from pyproject.toml   | 15m  | D1.1-D1.9 |
| D1.11 | Search codebase for remaining Supabase imports | 30m  | D1.10     |
| D1.12 | Run tests (core must work offline)             | 1h   | D1.11     |

**Cleanup Rules (per SUPABASE_DECOUPLING_PLAN.md):**

- ❌ No backwards compat code
- ❌ No deprecated warnings
- ❌ No stub methods
- ❌ No comments about removal
- ✅ Complete deletion only

**Verification:**

- [ ] No Supabase imports in core
- [ ] Core works completely offline
- [ ] All tests pass
- [ ] No publish/delete in execute tool

### Phase D2: Registry Tool Implementation (2 days)

Create HTTP-based registry tool.

**Files to create:**

- `.ai/tools/core/registry.py`

**Tasks:**

| ID    | Task                                            | Est. | Depends    |
| ----- | ----------------------------------------------- | ---- | ---------- |
| D2.1  | Create `.ai/tools/core/` directory if needed    | 15m  | D1.12      |
| D2.2  | Create `registry.py` with tool metadata         | 1h   | D2.1       |
| D2.3  | Define executor chain: `registry → http_client` | 30m  | D2.2       |
| D2.4  | Implement `search` action (public)              | 1h   | D2.2       |
| D2.5  | Implement `get` action (public)                 | 30m  | D2.2       |
| D2.6  | Implement `download` action (public)            | 1h   | D2.2       |
| D2.7  | Implement `upload` action (requires auth)       | 2h   | D2.2       |
| D2.8  | Implement `publish` action (requires auth)      | 1h   | D2.2       |
| D2.9  | Implement `private` action (requires auth)      | 30m  | D2.2       |
| D2.10 | Implement `unlist` action (requires auth)       | 30m  | D2.2       |
| D2.11 | Implement `delete` action (requires auth)       | 1h   | D2.2       |
| D2.12 | Implement `list`, `update`, `versions`, `stats` | 2h   | D2.2       |
| D2.13 | Add `required_scope` declarations               | 30m  | D2.7-D2.11 |
| D2.14 | Test tool discovery and loading                 | 1h   | D2.2-D2.13 |
| D2.15 | Test executor chain resolution                  | 1h   | D2.3       |

**Verification:**

- [ ] Tool discovered correctly
- [ ] Executor chain resolves: `registry → http_client`
- [ ] All 12 actions implemented
- [ ] Auth injection works for write operations
- [ ] Public operations work without auth

### Phase D3: Integration & Testing (1 day)

Complete integration testing and documentation.

**Tasks:**

| ID   | Task                               | Est. | Depends |
| ---- | ---------------------------------- | ---- | ------- |
| D3.1 | Write unit tests for registry tool | 2h   | D2.15   |
| D3.2 | Write integration tests with auth  | 2h   | D3.1    |
| D3.3 | Test E2E workflows                 | 1h   | D3.2    |
| D3.4 | Remove Supabase mocks from tests   | 1h   | D3.1    |
| D3.5 | Update user documentation          | 1h   | D3.3    |
| D3.6 | Create migration guide             | 1h   | D3.5    |

**Verification:**

- [ ] All tests pass
- [ ] Auth injection works E2E
- [ ] Documentation complete
- [ ] Migration guide available

---

## Stream E: Thread & Streaming (Resume)

**Duration:** 21-26 days (per existing plan)  
**Dependencies:** Streams A, B, C, D complete  
**Reference:** [implementation/thread-streaming/README.md](../../implementation/thread-streaming/README.md)

### Pre-Resume Checklist

Before resuming Phase 8.x work, verify:

- [ ] EnvResolver integrated and tested (Stream A)
- [ ] AuthStore integrated and tested (Stream B)
- [ ] LockfileStore integrated and tested (Stream C)
- [ ] Supabase decoupled, registry tool works (Stream D)
- [ ] All kernel services work together
- [ ] Full test suite passes

### Phase Summary (from existing plan)

| Phase | Focus                         | Days | Status     |
| ----- | ----------------------------- | ---- | ---------- |
| 8.1   | http_client streaming + sinks | 3-4  | 📋         |
| 8.2   | LLM endpoint tools            | 1-2  | 📋         |
| 8.3   | JSON-RPC protocol handling    | 2    | 📋         |
| 8.4   | MCP base tools (stdio + http) | 2    | 📋         |
| 8.5   | Thread registry (SQLite)      | 2-3  | ✅         |
| 8.6   | Help tool extensions          | 2    | ⏭️ Skipped |
| 8.7   | Thread intervention tools     | 3    | 📋         |
| 8.8   | Cleanup: remove kiwi_mcp/mcp/ | 1    | ✅         |
| 8.9   | Thread ID sanitization        | 0.5  | 📋         |
| 8.10  | Capability token system       | 1-2  | 📋         |
| 8.11  | Tool chain error handling     | 1    | 📋         |
| 8.12  | Cost tracking validation      | 1    | 📋         |
| 8.13  | MCP connector pattern         | 1-2  | 📋         |

---

## Execution Schedule

### Week 1: Kernel Services (Parallel)

| Day | Stream A (Env) | Stream B (Auth) | Stream C (Lock)      |
| --- | -------------- | --------------- | -------------------- |
| Mon | A1.1-A1.4      | B1.1-B1.4       | C1.1-C1.3            |
| Tue | A1.5-A1.9      | B1.5-B1.9       | C1.4-C1.7            |
| Wed | A2.1-A2.7      | B1.10-B1.13     | C1.8-C1.10           |
| Thu | A3.1-A3.4      | B2.1-B2.3       | C2.1-C2.4            |
| Fri | A3.5-A3.8      | B2.4-B2.6       | C2.5-C2.6, C3.1-C3.3 |

### Week 2: Auth CLI + Supabase Decoupling

| Day | Task                 |
| --- | -------------------- |
| Mon | B3.1-B3.4, C3.4-C3.7 |
| Tue | B3.5-B3.8            |
| Wed | D1.1-D1.6            |
| Thu | D1.7-D1.12           |
| Fri | D2.1-D2.8            |

### Week 3: Registry Tool + Integration

| Day | Task                                  |
| --- | ------------------------------------- |
| Mon | D2.9-D2.15                            |
| Tue | D3.1-D3.6                             |
| Wed | Integration testing, bug fixes        |
| Thu | Documentation, final verification     |
| Fri | Resume Thread & Streaming (Phase 8.1) |

### Week 4+: Thread & Streaming

Resume Phase 8.x per existing implementation plan.

---

## Risk Mitigation

### Risk: OS Keychain Differences

**Impact:** AuthStore may behave differently on macOS/Windows/Linux  
**Mitigation:** Test on Linux first (primary platform), document platform-specific notes

### Risk: Breaking Changes

**Impact:** Users with existing publish/delete workflows break  
**Mitigation:** Clear migration guide, no backwards compat in code (per design)

### Risk: Integration Complexity

**Impact:** Multiple kernel services may conflict  
**Mitigation:** Test each service independently first, then integration

### Risk: Thread Streaming Dependencies

**Impact:** Phase 8.x may need kernel features we haven't anticipated  
**Mitigation:** Review 8.1 requirements before Week 3 ends

---

## Success Criteria

### Kernel Infrastructure Complete

- [ ] EnvResolver: Data-driven, all resolver types work
- [ ] AuthStore: OS keychain, token injection, CLI commands
- [ ] LockfileStore: Freeze, validate, CLI commands
- [ ] All three services integrated into executor
- [ ] Full test suite passes

### Supabase Decoupling Complete

- [ ] No Supabase Python SDK in core
- [ ] Core works completely offline
- [ ] Registry tool has all 12 operations
- [ ] Auth injection works for authenticated operations
- [ ] Clean codebase (no legacy code)

### Ready for Thread & Streaming

- [ ] All kernel services stable
- [ ] No blockers for Phase 8.x
- [ ] Documentation up to date

---

## References

| Document                                                                                     | Purpose                       |
| -------------------------------------------------------------------------------------------- | ----------------------------- |
| [ENVIROMENT_RESOLUTION_ARCHETECTURE.md](./ENVIROMENT_RESOLUTION_ARCHETECTURE.md)             | Stream A design               |
| [AUTH_STORE_IMPLEMENTATION.md](./AUTH_STORE_IMPLEMENTATION.md)                               | Stream B implementation       |
| [AGENT_CREDENTIAL_SECURITY.md](./AGENT_CREDENTIAL_SECURITY.md)                               | Security architecture         |
| [LOCKFILE_IMPLEMENTATION_PLAN.md](./LOCKFILE_IMPLEMENTATION_PLAN.md)                         | Stream C design               |
| [SUPABASE_DECOUPLING_PLAN.md](./SUPABASE_DECOUPLING_PLAN.md)                                 | Stream D design               |
| [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)                                     | Previous roadmap (superseded) |
| [implementation/thread-streaming/README.md](../../implementation/thread-streaming/README.md) | Phase 8.x plan                |

---

_Generated: 2026-01-27_
