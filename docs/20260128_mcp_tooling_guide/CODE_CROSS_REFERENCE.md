# Code Cross-Reference

**How to Navigate Between Documentation and Implementation**

---

## Document → Code Mapping

### README.md

| Section | Relevant Code Files |
|---------|-------------------|
| Tool Structure | `.ai/tools/utility/hello_world.py` (example) |
| Tool Types | `kiwi_mcp/schemas.py` (metadata extraction) |
| Creating Tools | `.ai/tools/` (all example tools) |
| Executor Chain | `kiwi_mcp/primitives/executor.py` (chain building) |
| Signature Validation | `kiwi_mcp/utils/validators.py` (ValidationManager) |
| Search & Discovery | `kiwi_mcp/handlers/tool/handler.py` (search method) |
| Execution Flow | `kiwi_mcp/handlers/tool/handler.py` (execute method) |
| Metadata Extraction | `kiwi_mcp/schemas.py` (extract_tool_metadata) |

### QUICK_START.md

| Section | Code Reference |
|---------|----------------|
| Create a Tool File | `.ai/tools/utility/hello_world.py` |
| Sign the Tool | `kiwi_mcp/utils/validators.py` |
| Run the Tool | `kiwi_mcp/tools/execute.py` |
| Common Patterns | `.ai/tools/utility/` (all tools) |

### TOOL_API_REFERENCE.md

| Tool | Code File |
|------|-----------|
| search | `kiwi_mcp/tools/search.py` + `kiwi_mcp/handlers/tool/handler.py` |
| load | `kiwi_mcp/tools/load.py` + `kiwi_mcp/handlers/tool/handler.py` |
| execute | `kiwi_mcp/tools/execute.py` + `kiwi_mcp/handlers/tool/handler.py` |
| help | `kiwi_mcp/tools/help.py` |

### IMPLEMENTATION_NOTES.md

| Topic | Code File |
|-------|-----------|
| Architecture | `kiwi_mcp/server.py` (KiwiMCP class) |
| ToolHandler | `kiwi_mcp/handlers/tool/handler.py` |
| Metadata Extraction | `kiwi_mcp/schemas.py` |
| Executor Chain | `kiwi_mcp/primitives/executor.py` |
| Signature Validation | `kiwi_mcp/utils/validators.py` |
| Tool Resolution | `kiwi_mcp/utils/resolvers.py` |
| Output Management | `kiwi_mcp/utils/output_manager.py` |

---

## Code → Document Mapping

### MCP Server Entry

```
kiwi_mcp/server.py
└─ See: README.md "Overview"
    See: IMPLEMENTATION_NOTES.md "Architecture Overview"
```

### The 4 MCP Tools

```
kiwi_mcp/tools/search.py
└─ See: TOOL_API_REFERENCE.md "search"
    See: IMPLEMENTATION_NOTES.md "1. Search (ToolHandler.search)"

kiwi_mcp/tools/load.py
└─ See: TOOL_API_REFERENCE.md "load"
    See: IMPLEMENTATION_NOTES.md "2. Load (ToolHandler.load)"

kiwi_mcp/tools/execute.py
└─ See: TOOL_API_REFERENCE.md "execute"
    See: IMPLEMENTATION_NOTES.md "3. Execute: Run & Sign"

kiwi_mcp/tools/help.py
└─ See: TOOL_API_REFERENCE.md "help"
```

### Type Handlers

```
kiwi_mcp/handlers/tool/handler.py
├─ ToolHandler.search()
│  └─ See: README.md "Search and Discovery"
│      See: TOOL_API_REFERENCE.md "search"
│
├─ ToolHandler.load()
│  └─ See: TOOL_API_REFERENCE.md "load"
│
├─ ToolHandler.execute()
│  ├─ _run_tool()
│  │  └─ See: TOOL_API_REFERENCE.md "action: run"
│  │      See: IMPLEMENTATION_NOTES.md "Execution Flow"
│  │
│  └─ _sign_tool()
│     └─ See: TOOL_API_REFERENCE.md "action: sign"
│         See: README.md "Signature Validation"
│
└─ _search_local()
   └─ See: IMPLEMENTATION_NOTES.md "Tool Resolution"
```

### Metadata System

```
kiwi_mcp/schemas.py
├─ extract_tool_metadata()
│  └─ See: README.md "Metadata Extraction"
│      See: IMPLEMENTATION_NOTES.md "Tool Metadata Extraction"
│
└─ validate_tool_metadata()
   └─ See: IMPLEMENTATION_NOTES.md "Metadata Validation"
```

### Execution System

