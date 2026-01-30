# Lilux Documentation Roadmap

**Purpose:** Two parallel goals:
1. **ARCHITECTURE DOCS** (Primary) - Describe intended architecture + existing code
2. **KNOWLEDGE-BASE DOCS** (Secondary) - Create 16 knowledge entries for reference

**Status:**
- ✅ Architecture docs complete: `ARCHITECTURE.md`, `COMPLETE_DATA_DRIVEN_ARCHITECTURE.md`
- ⏳ Knowledge-base entries: Optional, can be created after implementation

**Note:** This roadmap covers documentation creation. For **implementation roadmap**, see `COMPLETE_DATA_DRIVEN_ARCHITECTURE.md` Phases 6.1-6.6.

---

## Implementation Phases (Architecture Build)

**See:** `COMPLETE_DATA_DRIVEN_ARCHITECTURE.md` Phases 6.1-6.6 for detailed implementation steps

**Quick View:**
- **Phase 6.1:** Copy primitive schemas to `.ai/tools/rye/primitives/`
- **Phase 6.2:** Create runtime schemas in `.ai/tools/rye/runtimes/`
- **Phase 6.3:** Implement `rye/executor/universal_executor.py`
- **Phase 6.4:** Bundle all 14 tool categories to `rye/.ai/tools/rye/`
- **Phase 6.5:** Implement YAML config loading
- **Phase 6.6:** Implement tool discovery (recursive scan)

**Code Status:**
- ✅ All Lilux primitives exist (no coding needed)
- ✅ All runtime services exist (use in executor)
- ✅ .ai/ bundle structure ready (copy from kiwi-mcp)
- ⏳ Universal executor needs building (orchestration logic)

---

## Phase 1: Core Microkernel Documentation (Priority 1)

### 1.1: Principles and Package Structure
**Files:** `principles.md`, `package/structure.md`
**Time:** 30 min
**Dependencies:** None

**Tasks:**
- [ ] Expand `principles.md` with microkernel vs OS comparison
- [ ] Complete `package/structure.md` with actual lilux/ directory layout
- [ ] Add cross-references to RYE docs
- [ ] Verify source links to kiwi-mcp

### 1.2: Primitives Documentation
**Files:** `primitives/overview.md`, `primitives/subprocess.md`, `primitives/http-client.md`
**Time:** 45 min
**Dependencies:** 1.1

**Tasks:**
- [ ] Document all 5 primitives (subprocess, http_client, lockfile, auth, chain_validator)
- [ ] Add missing primitive docs: `lockfile.md`, `auth.md`, `chain-validator.md`
- [ ] Explain `__executor_id__ = None` pattern
- [ ] Show CONFIG_SCHEMA examples from kiwi-mcp
- [ ] Link to corresponding RYE schemas: `[[rye/categories/primitives]]`

### 1.3: Runtime Services
**Files:** `runtime-services/auth-store.md`, `runtime-services/env-resolver.md`, `runtime-services/lockfile-store.md`
**Time:** 30 min
**Dependencies:** 1.2

**Tasks:**
- [ ] Document AuthStore (keychain integration)
- [ ] Document EnvResolver (template variable resolution)
- [ ] Document LockfileStore (concurrency management)
- [ ] Show how these support the universal executor
- [ ] Cross-reference to RYE's ENV_CONFIG usage

---

## Phase 2: Supporting Infrastructure (Priority 2)

### 2.1: Configuration and Storage
**Files:** `config/overview.md`, `storage/overview.md`
**Time:** 30 min
**Dependencies:** 1.3

**Tasks:**
- [ ] Document search_config.py and vector_config.py
- [ ] Document vector storage layer (RAG support)
- [ ] Explain how RYE uses these for tool discovery
- [ ] Link to RYE's universal executor: `[[rye/universal-executor/overview]]`

### 2.2: Schemas and Utils
**Files:** `schemas/overview.md`, `schemas/tool-schema.md`, `utils/overview.md`
**Time:** 30 min
**Dependencies:** 2.1

**Tasks:**
- [ ] Document tool_schema.py (JSON Schema definitions)
- [ ] Document minimal utils (resolvers, logger, paths, extensions)
- [ ] Explain "minimal" principle (no content intelligence)
- [ ] Contrast with RYE's rich utils: `[[rye/content-handlers/overview]]`

### 2.3: Handlers and Legacy Tools
**Files:** `handlers/overview.md`, `tools/overview.md`, `tools/mcp-tools.md`
**Time:** 30 min
**Dependencies:** 2.2

**Tasks:**
- [ ] Document dumb routing handlers (no content intelligence)
- [ ] Mark legacy MCP tools as deprecated
- [ ] Explain migration to RYE MCP server
- [ ] Add clear warnings about what NOT to use

---

## Documentation Standards

### Source Linking
Every file must start with:
```markdown
**Source:** Original implementation: `kiwi_mcp/{path}` in kiwi-mcp
```

### Cross-References
Use backlinks to related concepts:
- `[[rye/categories/primitives]]` - Link to RYE primitive schemas
- `[[rye/mcp-server]]` - Link to RYE MCP implementation
- `[[rye/universal-executor/overview]]` - Link to universal executor

### Content Structure
1. **Purpose** - What this component does
2. **Key Files** - List actual files with descriptions
3. **Architecture Role** - How it fits in microkernel
4. **RYE Relationship** - How RYE uses this component
5. **Examples** - Code snippets from kiwi-mcp

### Validation Checklist
- [ ] Source link points to actual kiwi-mcp file
- [ ] No content intelligence claims (Lilux is dumb)
- [ ] Clear separation from RYE responsibilities
- [ ] Cross-references to related RYE docs
- [ ] Examples match kiwi-mcp implementation

---

## Success Criteria

### ✅ Complete Coverage
- All 9 Lilux package directories documented
- All key files explained with purpose
- Clear architecture role for each component

### ✅ Accurate Separation
- Lilux = dumb primitives and services
- RYE = smart content understanding
- No confusion about responsibilities

### ✅ Migration Clarity
- Legacy components clearly marked
- Correct usage patterns documented
- Clear path to RYE for actual usage

### ✅ Cross-Reference Network
- Links to related RYE documentation
- Consistent terminology across docs
- Easy navigation between concepts

---

**Estimated Total Time:** 3 hours
**Priority:** Complete before RYE documentation
**Dependencies:** Architecture docs must be stable first