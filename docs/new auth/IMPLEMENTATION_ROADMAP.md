# Implementation Roadmap

**Date:** 2026-01-26  
**Status:** Planning  
**Goal:** Secure auth + Supabase decoupling + registry tool

---

## Overview

Three coordinated implementation tracks:

1. **Auth Store** - Kernel-only token management (OS keychain)
2. **Supabase Removal** - Decouple core SDK dependency
3. **Registry Tool** - HTTP-based registry via primitives

**Timeline:** ~2-3 weeks total

---

## Architecture Decision

### Token Security Model

```
Agent (UNTRUSTED) → PrimitiveExecutor (TRUSTED) → AuthStore (KERNEL ONLY) → OS Keychain
                                          ↓
                                    Http Client (injects token)
                                          ↓
                                    Supabase REST API
```

**Key Principle:** Tokens in kernel-only auth store, never visible to agents.

---

## Track 1: Auth Store Implementation

**Duration:** 3-4 days  
**Dependencies:** None  
**Deliverable:** Secure token management

### Phase 1: Core AuthStore Class (1 day)
- File: `kiwi_mcp/runtime/auth.py`
- Features:
  - OS keychain integration (`keyring` library)
  - Token storage/retrieval
  - Metadata caching
  - Token expiry checking
  - Exception handling

**Checklist:**
- [ ] Create `AuthStore` class
- [ ] Add `keyring>=23.0.0` dependency
- [ ] Test OS keychain locally
- [ ] Write unit tests

**Tests needed:**
- Token set/get/clear
- Expiry checking
- Authentication status
- Cache behavior

### Phase 2: Runtime Integration (1-2 days)
- File: `kiwi_mcp/executor.py` (update)
- Features:
  - Token injection into HTTP headers
  - Scope validation
  - Error handling
  - Tool definition updates

**Checklist:**
- [ ] Integrate `AuthStore` into `PrimitiveExecutor`
- [ ] Add auth injection logic
- [ ] Update tool config schema (`required_scope`)
- [ ] Handle `AuthenticationRequired` exceptions
- [ ] Write integration tests

**Tests needed:**
- Auth injection with authenticated tools
- Public tools (no auth)
- Missing credentials error handling

### Phase 3: User Commands & Auth Flow (1-2 days)
- Files: `kiwi_mcp/cli/auth.py` (new)
- Features:
  - `kiwi auth signin` command
  - `kiwi auth logout` command
  - `kiwi auth status` command
  - Supabase Auth integration
  - Token refresh lifecycle

**Checklist:**
- [ ] Implement signin flow
- [ ] Implement logout flow
- [ ] Implement status command
- [ ] Handle refresh tokens
- [ ] User documentation

**Tests needed:**
- E2E authentication flow
- Token refresh
- Logout and re-auth

---

## Track 2: Supabase Removal

**Duration:** 2-3 days  
**Dependencies:** Auth Store Phase 1+2 must be complete
**Deliverable:** Core with no Supabase SDK

### Phase 1: Remove SDK (1-2 days)
- Delete registry API classes
- Remove vector store integration
- Update handlers (no publish/delete)
- Remove `supabase` dependency

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

**Checklist:**
- [ ] Delete all registry API files (complete, no stubs)
- [ ] Update handlers (no publish/delete actions)
- [ ] Remove registry from vector manager
- [ ] Update search/load/execute tools
- [ ] Remove Supabase dependency
- [ ] No backwards compat code or comments
- [ ] Run tests (core must work offline)

### Phase 2: Registry Tool (1 day)
- File: `.ai/tools/core/registry.py`
- Features:
  - HTTP-based registry operations
  - Upload, download, search, publish, delete, etc.
  - Uses `http_client` primitive
  - Declares `required_scope` for auth injection

**Operations:**
- search, get, download (public)
- upload, publish, private, unlist, delete (authenticated)
- list, update, versions, stats

**Checklist:**
- [ ] Create `.ai/tools/core/registry.py`
- [ ] Define executor chain: `registry → http_client`
- [ ] Implement all operations
- [ ] Add scope declarations
- [ ] Test tool discovery
- [ ] Test executor chain resolution

### Phase 3: Integration & Testing (1 day)
- Unit tests for registry tool
- Integration tests with auth injection
- E2E workflows
- Documentation updates

**Checklist:**
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Auth injection works
- [ ] Public and authenticated operations work
- [ ] Documentation updated

---

## Track 3: Registry Tool (Parallel)

**Duration:** 1-2 days  
**Dependencies:** Supabase Removal Phase 2
**Deliverable:** Full registry operations via HTTP

This is part of Supabase Removal but can be worked on in parallel after Phase 1.

See SUPABASE_DECOUPLING_PLAN.md Phase 2 for details.

---

## Execution Order

### Week 1

**Monday-Tuesday: Auth Store Phase 1**
- Create `AuthStore` class with OS keychain
- Add `keyring` dependency
- Unit tests

**Wednesday: Auth Store Phase 2**
- Integrate into `PrimitiveExecutor`
- Token injection
- Integration tests

**Thursday-Friday: Auth Store Phase 3**
- User commands (`kiwi auth signin`, etc.)
- Supabase Auth integration
- E2E tests

### Week 2

**Monday: Supabase Removal Phase 1**
- Delete registry API files
- Update handlers
- Remove dependency

**Tuesday-Wednesday: Registry Tool (Phase 2)**
- Create `.ai/tools/core/registry.py`
- Implement all operations
- Test with auth injection

**Thursday-Friday: Integration & Testing (Phase 3)**
- Full integration tests
- E2E workflows
- Documentation

---

## Risk Mitigation

### Risk: Token Refresh Complexity
**Mitigation:** Implement Phase 3 carefully with thorough testing. Have fallback to re-auth.

### Risk: Breaking Changes
**Mitigation:** No backwards compat in code - users migrate to registry tool via documentation.

### Risk: Network Failures
**Mitigation:** HttpClientPrimitive has retry logic. Add timeout handling in registry tool.

### Risk: OS Keychain Issues
**Mitigation:** Test on all three platforms (macOS, Windows, Linux) during Phase 1.

---

## Success Criteria

### Auth Store
- ✅ Tokens stored in OS keychain (encrypted)
- ✅ Auto-refresh on expiry
- ✅ No token visibility to agents
- ✅ All unit tests pass
- ✅ E2E signin/logout workflow works

### Supabase Removal
- ✅ Core has no Supabase dependency
- ✅ Core works offline
- ✅ No publish/delete in execute tool
- ✅ No backwards compat code
- ✅ All tests pass

### Registry Tool
- ✅ All 12 operations work
- ✅ Auth injection works for write operations
- ✅ Public read operations work (no auth)
- ✅ Executor chain works: `registry → http_client`
- ✅ All integration tests pass

---

## References

- [AUTH_STORE_IMPLEMENTATION.md](./AUTH_STORE_IMPLEMENTATION.md) - Phase 1-3 details
- [SUPABASE_DECOUPLING_PLAN.md](./SUPABASE_DECOUPLING_PLAN.md) - Phase 1-3 details
- [AGENT_CREDENTIAL_SECURITY.md](./AGENT_CREDENTIAL_SECURITY.md) - Architecture & security
- [UNIFIED_TOOLS_ARCHITECTURE.md](./UNIFIED_TOOLS_ARCHITECTURE.md) - Executor chains

---

_Generated: 2026-01-26_