```
kiwi_mcp/primitives/executor.py (PrimitiveExecutor)
├─ build_chain()
│  └─ See: README.md "Executor Chain"
│      See: IMPLEMENTATION_NOTES.md "PrimitiveExecutor"
│
└─ execute()
   └─ See: TOOL_API_REFERENCE.md "Parameter Passing"
       See: IMPLEMENTATION_NOTES.md "Execution Flow"
```

### Utilities

```
kiwi_mcp/utils/
├─ resolvers.py (ToolResolver)
│  └─ See: IMPLEMENTATION_NOTES.md "Tool Resolution"
│
├─ validators.py (ValidationManager)
│  └─ See: README.md "Signature Validation"
│      See: IMPLEMENTATION_NOTES.md "Signature Validation"
│
└─ output_manager.py (OutputManager)
   └─ See: IMPLEMENTATION_NOTES.md "Output Management"
```

### Example Tools

```
.ai/tools/
├─ primitives/subprocess.py
│  └─ See: README.md "Example 3: Hard-Coded Primitive"
│
├─ primitives/http_client.py
│  └─ See: README.md "Tool Types: Primitives"
│
├─ utility/hello_world.py
│  └─ See: QUICK_START.md "Example 1: Create a Tool File"
│
└─ utility/http_test.py
   └─ See: README.md "Examples"
```

---

## Key Code Patterns

### Pattern 1: Extracting Tool Metadata

**Where:** `kiwi_mcp/schemas.py`  
**See Documentation:** README.md "Metadata Extraction"

```python
from kiwi_mcp.schemas import extract_tool_metadata

meta = extract_tool_metadata(file_path, project_path)
# Returns: {
#   "name": "my_tool",
#   "description": "...",
#   "version": "1.0.0",
#   "tool_type": "python",
#   "executor_id": "python_runtime",
#   "category": "custom"
# }
```

### Pattern 2: Building Executor Chain

**Where:** `kiwi_mcp/primitives/executor.py`  
**See Documentation:** README.md "Executor Chain", IMPLEMENTATION_NOTES.md "PrimitiveExecutor"

```python
executor = PrimitiveExecutor(project_path)
chain = executor.build_chain("my_tool")
# Returns: [my_tool, python_runtime, subprocess]
```

### Pattern 3: Resolving Tools

**Where:** `kiwi_mcp/utils/resolvers.py`  
**See Documentation:** IMPLEMENTATION_NOTES.md "Tool Resolution"

```python
resolver = ToolResolver(project_path)
file_path = resolver.resolve("my_tool")
# Returns: Path or None
```

### Pattern 4: Validating Signatures

**Where:** `kiwi_mcp/utils/validators.py`  
**See Documentation:** README.md "Signature Validation", IMPLEMENTATION_NOTES.md "Signature Validation"

```python
is_valid = ValidationManager.validate_hash(content, stored_hash)
```

### Pattern 5: Searching Tools

**Where:** `kiwi_mcp/handlers/tool/handler.py` (ToolHandler.search)  
**See Documentation:** TOOL_API_REFERENCE.md "search"

```python
handler = ToolHandler(project_path)
results = await handler.search("query", source="local", limit=10)
```

---

## Understanding The Flow

### Complete Search → Run Flow

```
1. User calls execute tool with:
   { item_type: "tool", action: "run", item_id: "my_tool", ... }
   └─ See: TOOL_API_REFERENCE.md "execute: run"

2. ExecuteTool dispatches to ToolHandler
   └─ kiwi_mcp/tools/execute.py
   └─ kiwi_mcp/handlers/tool/handler.py

3. ToolHandler.execute() calls _run_tool()
   └─ IMPLEMENTATION_NOTES.md "3. Execute: Run"
   └─ Resolves tool: resolver.resolve("my_tool")
   └─ See: IMPLEMENTATION_NOTES.md "Tool Resolution"

4. Extract metadata
   └─ extract_tool_metadata(file_path, project_path)
   └─ See: README.md "Metadata Extraction"

5. Validate signature
   └─ ValidationManager.validate_hash(...)
   └─ See: README.md "Signature Validation"

6. Build executor chain
   └─ PrimitiveExecutor.build_chain("my_tool")
   └─ See: README.md "Executor Chain"
   └─ IMPLEMENTATION_NOTES.md "PrimitiveExecutor"

7. Execute via primitive
   └─ executor.execute(tool_id, parameters)
   └─ See: IMPLEMENTATION_NOTES.md "Execution Flow"

8. Save output
   └─ OutputManager.save(tool_name, result)
   └─ See: IMPLEMENTATION_NOTES.md "Output Management"

9. Return result
   └─ See: TOOL_API_REFERENCE.md "Returns"
```

