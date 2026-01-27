# Kiwi MCP Tooling Documentation - Index

**Created:** 2026-01-28  
**Status:** Corrected Implementation Documentation  
**Total Lines:** 1,820  
**Total Files:** 4 + This Index

---

## Quick Navigation

| Document | Purpose | Audience | Read Time |
|----------|---------|----------|-----------|
| [README.md](#readme) | Complete guide to Kiwi MCP tooling | Everyone | 15 min |
| [QUICK_START.md](#quick-start) | 5-minute setup and common patterns | Developers | 5 min |
| [TOOL_API_REFERENCE.md](#api-reference) | Detailed API documentation | API users | 10 min |
| [IMPLEMENTATION_NOTES.md](#implementation) | Deep dive into how it works | Maintainers | 20 min |

---

## README.md

**Comprehensive Overview of Kiwi MCP Tooling**

### What You'll Learn

- ✅ Corrected facts vs outdated documentation
- ✅ How tools are actually structured (Python files, not database)
- ✅ The 4 tool types: primitive, python, api, mcp_tool
- ✅ How the executor chain works
- ✅ Signature validation system
- ✅ Search and discovery
- ✅ Tool locations and organization
- ✅ Metadata extraction
- ✅ Complete execution flow
- ✅ Practical examples
- ✅ Current limitations
- ✅ Future roadmap
- ✅ Troubleshooting
- ✅ Best practices

### Key Sections

1. **Overview** - The 4 MCP tools
2. **Key Differences** - What's NOT implemented
3. **Tool Structure** - How tools look
4. **Tool Types** - primitive, python, api, mcp_tool
5. **Creating Tools** - Step-by-step guide
6. **Executor Chain** - How tools chain together
7. **Signature Validation** - File integrity checking
8. **Search & Discovery** - Finding tools
9. **Execution Flow** - Run through the system
10. **Examples** - Real code samples
11. **Limitations** - What's not yet done
12. **Future Roadmap** - What's planned
13. **Troubleshooting** - Common issues
14. **Best Practices** - Tips and tricks

---

## QUICK_START.md

**Get Started in 5 Minutes**

### What You'll Learn

- ✅ Create your first tool (3 steps)
- ✅ Common patterns to copy/paste
- ✅ File structure overview
- ✅ Required metadata fields
- ✅ Tool types at a glance
- ✅ How to search tools
- ✅ Quick troubleshooting

### Perfect For

- First-time users
- Copy-paste patterns
- Quick reference
- Code examples

### Sections

1. **5-Minute Setup** - Create → Sign → Run
2. **Common Patterns** - Input/Output, API, Dependencies
3. **File Structure** - Where things live
4. **Metadata Fields** - Required variables
5. **Tool Types** - Quick comparison
6. **Search Tools** - Finding what you need
7. **Troubleshoot** - Quick fixes
8. **Next Steps** - Where to go from here

---

## TOOL_API_REFERENCE.md

**Complete API Documentation**

### What You'll Learn

- ✅ All 4 MCP tools: search, load, execute, help
- ✅ Parameters and return values
- ✅ All possible error responses
- ✅ Tool file format requirements
- ✅ Executor chain details

### Perfect For

- API integration
- Tool development
- Integration testing
- Reference lookup

### Tools Documented

1. **search** - Parameters, returns, examples, algorithm
2. **load** - Read-only vs copy modes, returns
3. **execute: run** - Parameters, return values, examples
4. **execute: sign** - Signature creation, validation
5. **help** - General and topic-specific help
6. **Error Responses** - All error types and solutions
7. **Tool File Format** - Required signature, metadata, function
8. **Executor Chain** - How resolution works

---

## IMPLEMENTATION_NOTES.md

**Deep Dive into Architecture**

### What You'll Learn

- ✅ Architecture overview (4 tools → 3 handlers)
- ✅ File structure (local vs user space)
- ✅ Metadata extraction algorithm
- ✅ Complete execution flow (search → load → run → sign)
- ✅ PrimitiveExecutor design
- ✅ Signature validation implementation
- ✅ Tool resolution algorithm
- ✅ Validation system
- ✅ Output management
- ✅ Auto-dependency detection
- ✅ Performance analysis
- ✅ Current limitations
- ✅ Future roadmap

### Perfect For

- Contributing to Kiwi MCP
- Debugging issues
- Understanding design decisions
- Performance optimization
- Feature development

### Sections

1. **Architecture Overview** - Diagram of 4 tools
2. **File Structure** - Local, user, output directories
3. **Tool Metadata Extraction** - AST parsing details
4. **Execution Flow** - Search → Load → Run → Sign
5. **PrimitiveExecutor** - Chain building and execution
6. **Signature Validation** - Hash calculation and checking
7. **Tool Resolution** - Where tools are found
8. **Metadata Validation** - Validation rules
9. **Output Management** - Where results are saved
10. **Dependencies** - Auto-detection algorithm
11. **Performance** - Complexity and bottlenecks
12. **Limitations & TODOs** - What's missing

---

## What Changed From Previous Docs

### ❌ Removed (Incorrect Information)

- Database schema (tools, tool_versions, tool_version_files) - NOT implemented
- Registry support for tools - NOT implemented
- Tool creation via API (`create` action) - NOT implemented
- Tool publishing to registry (`publish` action) - NOT implemented
- Automatic venv creation - NOT implemented
- Automatic dependency installation - NOT implemented
- Separate MCP server management - NOT implemented
- Unified tools table - FUTURE, not now

### ✅ Added (Correct Information)

- Python file-based tools with metadata headers
- Simple executor chain using `__executor_id__`
- 4 tool types: primitive, python, api, mcp_tool
- Signature validation with SHA256 hashes
- Local file operations only
- Metadata extraction from docstrings and `__*__` variables
- Complete execution flow details
- Implementation details and architecture

---

## How to Use These Docs

### I'm new to Kiwi MCP

1. Start: **QUICK_START.md** (5 min)
2. Then: **README.md** - Full context (15 min)
3. Reference: **TOOL_API_REFERENCE.md** - Look things up

### I'm building a tool

1. Copy pattern from: **QUICK_START.md**
2. Reference parameters: **TOOL_API_REFERENCE.md**
3. Check examples: **README.md** - Examples section

### I'm integrating via API

1. Study: **TOOL_API_REFERENCE.md**
2. Understand flow: **IMPLEMENTATION_NOTES.md**
3. Check examples: All documents have examples

### I'm contributing to Kiwi MCP

1. Understand: **IMPLEMENTATION_NOTES.md**
2. Reference code:
   - `kiwi_mcp/handlers/tool/handler.py`
   - `kiwi_mcp/primitives/executor.py`
   - `kiwi_mcp/schemas.py`
3. See flow: **README.md** - Execution Flow section

### I'm debugging an issue

1. **QUICK_START.md** - Troubleshoot section
2. **README.md** - Troubleshooting section
3. **IMPLEMENTATION_NOTES.md** - Architecture details
4. Code: Check relevant `.py` files

---

## Key Concepts

### Tools
Python files with metadata headers that can be executed via MCP. Located in `.ai/tools/` or `~/.ai/tools/`.

### Metadata
Information about a tool extracted from:
- `__version__` variable
- `__tool_type__` variable
- `__executor_id__` variable
- `__category__` variable
- Module docstring

### Executor Chain
Chain of tool references from tool → runtime → primitive. Each tool has an `__executor_id__` pointing to the next tool in the chain.

### Primitives
Hard-coded implementations (subprocess, http_client) that cannot be overridden. Form the bottom of all executor chains.

### Signature
File integrity check: `# kiwi-mcp:validated:{TIMESTAMP}Z:{HASH}`

### Resolution
Finding a tool file by name. Searches project tools first, then user tools.

### Validation
Checking that file content matches the stored hash in the signature.

---

## File Locations

```
docs/20260128_mcp_tooling_guide/
├── INDEX.md                    (this file)
├── README.md                   (comprehensive guide)
├── QUICK_START.md              (5-minute setup)
├── TOOL_API_REFERENCE.md       (API docs)
└── IMPLEMENTATION_NOTES.md     (deep dive)
```

---

## Implementation References

The actual implementation can be found in:

| File | Purpose |
|------|---------|
| `kiwi_mcp/server.py` | MCP server entry point |
| `kiwi_mcp/tools/search.py` | SearchTool |
| `kiwi_mcp/tools/load.py` | LoadTool |
| `kiwi_mcp/tools/execute.py` | ExecuteTool |
| `kiwi_mcp/tools/help.py` | HelpTool |
| `kiwi_mcp/handlers/tool/handler.py` | ToolHandler (main logic) |
| `kiwi_mcp/primitives/executor.py` | PrimitiveExecutor |
| `kiwi_mcp/schemas.py` | Metadata extraction |
| `kiwi_mcp/utils/resolvers.py` | Tool resolution |
| `kiwi_mcp/utils/validators.py` | Validation logic |
| `kiwi_mcp/utils/output_manager.py` | Output management |

---

## Corrections Summary

### Previous Docs Said
- Tools stored in database with versions table
- Registry support for tools
- Tool creation and publishing APIs
- Automatic venv and dependency management

### Actual Implementation
- Tools stored as Python files with metadata headers
- Local-only operations
- No creation or publishing APIs yet
- Manual dependency management

### Future Plans (Phase 2-4)
- Database tables for tools
- Registry support
- Venv isolation
- Auto-dependency installation
- Tool creation and publishing APIs

---

## Feedback

If you find:
- ❌ Incorrect information
- ❌ Missing details
- ❌ Broken examples
- ❌ Confusing sections

Please check the actual code in `kiwi_mcp/` and update these docs accordingly.

---

## Document Stats

| Metric | Value |
|--------|-------|
| Total Documents | 4 + Index |
| Total Lines | ~1,820 |
| README.md | 630 lines |
| QUICK_START.md | 154 lines |
| TOOL_API_REFERENCE.md | 455 lines |
| IMPLEMENTATION_NOTES.md | 581 lines |
| Created | 2026-01-28 |
| Version | 1.0.0 |

---

## License

These documentation files are part of Kiwi MCP and follow the same license as the project.

---

**Last Updated:** 2026-01-28  
**Status:** ✅ Current with Implementation  
**Version:** 1.0.0
