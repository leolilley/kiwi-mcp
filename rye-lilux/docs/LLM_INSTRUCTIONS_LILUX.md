# LLM Instructions: Complete Lilux Documentation

**Task:** Fill out all 16 Lilux microkernel documentation files following the roadmap

**Roadmap:** `/home/leo/projects/kiwi-mcp/rye-lilux/docs/LILUX_DOCS_ROADMAP.md`
**Reference Architecture:** `/home/leo/projects/kiwi-mcp/rye-lilux/docs/ARCHITECTURE.md`

---

## CRITICAL: Follow These Rules

### 1. **Source Verification REQUIRED**
- Every file already has a source line: `**Source:** Original implementation: {path} in kiwi-mcp`
- **READ the source file FIRST** before writing documentation
- **Copy actual examples** from the source implementation
- **Do NOT invent features** that don't exist in kiwi-mcp

### 2. **Lilux = Microkernel (Dumb)**
- Lilux provides **generic execution primitives only**
- **NO content intelligence** (no XML parsing, no metadata understanding)
- **NO tool discovery** (that's RYE's job)
- **NO universal executor** (that's RYE's job)

### 3. **Architecture Separation**
- **Lilux:** Code implementations in `lilux/` package
- **RYE:** Schemas in `.ai/tools/rye/` + universal executor
- **Clear separation:** Don't mix responsibilities

### 4. **Cross-Reference Pattern**
Use backlinks to related concepts:
- `[[rye/categories/primitives]]` - Link to RYE primitive schemas
- `[[rye/universal-executor/overview]]` - Link to RYE's executor
- `[[rye/mcp-server]]` - Link to RYE's MCP server

---

## Phase 1: Core Microkernel Documentation

### Task 1.1: Principles and Package Structure (30 min)

**Files to complete:**
- `docs/lilux/principles.md` (already has foundation)
- `docs/lilux/package/structure.md`

**Instructions:**
1. **Read source:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/` package structure
2. **Expand principles.md** with:
   - What Lilux does vs doesn't do
   - Microkernel analogy (Linux kernel vs userspace)
   - Installation as library dependency
   - Clear separation from RYE
3. **Complete package/structure.md** with:
   - Actual `lilux/` directory layout
   - Purpose of each directory
   - What files exist vs what's planned

### Task 1.2: Primitives Documentation (45 min)

**Files to complete:**
- `docs/lilux/primitives/overview.md`
- `docs/lilux/primitives/subprocess.md` 
- `docs/lilux/primitives/http-client.md`
- **ADD:** `docs/lilux/primitives/lockfile.md`
- **ADD:** `docs/lilux/primitives/chain-validator.md`
- **ADD:** `docs/lilux/primitives/integrity.md`

**Instructions:**
1. **Read sources:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/primitives/*.py`
2. **Document each primitive:**
   - Purpose and functionality
   - Key methods and classes
   - Configuration patterns
   - How RYE uses it (link to `[[rye/categories/primitives]]`)
3. **Show `__executor_id__ = None` pattern**
4. **Copy actual code examples** from kiwi-mcp

### Task 1.3: Runtime Services (30 min)

**Files to complete:**
- `docs/lilux/runtime-services/auth-store.md`
- `docs/lilux/runtime-services/env-resolver.md`
- `docs/lilux/runtime-services/lockfile-store.md`