### File Reading Flow

```
1. User calls load tool with item_id="my_tool"
   └─ See: TOOL_API_REFERENCE.md "load"

2. LoadTool dispatches to ToolHandler.load()
   └─ kiwi_mcp/tools/load.py
   └─ kiwi_mcp/handlers/tool/handler.py

3. Resolve tool location
   └─ resolver.resolve("my_tool")
   └─ See: IMPLEMENTATION_NOTES.md "Tool Resolution"

4. Extract metadata
   └─ extract_tool_metadata(file_path)
   └─ See: README.md "Metadata Extraction"

5. Read file content
   └─ file_path.read_text()

6. Return file + metadata
   └─ See: TOOL_API_REFERENCE.md "Returns (Read-Only)"
```

---

## Finding Specific Answers

### I want to know how tools are structured
```
→ README.md "How Tools Are Actually Structured"
→ QUICK_START.md "Create a Tool File"
→ Look at: .ai/tools/utility/hello_world.py
```

### I want to understand executor chains
```
→ README.md "Executor Chain"
→ IMPLEMENTATION_NOTES.md "PrimitiveExecutor"
→ Code: kiwi_mcp/primitives/executor.py
```

### I want to add a new feature
```
→ IMPLEMENTATION_NOTES.md "Architecture Overview"
→ Find relevant code file (see above)
→ Trace through execution flow
→ Update docs when done
```

### I want to fix a bug
```
→ IMPLEMENTATION_NOTES.md "Limitations & TODOs"
→ Check the specific code file
→ Cross-reference with relevant doc section
→ Test against examples in README.md
```

### I want to understand the API
```
→ TOOL_API_REFERENCE.md (complete reference)
→ See "Examples" sections
→ Try with example from QUICK_START.md
```

---

## Documentation Maintenance

When updating code, also update:

| Code Change | Documentation Change |
|-------------|----------------------|
| Add tool type | README.md "Tool Types" + IMPLEMENTATION_NOTES.md |
| Add MCP tool | TOOL_API_REFERENCE.md "examples" |
| Change executor logic | IMPLEMENTATION_NOTES.md "PrimitiveExecutor" |
| Add validation rule | IMPLEMENTATION_NOTES.md "Metadata Validation" |
| Add error type | TOOL_API_REFERENCE.md "Error Responses" |
| Change file format | README.md "Tool Structure" + examples |

---

## Code File Glossary

| File | Purpose | See Docs |
|------|---------|----------|
| `kiwi_mcp/server.py` | MCP server entry | Architecture Overview |
| `kiwi_mcp/tools/search.py` | Search tool | TOOL_API_REFERENCE.md |
| `kiwi_mcp/tools/load.py` | Load tool | TOOL_API_REFERENCE.md |
| `kiwi_mcp/tools/execute.py` | Execute tool | TOOL_API_REFERENCE.md |
| `kiwi_mcp/tools/help.py` | Help tool | TOOL_API_REFERENCE.md |
| `kiwi_mcp/handlers/tool/handler.py` | Main logic | IMPLEMENTATION_NOTES.md |
| `kiwi_mcp/primitives/executor.py` | Chain execution | README.md + IMPLEMENTATION_NOTES.md |
| `kiwi_mcp/schemas.py` | Metadata extraction | README.md |
| `kiwi_mcp/utils/resolvers.py` | Tool finding | IMPLEMENTATION_NOTES.md |
| `kiwi_mcp/utils/validators.py` | Validation | README.md |
| `kiwi_mcp/utils/output_manager.py` | Output saving | IMPLEMENTATION_NOTES.md |
| `.ai/tools/` | Example tools | QUICK_START.md + README.md |

---

## Quick Lookup Table

| Question | Document | Section |
|----------|----------|---------|
| How do I create a tool? | QUICK_START.md | "5-Minute Setup" |
| What parameters does search accept? | TOOL_API_REFERENCE.md | "search: Parameters" |
| How is the executor chain built? | IMPLEMENTATION_NOTES.md | "PrimitiveExecutor" |
| What's the file format? | README.md | "Tool Structure" |
| How are signatures validated? | README.md | "Signature Validation" |
| Where are tools stored? | README.md | "Tool Locations" |
| What's the execution flow? | IMPLEMENTATION_NOTES.md | "Execution Flow" |
| How do I troubleshoot? | README.md | "Troubleshooting" |
| What are the limitations? | README.md | "Current Limitations" |
| What's planned next? | README.md | "Future Roadmap" |

---

Last updated: 2026-01-28
