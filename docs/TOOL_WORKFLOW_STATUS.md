# Tool Workflow Status & Implementation Plan

**Generated:** 2026-01-23  
**Scope:** Complete end-to-end tool lifecycle (create → publish → load → search)

---

## Current Implementation Status

### ✅ Fully Implemented

| Component | Status | Notes |
|-----------|--------|-------|
| **ToolRegistry API** | ✅ Complete | All CRUD operations implemented |
| **Tool Search** | ✅ Complete | Both registry and local search working |
| **Tool Load** | ✅ Complete | Registry → Project/User copy working |
| **Tool Run** | ✅ Complete | PrimitiveExecutor with validation |
| **Tool Delete** | ✅ Complete | Registry API has delete method |
| **Vector Search** | ✅ Complete | Hybrid search (vector + keyword) working |
| **Auto-embedding** | ✅ Complete | ValidationManager.validate_and_embed() integrated |

### ⚠️ Partially Implemented

| Component | Status | What's Missing |
|-----------|--------|----------------|
| **Tool Create** | ⚠️ Stubbed | Handler method returns "not yet implemented" |
| **Tool Update** | ⚠️ Stubbed | Handler method returns "not yet implemented" |
| **Tool Publish** | ⚠️ Stubbed | Handler method returns "not yet implemented" |

### 📊 Code Locations

**Tool Handler:**
- File: `kiwi_mcp/handlers/tool/handler.py`
- Stubbed methods:
  - `_create_tool()` (line 514-518)
  - `_update_tool()` (line 520-522)
  - `_publish_tool()` (line 506-508)

**Tool Registry:**
- File: `kiwi_mcp/api/tool_registry.py`
- ✅ All methods implemented:
  - `search()` - Working
  - `get()` - Working
  - `list()` - Working
  - `publish()` - Working (line 248-366)
  - `delete()` - Working (line 368-420)

**Search Tool:**
- File: `kiwi_mcp/tools/search.py`
- ✅ Vector + keyword search working
- ✅ RAG integration complete

---

## What Works Right Now

### 1. ✅ Search for Tools (Local + Registry)