**Instructions:**
1. **Read sources:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/runtime/*.py`
2. **Document each service:**
   - AuthStore: Keychain integration, token management
   - EnvResolver: Template variable resolution, ENV_CONFIG processing
   - LockfileStore: Concurrency management
3. **Show how RYE's universal executor uses these**
4. **Link to RYE's ENV_CONFIG usage:** `[[rye/categories/runtimes]]`

---

## Phase 2: Supporting Infrastructure

### Task 2.1: Configuration and Storage (30 min)

**Files to complete:**
- `docs/lilux/config/overview.md`
- `docs/lilux/storage/overview.md`

**Instructions:**
1. **Read sources:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/config/*.py`, `/home/leo/projects/kiwi-mcp/kiwi_mcp/storage/vector/*.py`
2. **Document configuration:**
   - search_config.py and vector_config.py
   - How these support tool discovery
3. **Document vector storage:**
   - RAG support for knowledge base
   - Vector embedding and search
   - How RYE uses this for knowledge tools

### Task 2.2: Schemas and Utils (30 min)

**Files to complete:**
- `docs/lilux/schemas/overview.md`
- `docs/lilux/schemas/tool-schema.md`
- `docs/lilux/utils/overview.md`

**Instructions:**
1. **Read sources:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/schemas/*.py`, `/home/leo/projects/kiwi-mcp/kiwi_mcp/utils/*.py`
2. **Document schemas:**
   - tool_schema.py: JSON Schema definitions
   - How RYE uses these for validation
3. **Document utils:**
   - Minimal helpers only (resolvers, logger, paths)
   - **Emphasize "minimal"** - no content intelligence
   - Contrast with RYE's rich utils

### Task 2.3: Handlers and Legacy Tools (30 min)

**Files to complete:**
- `docs/lilux/handlers/overview.md`
- `docs/lilux/tools/overview.md` (already marked as legacy)
- `docs/lilux/tools/mcp-tools.md` (already marked as legacy)

**Instructions:**
1. **Read sources:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/*.py`, `/home/leo/projects/kiwi-mcp/kiwi_mcp/tools/*.py`
2. **Document handlers:**
   - Dumb routing only (no content intelligence)
   - How they resolve file paths
   - How they differ from RYE's smart handlers
3. **Confirm legacy tools status:**
   - Mark as deprecated/not used
   - Point to RYE's MCP server instead

---

## Validation Requirements

### Before Completing Each File:
- [ ] **Read the source file** in kiwi-mcp
- [ ] **Verify examples** match actual implementation
- [ ] **Check cross-references** point to correct files
- [ ] **Confirm microkernel principle** (dumb, no intelligence)

### Content Structure for Each File:
```markdown
**Source:** Original implementation: `{path}` in kiwi-mcp

# {Title}

## Purpose
What this component does in the microkernel

## Key Files
List actual files with descriptions

## Architecture Role
How it fits in the microkernel (Layer 1)

## RYE Relationship
How RYE uses this component (with links)

## Examples
Code snippets from kiwi-mcp source
```

### Cross-Reference Links:
- `[[rye/categories/primitives]]` - RYE primitive schemas
- `[[rye/universal-executor/overview]]` - RYE's executor
- `[[rye/mcp-server]]` - RYE's MCP server
- `[[rye/categories/runtimes]]` - RYE runtime schemas

---

## Success Criteria

### ✅ **Accurate Documentation**
- All examples copied from actual kiwi-mcp code
- No invented features or capabilities
- Clear microkernel boundaries maintained

### ✅ **Complete Coverage**
- All 9 Lilux package directories documented
- All key files explained with purpose
- Legacy components clearly marked

### ✅ **Architecture Alignment**
- Lilux = dumb primitives and services
- RYE = smart content understanding
- Clear separation of responsibilities

### ✅ **Navigation Network**
- Cross-references to related RYE docs
- Consistent terminology across all files
- Easy navigation between concepts

---

## Common Mistakes to Avoid

### ❌ **Don't Give Lilux Intelligence**
- "Lilux parses XML" → NO, RYE does that
- "Lilux understands tools" → NO, RYE does that
- "Lilux provides tool discovery" → NO, RYE does that

### ❌ **Don't Invent Features**
- Only document what exists in kiwi-mcp
- Don't add capabilities that aren't implemented
- Don't describe future features as current

### ❌ **Don't Mix Responsibilities**
- Keep Lilux docs focused on microkernel only
- Point to RYE for intelligence features
- Maintain clear boundaries

---

**Estimated Time:** 3 hours total
**Order:** Follow roadmap phases (1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 2.3)
**Validation:** Read source files, verify examples, check cross-references