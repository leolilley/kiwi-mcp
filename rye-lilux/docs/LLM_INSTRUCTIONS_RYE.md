# LLM Instructions: Complete RYE Documentation

**Task:** Fill out all 26 RYE operating system documentation files following the roadmap

**Roadmap:** `/home/leo/projects/kiwi-mcp/rye-lilux/docs/RYE_DOCS_ROADMAP.md`
**Reference Architecture:** `/home/leo/projects/kiwi-mcp/rye-lilux/docs/ARCHITECTURE.md`

---

## CRITICAL: Follow These Rules

### 1. **Source Verification REQUIRED**
- Every file already has a source line: `**Source:** Original implementation: {path} in kiwi-mcp`
- **READ the source file/directory FIRST** before writing documentation
- **Copy actual tool metadata** from kiwi-mcp `.ai/tools/`
- **Reference real YAML configs** from kiwi-mcp
- **Do NOT invent tools** that don't exist

### 2. **RYE = Operating System (Smart)**
- RYE provides **universal executor** with tool auto-discovery
- RYE understands **content shapes** (XML, frontmatter, metadata)
- RYE provides **5 MCP tools** (search, load, execute, sign, help)
- RYE bundles **complete .ai/ tool collection**

### 3. **Category Organization**
- **Everything under `.ai/tools/rye/`** (RYE's bundled tools)
- **17 categories:** primitives, runtimes, capabilities, telemetry, extractors, parsers, protocol, sinks, threads, mcp, llm, registry, utility, examples
- **No python category** in base RYE package
- **Each category** has specific tools from kiwi-mcp

### 4. **Tool Metadata Patterns**
Copy exact metadata from kiwi-mcp:
- `__tool_type__ = "primitive"` (primitives)
- `__tool_type__ = "runtime"` (runtimes)  
- `__tool_type__ = "python"` (Python tools)
- `__executor_id__` values: `None`, `"subprocess"`, `"http_client"`, `"python_runtime"`

---

## Phase 1: Core RYE Architecture (2 hours)

### Task 1.1: Principles and Package Structure (30 min)

**Files to complete:**
- `docs/rye/principles.md` (already has foundation)
- `docs/rye/package/structure.md`

**Instructions:**
1. **Read source:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/` package structure
2. **Expand principles.md** with:
   - RYE as operating system layer
   - Universal executor concept
   - Data-driven tool discovery
   - Relationship to Lilux microkernel
3. **Complete package/structure.md** with:
   - Actual `rye/` directory layout
   - Purpose of each directory
   - How .ai/ bundle is packaged

### Task 1.2: Universal Executor Documentation (1 hour)

**Files to complete:**
- `docs/rye/universal-executor/overview.md`
- `docs/rye/universal-executor/routing.md`

**Instructions:**
1. **Read source:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/primitives/executor.py` (the current universal executor)
2. **Document architecture:**
   - How tool metadata is parsed
   - Three-layer routing (primitives → runtimes → tools)
   - ENV_CONFIG resolution process
   - Tool auto-discovery from `.ai/tools/`
3. **Show routing examples:**
   - Primitive tool → direct to Lilux
   - Runtime tool → ENV_CONFIG resolution → Lilux
   - Python tool → python_runtime → subprocess primitive

### Task 1.3: Content Bundle Structure (30 min)

**Files to complete:**
- `docs/rye/bundle/structure.md`

**Instructions:**
1. **Read source:** `/home/leo/projects/kiwi-mcp/.ai/` directory structure
2. **Document complete .ai/ layout:**
   - All 17 tool categories under `.ai/tools/rye/`
   - Directives organization
   - Knowledge organization
3. **Show auto-discovery process:**
   - How RYE scans `.ai/tools/rye/`
   - How metadata is extracted
   - How tool registry is built

---

## Phase 2: Tool Categories Documentation (4 hours)

### Task 2.1: Core RYE Categories (45 min)

**Files to complete:**
- `docs/rye/categories/rye.md`
- `docs/rye/categories/primitives.md`
- `docs/rye/categories/runtimes.md`

**Instructions:**
1. **Read sources:** 
   - `/home/leo/projects/kiwi-mcp/.ai/tools/primitives/*.py`
   - `/home/leo/projects/kiwi-mcp/.ai/tools/runtimes/*.py`
2. **Document RYE category concept:**
   - What "rye" category means (bundled tools)
   - How it differs from other categories
3. **Document primitive schemas:**
   - Copy actual CONFIG_SCHEMA from kiwi-mcp
   - Show `__executor_id__ = None` pattern
   - Link to Lilux implementations
4. **Document runtime schemas:**
   - Copy actual ENV_CONFIG from kiwi-mcp
   - Show template variable usage (`${RYE_PYTHON}`)
   - Explain environment resolution

### Task 2.2: System Infrastructure Categories (1 hour)

**Files to complete:**
- `docs/rye/categories/capabilities.md`
- `docs/rye/categories/telemetry.md`
- `docs/rye/categories/parsers.md`
- `docs/rye/categories/extractors.md`

**Instructions:**
1. **Read sources:**
   - `/home/leo/projects/kiwi-mcp/.ai/tools/capabilities/*.py`
   - `/home/leo/projects/kiwi-mcp/.ai/tools/core/telemetry*.py`
   - `/home/leo/projects/kiwi-mcp/.ai/parsers/*.py`
   - `/home/leo/projects/kiwi-mcp/.ai/extractors/`
2. **Document each category:**
   - List all actual files from kiwi-mcp
   - Show tool metadata patterns
   - Explain purpose and usage
   - Show executor_id values

### Task 2.3: Protocol and Communication Categories (45 min)

**Files to complete:**
- `docs/rye/categories/protocol.md`
- `docs/rye/categories/sinks.md`
- `docs/rye/categories/mcp.md`
- `docs/rye/categories/llm.md`

**Instructions:**
1. **Read sources:**
   - `/home/leo/projects/kiwi-mcp/.ai/tools/protocol/*.py`
   - `/home/leo/projects/kiwi-mcp/.ai/tools/sinks/*.py`
   - `/home/leo/projects/kiwi-mcp/.ai/tools/mcp/*.py` and `*.yaml`
   - `/home/leo/projects/kiwi-mcp/.ai/tools/llm/*.yaml`
2. **Document YAML configs:**
   - Copy actual YAML examples
   - Explain configuration patterns
   - Show how they're loaded dynamically

### Task 2.4: Execution and Threading Categories (45 min)

**Files to complete:**
- `docs/rye/categories/threads.md`
- `docs/rye/categories/registry.md`
- `docs/rye/categories/utility.md`
- `docs/rye/categories/examples.md`

**Instructions:**
1. **Read sources:**
   - `/home/leo/projects/kiwi-mcp/.ai/tools/threads/*.py` and `*.yaml`
   - `/home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/core/registry.py` (actual implementation)
   - `/home/leo/projects/kiwi-mcp/.ai/tools/utility/*.py`
   - `/home/leo/projects/kiwi-mcp/.ai/tools/examples/`
2. **Document registry correctly:**
   - Single `registry.py` file (not multiple files)
   - Uses `__executor_id__ = "http_client"`
   - All auth, push, pull, key operations

### Task 2.5: Categories Overview (30 min)

**Files to complete:**
- `docs/rye/categories/overview.md`

**Instructions:**
1. **Create master overview** of all 17 categories
2. **Show category relationships** and dependencies
3. **Document auto-discovery process**
4. **Link to all individual category docs**

---

## Phase 3: Tool Format and Content Handling (1.5 hours)

### Task 3.1: Tool Format Documentation (45 min)

**Files to complete:**
- `docs/rye/tool-format/python.md`
- `docs/rye/tool-format/yaml.md`

**Instructions:**
1. **Read sources:** Actual tool files from kiwi-mcp `.ai/tools/`
2. **Document Python tool pattern:**
   - Copy actual metadata examples
   - Show `__tool_type__`, `__executor_id__`, `__category__`
   - Document CONFIG_SCHEMA patterns
3. **Document YAML config pattern:**
   - Copy actual YAML files from kiwi-mcp
   - Show configuration structure
   - Explain dynamic loading

### Task 3.2: Content Handlers and MCP Server (30 min)

**Files to complete:**
- `docs/rye/content-handlers/overview.md`
- `docs/rye/mcp-server.md` (already has foundation)

**Instructions:**
1. **Read source:** `/home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/*.py`
2. **Document content intelligence:**
   - XML parsing for directives
   - Frontmatter parsing for knowledge
   - Metadata extraction for tools
3. **Expand MCP server docs:**
   - Complete configuration examples
   - Document all 5 MCP tools
   - Show tool auto-discovery process

---

## Validation Protocol

### Before Writing Each File:
1. **Read the source file/directory** in kiwi-mcp
2. **Verify the source link** points to correct location
3. **Check existing content** (don't overwrite good content)
4. **Plan cross-references** to related docs

### While Writing:
1. **Copy actual examples** from kiwi-mcp
2. **Use exact metadata** from source files
3. **Add cross-reference links** using `[[path]]` syntax
4. **Maintain consistent terminology**

### After Writing:
1. **Verify all examples** are copy-pasteable from kiwi-mcp
2. **Check cross-references** point to correct files
3. **Confirm architecture alignment** with big docs
4. **Test readability** and completeness

---

## Critical Success Factors

### ✅ **Source Accuracy**
- Every example copied from actual kiwi-mcp files
- No invented features or capabilities
- Metadata patterns match exactly

### ✅ **Architecture Consistency**
- RYE = smart OS layer with universal executor
- Lilux = dumb microkernel with primitives
- Clear separation maintained throughout

### ✅ **Complete Coverage**
- All 17 tool categories documented
- All tool types and formats covered
- All cross-references working

### ✅ **Implementation Guidance**
- Developers can implement based on docs alone
- Clear migration path from kiwi-mcp
- Concrete examples for every concept

---

## Emergency Protocols

### If You Get Confused:
1. **Stop and re-read** `/home/leo/projects/kiwi-mcp/rye-lilux/docs/ARCHITECTURE.md`
2. **Check the source** in kiwi-mcp for actual implementation
3. **Verify category structure** (rye/ only, no python/)
4. **Ask for clarification** rather than guessing

### If Examples Don't Match:
1. **Always trust kiwi-mcp source** over documentation
2. **Copy exact metadata** from source files
3. **Update docs** to match reality, not intentions

---

**Total Estimated Time:** 7.5 hours
**Dependencies:** Complete Lilux docs first
**Validation:** Every file must reference actual kiwi-mcp implementation