# LLM Documentation Instructions: Building Accurate rye-lilux Knowledge Base

**Purpose:** Ensure LLMs build accurate documentation without corrupting the architecture

**Problem:** LLMs consistently misunderstand the rye-lilux architecture and create incorrect documentation that contradicts the established design principles.

---

## Core Architecture Principles (DO NOT DEVIATE)

### 1. Package Separation

- **Lilux** = Microkernel package (`pip install lilux`)
- **RYE** = OS package (`pip install rye-lilux`)
- **Monorepo** = Both developed together, packaged separately

### 2. MCP Entry Point

- **RYE is the main MCP server** (`python -m rye.server`)
- **Lilux is NOT an MCP server** (it's a dependency library)
- **LLMs call `mcp__rye__*`** (not `mcp__lilux__*`)

### 3. Tool Organization

```
.ai/tools/
├── rye/           # ← "rye" IS a category name
│   ├── primitives/
│   ├── runtimes/
│   ├── capabilities/
│   ├── telemetry/
│   ├── extractors/
│   ├── parsers/
│   ├── protocol/
│   ├── sinks/
│   ├── threads/
│   ├── mcp/
│   ├── llm/
│   ├── registry/
│   └── utility/
├── python/        # ← "python" IS a separate category
│   ├── lib/
│   └── *.py
└── {other-categories}/
```

### 4. Schema/Code Separation

- **Primitive schemas** → `.ai/tools/rye/primitives/*.py` (metadata only)
- **Primitive code** → `lilux/primitives/*.py` (implementation)
- **Runtime schemas** → `.ai/tools/rye/runtimes/*.py` (ENV_CONFIG + metadata)
- **Runtime code** → May be in `lilux/runtimes/*.py` or runtime-executed

### 5. Everything is a Tool

- Primitives are tools (with schemas)
- Runtimes are tools (with schemas)
- Capabilities are tools
- Telemetry tools are tools
- No special "core" distinction - just categories

---

## Common LLM Mistakes (AVOID THESE)

### ❌ Wrong: Category Confusion

```
.ai/tools/
└── rye/
    └── rye/          # ← WRONG: Double nesting
        └── primitives/
```

### ✅ Correct: Category Structure

```
.ai/tools/
└── rye/              # ← "rye" is the category name
    └── primitives/
```

### ❌ Wrong: MCP Entry Point

- "Lilux provides MCP server"
- "LLM calls `mcp__lilux__*`"
- "User runs `python -m lilux.server`"

### ✅ Correct: MCP Entry Point

- "RYE provides MCP server"
- "LLM calls `mcp__rye__*`"
- "User runs `python -m rye.server`"

### ❌ Wrong: Runtime Location

- "Runtimes live in `lilux/runtimes/`"
- "Runtimes are part of Lilux package"

### ✅ Correct: Runtime Location

- "Runtime schemas live in `.ai/tools/rye/runtimes/`"
- "Runtime code may be in `lilux/runtimes/` or runtime-executed"

### ❌ Wrong: Tool Categories

- "Core tools are special"
- "Primitives are not tools"
- "Only 5 hardcoded tools"

### ✅ Correct: Tool Categories

- "Everything is a tool organized by category"
- "Primitives are tools with schemas"
- "Auto-discovery from `.ai/tools/`"

---

## Documentation Writing Protocol

### Step 1: Identify Source

Every doc MUST start with source line:

```markdown
**Source:** Original implementation: `{path}` in kiwi-mcp
```

### Step 2: Verify Category

Check the category structure:

- Is this under `.ai/tools/rye/`?
- Is this under `.ai/tools/python/`?
- Is this a separate category?

### Step 3: Check Architecture Alignment

Before writing, verify:

- Does this contradict the package separation?
- Does this contradict the MCP entry point?
- Does this contradict the tool organization?
- Does this contradict the schema/code separation?

### Step 4: Use Grounded Examples

Reference actual files from kiwi-mcp:

- `.ai/tools/primitives/subprocess.py`
- `.ai/tools/runtimes/python_runtime.py`
- `.ai/tools/capabilities/git.py`
- `.ai/parsers/markdown_xml.py`

### Step 5: Cross-Reference

Link to related docs:

- `[[primitives]]` for primitive references
- `[[runtimes]]` for runtime references
- `[[categories/overview]]` for category explanations

---

## Validation Checklist

Before finalizing any documentation, verify:

### ✅ Architecture Alignment

- [ ] RYE is main MCP entry point (not Lilux)
- [ ] Tools organized by category (rye, python, etc.)
- [ ] Schema/code separation maintained
- [ ] Everything is a tool principle followed

### ✅ Source Traceability

- [ ] Source line points to actual kiwi-mcp file
- [ ] Examples reference real implementations
- [ ] No invented features or capabilities

### ✅ Consistency

- [ ] Terminology matches across all docs
- [ ] Category names consistent
- [ ] Package names consistent (lilux vs rye-lilux)

### ✅ Completeness

- [ ] Covers the specific topic thoroughly
- [ ] Links to related concepts
- [ ] Provides concrete examples

---

## Emergency Reset Protocol

If documentation becomes corrupted or inconsistent:

### 1. Return to Source

- Re-read the source implementation in kiwi-mcp
- Verify the actual file structure
- Check the actual metadata patterns

### 2. Verify Architecture

- Re-read `docs/ARCHITECTURE.md`
- Re-read `docs/COMPLETE_DATA_DRIVEN_ARCHITECTURE.md`
- Confirm the package separation principles

### 3. Rebuild from Principles

- Start with the core architecture principles
- Add one concept at a time
- Verify each addition against the source

---

## Success Metrics

Documentation is successful when:

### ✅ LLM Understanding

- LLM correctly identifies RYE as MCP entry point
- LLM correctly organizes tools by category
- LLM correctly separates schemas from code
- LLM correctly references source implementations

### ✅ Implementation Guidance

- Developer can implement based on docs alone
- No contradictions between docs
- Clear migration path from kiwi-mcp
- Concrete examples for every concept

### ✅ Maintainability

- Easy to update when implementation changes
- Clear source traceability
- Modular structure allows targeted updates
- Cross-references prevent drift

---

## Final Reminder

**The goal is NOT to document what we wish existed.**
**The goal is to document the correct architecture so it can be implemented accurately.**

Every line should be traceable to either:

1. Existing kiwi-mcp implementation
2. Established architecture principles
3. Necessary adaptations for the new structure

**When in doubt, reference the source. When confused, return to principles.**

---

**Document Status:** LLM Instruction Guide
**Last Updated:** 2026-01-30
**Author:** Architecture Team