```python
# Works via MCP
search(
    item_type="tool",
    query="email processing",
    source="all",  # local + registry
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Returns:** List of matching tools with scores, descriptions, sources

### 2. ✅ Load Tool from Registry

```python
# Works via MCP
load(
    item_type="tool",
    item_id="enrich_emails",
    source="registry",
    destination="project",  # or "user"
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Result:** Tool downloaded from registry to `.ai/tools/` or `~/.ai/tools/`

### 3. ✅ Run Tool

```python
# Works via MCP
execute(
    item_type="tool",
    action="run",
    item_id="test_script",
    parameters={"arg1": "value"},
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Result:** Tool executed with validation, embedding, and result returned

---

## What Doesn't Work Yet

### 1. ✅ Create New Tool

**Note:** The file must exist first. Use `create_script` directive or create the file manually, then use `create` action to validate and sign.

```python
# Step 1: Create the file (via create_script directive or manually)
# File should be at: .ai/scripts/{category}/{tool_name}.py

# Step 2: Validate and sign the file
execute(
    item_type="tool",
    action="create",
    item_id="my_new_tool",
    parameters={
        "location": "project",
        "category": "utility"
    },
    project_path="/home/leo/projects/kiwi-mcp"
)

# API tool (no files - handled differently)
execute(
    item_type="tool",
    action="create",
    item_id="weather_api",
    parameters={
        "tool_type": "api",  # ← Different type!
        "executor": "http_client",
        "manifest": {
            "config": {
                "method": "GET",
                "url_template": "https://api.weather.com/forecast?lat={lat}&lon={lon}"
            },
            "parameters": [
                {"name": "lat", "type": "number", "required": True},
                {"name": "lon", "type": "number", "required": True}
            ]
        }
    },
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:** Create tool structure based on `tool_type`:
- **script**: Directory with files → `.ai/tools/utility/my_new_tool/`
- **api**: Single YAML manifest → `.ai/tools/weather_api.yaml`
- **mcp_tool**: Single YAML manifest → `.ai/tools/tool_name.yaml`

### 2. ❌ Update Existing Tool

```python
# Returns "not yet implemented"
execute(
    item_type="tool",
    action="update",
    item_id="my_tool",
    parameters={
        "content": "#!/usr/bin/env python3\nprint('updated')",
        "description": "Updated description"
    },
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:** Update tool file, re-validate, re-embed

### 3. ❌ Publish Tool to Registry

```python
# Returns "not yet implemented"
execute(
    item_type="tool",
    action="publish",
    item_id="my_tool",
    parameters={"version": "1.0.0"},
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:** Upload tool to registry with version tracking

---

## 🚨 Critical Design Issue: Validation Architecture

**See:** [TOOL_VALIDATION_DESIGN.md](./TOOL_VALIDATION_DESIGN.md)

### Current Problem

The existing `ToolValidator` assumes all tools are Python/Bash scripts:

```python
# validators.py lines 270-277
expected_extensions = {".py", ".sh", ".yaml", ".yml"}
if actual_extension not in expected_extensions:
    issues.append("Unsupported file extension...")
```

**This is wrong** because tools are dynamic:
- ✅ **Script tools:** Have files (`.py`, `.sh`)
- ❌ **API tools:** NO files (pure manifest)
- ❌ **MCP tools:** NO files (references to MCP servers)
- ❌ **MCP servers:** NO files (connection config)

### Solution: Manifest-Driven Validation

Tools are defined by their **manifest**, not their file structure:

```yaml
# Every tool has a manifest (tool.yaml or embedded)
tool_id: my_tool
tool_type: script | api | mcp_tool | mcp_server | runtime
version: "1.0.0"
executor: another_tool_id
config:
  # Tool-type-specific configuration
parameters:
  # Tool parameters
```

**Validation must be type-specific:**
- `script` → Check files exist, validate syntax
- `api` → Check HTTP config, NO files
- `mcp_tool` → Check mcp_tool_name, NO files
- `mcp_server` → Check transport config

### Required Changes Before Implementation

1. **Refactor `ToolValidator`**
   - Remove file extension checks
   - Add tool_type dispatching
   - Create type-specific validators

2. **Update `ToolHandler._create_tool()`**
   - Accept `tool_type` parameter
   - Create different structures per type
   - Use correct validator

---

## Implementation Plan

### Phase 0: Fix Validation Architecture ⚠️ MUST DO FIRST

**Goal:** Make validation manifest-driven and type-aware

1. Refactor `ToolValidator` in `validators.py`
2. Add type-specific validators (ScriptToolValidator, APIToolValidator, etc.)
3. Update validation to check manifest, not file extensions
4. Test validation for each tool type

**This is blocking for Phase 1!**

### Phase 1: Tool Create ✅ Can Start After Phase 0

**Goal:** Implement `_create_tool()` in ToolHandler

**Reference Implementation:** `KnowledgeHandler._create_knowledge()` (lines 575-702)

**Steps:**

1. **File Creation** (similar to knowledge)
   - Determine save location (project vs user)
   - File must exist first (created via `create_script` directive or manually)
   - Search for existing file in project/user scripts directories

2. **Validation & Embedding**
   - Read existing file
   - Parse script metadata
   - Call `ValidationManager.validate_and_embed()`
   - Return error if validation fails (file left as-is)

3. **Signature Generation**
   - Compute content hash
   - Generate timestamp
   - Add signature to file using MetadataManager

**Code Structure:**

```python
async def _create_tool(
    self, tool_name: str, content: Optional[str], location: str, category: Optional[str]
) -> Dict[str, Any]:
    """Validate and register an existing tool file."""
    # 1. Validate location
    if location not in ("project", "user"):
        return {"error": f"Invalid location: {location}"}
    
    # 2. Find existing file
    if location == "project":
        search_base = self.project_path / ".ai" / "scripts"
    else:
        search_base = get_user_space() / "scripts"
    
    file_path = None
    if search_base.exists():
        for candidate in Path(search_base).rglob(f"{tool_name}.py"):
            if candidate.stem == tool_name:
                file_path = candidate
                break
    
    if not file_path or not file_path.exists():
        return {
            "error": f"Tool file not found: {tool_name}",
            "hint": f"Create the file first at .ai/scripts/{category or 'utility'}/{tool_name}.py"
        }
    
    # 3. Read and validate
    file_content = file_path.read_text()
    tool_meta = parse_script_metadata(file_path)
    validation_result = await ValidationManager.validate_and_embed(
        "tool", file_path, tool_meta,
        vector_store=self._vector_store,
        item_id=tool_meta.get("name")
    )
    if not validation_result["valid"]:
        return {
            "error": "Tool validation failed",
            "details": validation_result["issues"],
            "solution": "Fix validation issues and re-run create action"
        }
    
    # 4. Sign the validated content
    signed_content = MetadataManager.sign_content("tool", file_content)
    file_path.write_text(signed_content)
    
    return {
        "status": "created",
        "tool_id": tool_name,
        "path": str(file_path),
        "location": location,
        "category": category,
        "signature": {"hash": content_hash, "timestamp": timestamp}
    }
```

### Phase 2: Tool Update

**Goal:** Implement `_update_tool()` in ToolHandler

**Reference Implementation:** `KnowledgeHandler._update_knowledge()` (lines 704-807)

**Steps:**

1. Find existing tool file
2. Parse current metadata
3. Apply updates
4. Re-validate and re-embed
5. Update signature

**Similar to create but:**
- Must find existing file first
- Preserve existing metadata if not updated
- Verify signature before updating

### Phase 3: Tool Publish

**Goal:** Implement `_publish_tool()` in ToolHandler

**Reference Implementation:** `KnowledgeHandler._publish_knowledge()` (lines 853-962)

**Steps:**

1. Find local tool file
2. **ENFORCE hash validation** (critical!)
3. Parse tool metadata
4. Extract tool manifest
5. Call `ToolRegistry.publish()` (already implemented!)
6. Return publish result

**Critical Security:**
```python
# ALWAYS verify signature before publishing
signature_status = MetadataManager.verify_signature("tool", file_content)
if signature_status.get("status") in ["modified", "invalid"]:
    return {"error": "Cannot publish modified/invalid tool"}
```

---

## Testing Plan

### Test 1: Create Tool

```python
# Create a simple Python tool
result = await execute(
    item_type="tool",
    action="create",
    item_id="test_hello",
    parameters={
        "name": "test_hello",
        "description": "A simple greeting tool",
        "content": '''#!/usr/bin/env python3
"""Test greeting tool."""
import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"Hello, {name}!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
''',
        "location": "project",
        "category": "test",
        "tags": ["test", "demo"]
    },
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:**
- ✅ File created at `.ai/tools/test/test_hello.py`
- ✅ Validation passed
- ✅ Vector embedding created
- ✅ Signature added to file

**Verify:**
```bash
# Check file exists
ls -la .ai/tools/test/test_hello.py

# Check embedding in Supabase
SELECT * FROM item_embeddings WHERE item_id = 'test_hello' AND item_type = 'tool';
```

### Test 2: Publish Tool

```python
result = await execute(
    item_type="tool",
    action="publish",
    item_id="test_hello",
    parameters={"version": "1.0.0"},
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:**
- ✅ Tool uploaded to registry
- ✅ Version `1.0.0` created in `tool_versions` table
- ✅ Content stored in `tool_version_files` table

**Verify:**
```sql
-- Check tool metadata
SELECT * FROM tools WHERE tool_id = 'test_hello';

-- Check version
SELECT * FROM tool_versions WHERE tool_id = (
    SELECT id FROM tools WHERE tool_id = 'test_hello'
);

-- Check files
SELECT * FROM tool_version_files WHERE tool_version_id = (
    SELECT id FROM tool_versions WHERE tool_id = (
        SELECT id FROM tools WHERE tool_id = 'test_hello'
    ) AND version = '1.0.0'
);
```

### Test 3: Load from Registry to Userspace

```python
result = await load(
    item_type="tool",
    item_id="test_hello",
    source="registry",
    destination="user",
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:**
- ✅ Tool downloaded to `~/.ai/tools/test/test_hello.py`
- ✅ Content matches published version

**Verify:**
```bash
# Check file exists in userspace
ls -la ~/.ai/tools/test/test_hello.py

# Compare with project version
diff .ai/tools/test/test_hello.py ~/.ai/tools/test/test_hello.py
```

### Test 4: Search for Tool (Vector + Keyword)

```python
result = await search(
    item_type="tool",
    query="greeting hello world",
    source="all",
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:**
- ✅ Returns `test_hello` tool
- ✅ High relevance score (semantic match)
- ✅ Shows both local and registry versions

**Verify:**
```python
assert len(result["items"]) > 0
assert any(item["id"] == "test_hello" for item in result["items"])
assert result["search_type"] in ["vector_hybrid", "keyword"]
```

### Test 5: Update Tool

```python
result = await execute(
    item_type="tool",
    action="update",
    item_id="test_hello",
    parameters={
        "content": '''#!/usr/bin/env python3
"""Test greeting tool - UPDATED."""
import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"Hello, {name}! (updated)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
''',
        "description": "Updated greeting tool"
    },
    project_path="/home/leo/projects/kiwi-mcp"
)
```

**Expected:**
- ✅ File updated with new content
- ✅ Re-validated
- ✅ New signature generated
- ✅ Re-embedded (new vector)

**Verify:**
```bash
# Check file content
cat .ai/tools/test/test_hello.py | grep "updated"

# Check embedding updated
SELECT updated_at FROM item_embeddings 
WHERE item_id = 'test_hello' AND item_type = 'tool'
ORDER BY updated_at DESC LIMIT 1;
```

---

## Comparison with KnowledgeHandler

The ToolHandler should mirror KnowledgeHandler patterns:

| Feature | KnowledgeHandler | ToolHandler (Target) |
|---------|------------------|----------------------|
| Create | ✅ Lines 575-702 | ⚠️ To implement |
| Update | ✅ Lines 704-807 | ⚠️ To implement |
| Publish | ✅ Lines 853-962 | ⚠️ To implement |
| Delete | ✅ Lines 808-851 | ✅ Already works |
| Search | ✅ Working | ✅ Working |
| Load | ✅ Working | ✅ Working |
| Run | ✅ Working | ✅ Working |
| Validation | ✅ ValidationManager.validate_and_embed() | ✅ Same |
| Embedding | ✅ Auto-embed on create/update | ✅ Same |
| Signature | ✅ MetadataManager | ✅ Same |

---

## Key Differences: Tool vs Knowledge

### File Format

**Knowledge:**
- Markdown with YAML frontmatter
- Signature in frontmatter (`validated_at`, `content_hash`)

**Tool:**
- Python script (`.py` file)
- Signature in docstring metadata block at top

### Signature Format

**Knowledge:**
```yaml
---
zettel_id: my-note
title: My Note
validated_at: 2026-01-23T10:30:00Z
content_hash: abc123...
---
```

**Tool:**
```python
"""
Tool: my_tool
Hash: abc123...
Validated: 2026-01-23T10:30:00Z
"""
```

### Validation

**Both use:** `ValidationManager.validate_and_embed()`

**Knowledge validates:**
- YAML frontmatter format
- Required fields (zettel_id, title, content)
- Filename matches zettel_id

**Tool validates:**
- Python syntax (AST parse)
- Has shebang or main function
- Docstring present
- No syntax errors

---

## Implementation Priority

1. **Phase 1: Create** (Highest priority - enables full workflow)
2. **Phase 2: Publish** (High priority - enables registry sync)
3. **Phase 3: Update** (Medium priority - can edit files manually for now)

**Estimated effort:**
- Create: ~1-2 hours (straight adaptation from KnowledgeHandler)
- Publish: ~30 minutes (mostly signature checking)
- Update: ~1 hour (similar to create)

---

## Next Steps

1. ✅ Implement `_create_tool()` using knowledge handler as template
2. ✅ Test create flow end-to-end
3. ✅ Implement `_publish_tool()` with signature verification
4. ✅ Test full cycle: create → publish → load to userspace → search
5. ✅ Implement `_update_tool()` for completeness
6. ✅ Document successful workflow

---

## Success Criteria

The tool workflow is complete when:

- ✅ Can create a new Python tool via MCP
- ✅ Tool is automatically validated and embedded
- ✅ Can publish tool to registry with version
- ✅ Can load published tool to userspace
- ✅ Can search for tool using semantic search
- ✅ Can run tool with validation
- ✅ Can update tool and re-embed
- ✅ All operations work identically to knowledge/directive patterns

---

## Related Documentation

- [UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md](./UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md) - Overall plan
- [PHASE_6_STATUS_REPORT.md](./PHASE_6_STATUS_REPORT.md) - Current phase
- [RAG_INTEGRATION_COMPLETE.md](./RAG_INTEGRATION_COMPLETE.md) - RAG setup
- [DATABASE_SCHEMA_ALIGNMENT.md](./DATABASE_SCHEMA_ALIGNMENT.md) - Database structure
