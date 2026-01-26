# Supabase Decoupling & Registry Tool Implementation Plan

**Date:** 2026-01-26  
**Status:** Planning  
**Goal:** Remove Supabase dependency from core kernel and implement registry operations as a core tool (stored in `.ai/tools/core/`, executed via execute tool) using HTTP primitives

---

## Executive Summary

This plan outlines the complete decoupling of Supabase from the Kiwi MCP core kernel. The registry functionality will be moved to a **core tool** (stored in `.ai/tools/core/registry.py`) that uses `HttpClientPrimitive` to communicate with Supabase via REST API.

**Key Distinction:**

- **Meta tools** - The 4 hardcoded MCP tools (search, load, execute, help) in `kiwi_mcp/server.py`
- **Core tools** - Important tools stored in `.ai/tools/core/` (like registry)
- **Regular tools** - User/project tools stored in `.ai/tools/`

The registry tool is a **core tool** (not a meta tool) that gets executed via:

```python
execute(item_type="tool", action="run", item_id="registry", parameters={...})
```

The tool uses the `http_client` primitive via the executor chain: `registry → http_client`.

This enables:

- **Smaller kernel size** - No Supabase Python SDK dependency
- **Full offline support** - Core MCP works without network connectivity
- **Better modularity** - Registry as optional, swappable component
- **Private + public storage** - Users can save items privately or share publicly
- **Dual search capabilities** - Both RAG (vector) and keyword search

---

## Current Architecture

### Supabase Integration Points

**Core API Classes (Direct Supabase Dependency):**

- `kiwi_mcp/api/base.py` - `BaseRegistry` with `from supabase import create_client`
- `kiwi_mcp/api/directive_registry.py` - Inherits from `BaseRegistry`
- `kiwi_mcp/api/tool_registry.py` - Inherits from `BaseRegistry`
- `kiwi_mcp/api/knowledge_registry.py` - Inherits from `BaseRegistry`

**Vector Storage:**

- `kiwi_mcp/storage/vector/registry.py` - `RegistryVectorStore` with Supabase import

**Handler Integration:**

- `DirectiveHandler.__init__()` → `self.registry = DirectiveRegistry()`
- `ToolHandler.__init__()` → `self.registry = ToolRegistry()`
- `KnowledgeHandler.__init__()` → `self.registry = KnowledgeRegistry()`

**Registry Operations Currently Used:**

- `registry.search()` - Used when `source="registry"` or `source="all"` in search
- `registry.get()` - Used when `source="registry"` in load
- `registry.publish()` - Used in `execute(action="publish")`
- `registry.delete()` - Used in `execute(action="delete")`

**Dependencies:**

- `pyproject.toml` - `supabase>=2.0.0` as core dependency

---

## Target Architecture

### Core Kernel (No Supabase)

**4 Meta MCP Tools (unchanged - hardcoded in server):**

1. `search` - Local-only search (project + user space)
2. `load` - Local-only load (project ↔ user)
3. `execute` - Run, create, update, sign (no publish/delete)
4. `help` - Usage guidance

### Registry Tool Design

**Core tool (stored in `.ai/tools/core/`)** that provides all registry operations:

- Lives in `.ai/tools/core/registry.py` (core tools directory)
- Executed via: `execute(item_type="tool", action="run", item_id="registry", parameters={...})`
- Uses `HttpClientPrimitive` (via executor chain: `registry → http_client`)
- Makes HTTP requests to Supabase REST API
- No Supabase Python SDK dependency
- Supports private/public/unlisted visibility
- Dual search: RAG (vector) + keyword queries

**Tool Structure:**

- Tool location: `.ai/tools/core/registry.py` (or `.yaml` manifest)
- Executor: `http_client` (primitive)
- Parameters: Accepts registry action and parameters
- Returns: JSON response with results

---

## Registry Tool Operations

### Core Operations

| Action       | Purpose                         | Parameters                                                                                      |
| ------------ | ------------------------------- | ----------------------------------------------------------------------------------------------- |
| **upload**   | Upload item to registry         | `version`, `content`, `visibility` (public/private/unlisted), `category`, `description`, `tags` |
| **download** | Download from registry to local | `destination` (project/user), `version` (optional)                                              |
| **search**   | Search registry                 | `query`, `search_type` (rag/keyword/hybrid), `limit`, `filters`                                 |
| **publish**  | Make item public                | -                                                                                               |
| **private**  | Make item private               | -                                                                                               |
| **unlist**   | Make item unlisted              | -                                                                                               |
| **get**      | Get item details                | `version` (optional)                                                                            |
| **list**     | List items with filters         | `filters` (category, tags, visibility, author_id, is_official)                                  |
| **update**   | Update item metadata/content    | `metadata`, `content`                                                                           |
| **delete**   | Delete from registry            | `confirm` (true)                                                                                |
| **versions** | List all versions               | -                                                                                               |
| **stats**    | Get item statistics             | -                                                                                               |

### Search Types

**Note:** RAG/vector search is handled server-side by Supabase. The registry tool only makes HTTP requests - it does NOT need to generate embeddings or handle RAG logic.

1. **RAG Search** - Vector/semantic search using embeddings

   - Uses Supabase `search_embeddings` RPC function
   - Supabase handles embedding generation and vector search server-side
   - Registry tool just passes query and receives results

2. **Keyword Search** - Traditional text matching

   - Uses Supabase REST API with `ilike` filters
   - Searches name, description, content

3. **Hybrid Search** - Combines both (default)

   - Runs both RAG and keyword search
   - Merges and deduplicates results
   - All handled server-side by Supabase

---

## Cleanup Principles

**CRITICAL: Complete removal with zero backwards compatibility**

All removal must follow these principles:

1. **Complete Deletion**

   - Delete entire methods, not stub them
   - Delete entire code blocks, not comment them out
   - Delete entire files, don't leave empty stubs

2. **No Backwards Compatibility Code**

   - ❌ No `if action == "publish": return {"error": "use registry tool"}`
   - ❌ No `# DEPRECATED: removed in favor of registry tool`
   - ❌ No `# TODO: migrate to registry tool`
   - ❌ No stub methods that return errors
   - ❌ No migration helpers or compatibility layers

3. **No Comments About Removal**

   - ❌ No `# Removed: publish action - use registry tool instead`
   - ❌ No `# This was removed for Supabase decoupling`
   - ❌ No historical comments about what was removed
   - ✅ Code should read as if publish/delete never existed

4. **Clean Error Messages**

   - If action doesn't exist, return standard "unknown action" error
   - Don't mention that it was removed or migrated
   - Don't suggest using registry tool in error messages

5. **Clean Codebase**
   - Code should be minimal and clean
   - No legacy code paths
   - No conditional compilation or feature flags
   - No dead code

**Example of what NOT to do:**

```python
# ❌ BAD - Don't do this
if action == "publish":
    return {"error": "publish action removed, use registry tool instead"}

# ❌ BAD - Don't do this
# DEPRECATED: publish action removed in favor of registry tool
# def _publish_directive(self, ...):
#     pass

# ✅ GOOD - Just delete it completely
# (method doesn't exist at all)
```

---

## Implementation Plan

### Phase 1: Remove Supabase from Core (2-3 days)

#### 1.1 Delete Registry API Classes

**Files to delete:**

- `kiwi_mcp/api/base.py`
- `kiwi_mcp/api/directive_registry.py`
- `kiwi_mcp/api/tool_registry.py`
- `kiwi_mcp/api/knowledge_registry.py`

**Action:** Delete these files completely.

#### 1.2 Remove Registry from Vector Storage

**File:** `kiwi_mcp/storage/vector/registry.py`

**Options:**

- **Option A:** Delete file completely
- **Option B:** Keep as stub for future use

**Recommendation:** Delete (can recreate later if needed)

**File:** `kiwi_mcp/storage/vector/manager.py`

**Changes:**

- Remove `RegistryVectorStore` from `ThreeTierVectorManager`
- Update to only use `LocalVectorStore` (project + user)

#### 1.3 Update Handlers

**File:** `kiwi_mcp/handlers/directive/handler.py`

**Changes:**

1. Remove `self.registry = DirectiveRegistry()` from `__init__()` - **DELETE COMPLETELY, NO COMMENTS**
2. Remove registry search from `search()` method (lines ~302-317) - **DELETE CODE, NO STUBS**
3. Remove registry load from `load()` method - **DELETE CODE, NO STUBS**
4. Remove `_publish_directive()` method - **DELETE ENTIRE METHOD, NO BACKWARDS COMPAT**
5. Remove `_delete_directive()` method - **DELETE ENTIRE METHOD, NO BACKWARDS COMPAT**
6. Remove `publish` and `delete` from `execute()` method routing - **DELETE CASE STATEMENTS**
7. **NO DEPRECATED WARNINGS, NO MIGRATION MESSAGES, NO COMMENTS ABOUT REMOVAL**

**File:** `kiwi_mcp/handlers/tool/handler.py`

**Changes:**

1. Remove `self.registry = ToolRegistry()` from `__init__()` - **DELETE COMPLETELY, NO COMMENTS**
2. Remove `_search_registry()` method - **DELETE ENTIRE METHOD**
3. Remove registry load from `load()` method - **DELETE CODE, NO STUBS**
4. Remove `_publish_tool()` method - **DELETE ENTIRE METHOD, NO BACKWARDS COMPAT**
5. Remove `_delete_tool()` method - **DELETE ENTIRE METHOD, NO BACKWARDS COMPAT**
6. Remove `publish` and `delete` from `execute()` method routing - **DELETE CASE STATEMENTS**
7. **NO DEPRECATED WARNINGS, NO MIGRATION MESSAGES, NO COMMENTS ABOUT REMOVAL**

**File:** `kiwi_mcp/handlers/knowledge/handler.py`

**Changes:**

1. Remove `self.registry = KnowledgeRegistry()` from `__init__()` - **DELETE COMPLETELY, NO COMMENTS**
2. Remove registry search from `search()` method - **DELETE CODE, NO STUBS**
3. Remove registry load from `load()` method - **DELETE CODE, NO STUBS**
4. Remove `_publish_knowledge()` method - **DELETE ENTIRE METHOD, NO BACKWARDS COMPAT**
5. Remove `_delete_knowledge()` method - **DELETE ENTIRE METHOD, NO BACKWARDS COMPAT**
6. Remove `publish` and `delete` from `execute()` method routing - **DELETE CASE STATEMENTS**
7. **NO DEPRECATED WARNINGS, NO MIGRATION MESSAGES, NO COMMENTS ABOUT REMOVAL**

**Important:** All removal must be clean with:

- ❌ No `# TODO: removed for registry tool` comments
- ❌ No `# DEPRECATED: use registry tool instead` warnings
- ❌ No stub methods that return errors
- ❌ No backwards compatibility code
- ❌ No migration helpers
- ✅ Complete deletion of code
- ✅ Clean, minimal codebase

#### 1.4 Update Search Tool

**File:** `kiwi_mcp/tools/search.py`

**Changes:**

1. Remove `source="registry"` and `source="all"` options
2. Update schema: Change `source` enum to `["local"]` or remove parameter entirely
3. Remove `RegistryVectorStore` from vector search setup
4. Update `ThreeTierVectorManager` initialization to exclude registry store
5. Update `_vector_search()` to only search project + user stores

**Before:**

```python
source: {
    "type": "string",
    "enum": ["local", "registry", "all"],
    "default": "local"
}
```

**After:**

```python
# Remove source parameter entirely, or:
source: {
    "type": "string",
    "enum": ["local"],
    "default": "local"
}
```

#### 1.5 Update Load Tool

**File:** `kiwi_mcp/tools/load.py`

**Changes:**

1. Remove `source="registry"` option
2. Update schema: Change `source` enum to `["project", "user"]`

**Before:**

```python
source: {
    "type": "string",
    "enum": ["project", "user", "registry"]
}
```

**After:**

```python
source: {
    "type": "string",
    "enum": ["project", "user"]
}
```

#### 1.6 Update Execute Tool

**File:** `kiwi_mcp/tools/execute.py`

**Changes:**

1. Remove `"publish"` and `"delete"` from action enum - **DELETE FROM ENUM, NO COMMENTS**
2. Update description to only mention `run`, `create`, `update`, `sign` - **REMOVE ALL MENTIONS OF PUBLISH/DELETE**
3. Remove any error handling for publish/delete actions - **DELETE ERROR MESSAGES**
4. **NO DEPRECATED WARNINGS, NO MIGRATION MESSAGES, NO COMMENTS**

**Before:**

```python
action: {
    "type": "string",
    "enum": ["run", "publish", "delete", "create", "update", "sign"]
}
description="""Execute operations on directives, tools, or knowledge.

All three types support the same 4 actions for consistency:
- run: Execute/load content
- publish: Upload to registry with version
- delete: Remove from local/registry
- create: Validate and sign existing file
- update: Validate and update existing item
- sign: Validate and sign file
"""
```

**After:**

```python
action: {
    "type": "string",
    "enum": ["run", "create", "update", "sign"]
}
description="""Execute operations on directives, tools, or knowledge.

All three types support the same 4 actions for consistency:
- run: Execute/load content
- create: Validate and sign existing file
- update: Validate and update existing item
- sign: Validate and sign file

Note: For registry operations (upload, download, publish, delete), use the registry tool.
"""
```

**Important:**

- Remove all code paths that handle `action == "publish"` or `action == "delete"`
- Remove from supported_actions lists
- Remove from error messages
- **NO BACKWARDS COMPATIBILITY CODE OR COMMENTS**

#### 1.7 Remove Supabase Dependency

**File:** `pyproject.toml`

**Changes:**

- Remove `"supabase>=2.0.0"` from dependencies array

**Before:**

```toml
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "supabase>=2.0.0",  # REMOVE THIS
    ...
]
```

**After:**

```toml
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    ...
]
```

---

### Phase 2: Create Registry Tool (3-4 days)

#### 2.1 Create Registry Tool File

**New File:** `.ai/tools/core/registry.py` (core tools directory)

**Important:** This is a **core tool** (stored in `.ai/tools/core/`), not a meta tool (the 4 hardcoded MCP tools). It gets executed via the execute tool.

**Tool Structure:**

**Format:** Python file with tool metadata (required for validation)

```python
# .ai/tools/core/registry.py
# kiwi-mcp:validated:2026-01-26T00:00:00Z:hash...
"""Registry tool - manage items in remote Supabase registry via HTTP.

This tool uses the http_client primitive to communicate with Supabase REST API.
Executed via: execute(item_type="tool", action="run", item_id="registry", parameters={...})
"""

# Tool metadata (in frontmatter or __config__)
__tool_id__ = "registry"
__tool_type__ = "api"
__executor_id__ = "http_client"
__version__ = "1.0.0"
__description__ = "Manage items in remote Supabase registry (upload, download, search, publish, etc.)"

# Tool implementation
import os
import json
from typing import Dict, Any, Optional, List

def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute registry operation.

    Parameters:
        action: upload, download, search, publish, private, unlist, get, list, update, delete, versions, stats
        item_type: directive, tool, or knowledge
        item_id: Item identifier
        ... (other action-specific parameters)

    Returns:
        Dict with operation result
    """
    action = parameters.get("action")
    item_type = parameters.get("item_type")

    # Route to action handler
    if action == "upload":
        return _upload(parameters)
    elif action == "download":
        return _download(parameters)
    # ... etc

    # Action handlers use http_client primitive via executor chain
    # The tool executor will resolve: registry → http_client
    # And pass the HTTP config to http_client primitive
```

**Note:** Tool must be a Python file with metadata for validation. The executor chain (`registry → http_client`) is resolved automatically by the tool executor.

#### 2.2 Registry Tool Parameters

**Tool Parameters Schema:**

The registry tool accepts parameters that define the operation to perform:

```python
{
    "action": "upload" | "download" | "search" | "publish" | "private" | "unlist" | "get" | "list" | "update" | "delete" | "versions" | "stats",
    "item_type": "directive" | "tool" | "knowledge",
    "item_id": "string (optional for some actions)",
    # Action-specific parameters:
    "version": "string (for upload, download, get)",
    "content": "string (for upload, update)",
    "visibility": "public" | "private" | "unlisted" (for upload, publish, private, unlist)",
    "category": "string",
    "description": "string",
    "tags": ["string"],
    "query": "string (for search)",
    "search_type": "rag" | "keyword" | "hybrid" (for search)",
    "limit": "integer (for search, list)",
    "destination": "project" | "user" (for download)",
    "filters": {
        "category": "string",
        "tags": ["string"],
        "visibility": "string",
        "author_id": "string",
        "is_official": "boolean"
    },
    "metadata": "object (for update)",
    "confirm": "boolean (for delete)",
    "project_path": "string (for download destination='project')"
}
```

**Usage Example:**

```python
# Upload a directive
execute(
    item_type="tool",
    action="run",
    item_id="registry",
    parameters={
        "action": "upload",
        "item_type": "directive",
        "item_id": "my_directive",
        "version": "1.0.0",
        "content": "...",
        "visibility": "public"
    },
    project_path="/path/to/project"
)

# Search registry
execute(
    item_type="tool",
    action="run",
    item_id="registry",
    parameters={
        "action": "search",
        "item_type": "directive",
        "query": "authentication",
        "search_type": "hybrid",
        "limit": 10
    },
    project_path="/path/to/project"
)
```

#### 2.3 Data Flow Summary

**Upload Flow:**
```
Local file (.ai/directives/my_directive.md)
  ↓
Registry tool reads file content
  ↓
POST /rest/v1/directives (metadata)
  ↓
POST /rest/v1/directive_versions (content + version)
  ↓
Supabase creates embedding server-side (via trigger/RPC)
  ↓
Success response
```

**Download Flow:**
```
Registry tool receives download request
  ↓
GET /rest/v1/directives?name=eq.my_directive (metadata)
  ↓
GET /rest/v1/directive_versions?directive_id=eq.{id}&version=eq.1.0.0 (content)
  ↓
Registry tool writes to local (.ai/directives/my_directive.md)
  ↓
Success response
```

**Note:** All embedding operations happen server-side in Supabase. The registry tool only passes data through HTTP requests.

#### 2.4 Implement Action Handlers

**Key Implementation Details:**

1. **Upload Handler:**

   **Data Flow:** Local file → Registry tool → Supabase REST API
   
   **Implementation:**
   ```python
   # 1. Read local file
   file_path = handler.resolve(item_id)  # From .ai/ or ~/.ai/
   content = file_path.read_text()
   
   # 2. Validate and compute hash
   integrity_hash = compute_integrity_hash(content)
   
   # 3. POST main record
   POST /rest/v1/{table}
   Body: {
       "name": item_id,
       "category": category,
       "description": description,
       "visibility": visibility,
       ...
   }
   
   # 4. POST version record
   POST /rest/v1/{table}_versions
   Body: {
       "{table}_id": main_record_id,
       "version": version,
       "content": content,
       "content_hash": integrity_hash,
       ...
   }
   
   # 5. For tools: POST file records
   POST /rest/v1/tool_version_files
   Body: [{"path": "main.py", "content_text": "...", ...}, ...]
   
   # Note: Supabase creates embeddings server-side (via database triggers/RPC)
   ```

2. **Download Handler:**

   **Data Flow:** Supabase REST API → Registry tool → Local file
   
   **Implementation:**
   ```python
   # 1. GET main record
   GET /rest/v1/{table}?name=eq.{item_id}
   Response: {id, name, category, description, ...}
   
   # 2. GET version content
   GET /rest/v1/{table}_versions?{table}_id=eq.{id}&version=eq.{version}
   Response: {content, content_hash, version, ...}
   
   # 3. For tools: GET all files
   GET /rest/v1/tool_version_files?tool_version_id=eq.{version_id}
   Response: [{path, content_text, ...}, ...]
   
   # 4. Write to local storage
   handler.write(item_id, content, destination)  # To .ai/ or ~/.ai/
   ```

3. **Search Handler:**

   - **RAG Search:** POST to `/rest/v1/rpc/search_embeddings` (Supabase handles embeddings server-side)
   - **Keyword Search:** GET with `ilike` filters
   - **Hybrid:** Run both, merge results (all server-side)

4. **Visibility Handlers:**

   - PATCH `/rest/v1/{table}?id=eq.{id}` with `{"visibility": "public|private|unlisted"}`

5. **Get Handler:**

   - GET `/rest/v1/{table}?name=eq.{name}`
   - Include version information

6. **List Handler:**

   - GET with filter parameters
   - Support pagination

7. **Update Handler:**

   - PATCH `/rest/v1/{table}?id=eq.{id}`
   - Update version if content changed

8. **Delete Handler:**

   - DELETE `/rest/v1/{table}?id=eq.{id}`
   - Cascade delete versions

9. **Versions Handler:**

   - GET `/rest/v1/{table}_versions?{table}_id=eq.{id}`

10. **Stats Handler:**
    - GET item with statistics fields (download_count, quality_score, etc.)

#### 2.4 Supabase REST API Mapping

**Table Names:**

- `directive` → `directives` + `directive_versions`
- `tool` → `tools` + `tool_versions` + `tool_version_files`
- `knowledge` → `knowledge_entries` + `knowledge_versions`

**REST API Endpoints:**

| Operation         | Method | Endpoint                                         | Notes                       |
| ----------------- | ------ | ------------------------------------------------ | --------------------------- |
| Search (keyword)  | GET    | `/rest/v1/{table}?select=*&name=ilike.*{query}*` | Use ilike for text search   |
| Search (RAG)      | POST   | `/rest/v1/rpc/search_embeddings`                 | RPC function - pass `query_text`, Supabase generates embedding |
| Get               | GET    | `/rest/v1/{table}?name=eq.{name}`                | Get main record (metadata) |
| Get Version       | GET    | `/rest/v1/{table}_versions?{table}_id=eq.{id}`   | Get version content |
| Get Files         | GET    | `/rest/v1/tool_version_files?tool_version_id=eq.{id}` | Get all files for tool version |
| Upload            | POST   | `/rest/v1/{table}`                               | Create/update main record (metadata) |
| Upload Version    | POST   | `/rest/v1/{table}_versions`                      | Create version record (content) |
| Upload Files      | POST   | `/rest/v1/tool_version_files`                    | Create file records (for tools only) |
| Update            | PATCH  | `/rest/v1/{table}?id=eq.{id}`                    | Update metadata             |
| Update Visibility | PATCH  | `/rest/v1/{table}?id=eq.{id}`                    | `{"visibility": "public"}`  |
| Delete            | DELETE | `/rest/v1/{table}?id=eq.{id}`                    | Delete item                 |
| List              | GET    | `/rest/v1/{table}?select=*&{filters}`            | With filters                |
| Versions          | GET    | `/rest/v1/{table}_versions?{table}_id=eq.{id}`   | All versions                |

**Authentication Headers:**

```python
{
    "apikey": self.supabase_key,
    "Authorization": f"Bearer {self.supabase_key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"  # For POST/PATCH to return data
}
```

#### 2.5 RAG Search Implementation

**Important:** RAG search is handled entirely server-side by Supabase. The registry tool does NOT need to:
- Generate embeddings
- Handle vector operations
- Manage embedding services

**RAG Search Flow:**
1. Registry tool sends query text to Supabase RPC endpoint: `POST /rest/v1/rpc/search_embeddings`
2. Supabase RPC function receives `query_text` parameter
3. Supabase generates embedding for query (server-side)
4. Supabase performs vector search against `item_embeddings` table (server-side)
5. Supabase returns results with similarity scores
6. Registry tool passes through the results to caller

**Implementation:**
```python
# RAG search - Supabase handles everything server-side
config = {
    "method": "POST",
    "url": f"{self.supabase_url}/rest/v1/rpc/search_embeddings",
    "body": {
        "query_text": query,  # Just pass text, Supabase generates embedding
        "item_type": item_type,
        "match_count": limit
    }
}
result = await self.http_client.execute(config, {})
# Results already include similarity scores from Supabase
```

#### 2.6 Tool Location

**Registry Tool Location:**

The registry tool should be placed in the **core tools directory**:

- **Project space:** `.ai/tools/core/registry.py` (or `.ai/tools/core/registry.yaml`)
- **User space:** `~/.ai/tools/core/registry.py` (or `~/.ai/tools/core/registry.yaml`)

**Directory Structure:**

```
.ai/tools/
├── core/           # Core tools (like registry)
│   └── registry.py
├── llm/            # LLM tools
├── threads/        # Thread tools
└── ...             # Other tool categories
```

**No changes to `kiwi_mcp/server.py` needed** - the tool is discovered and executed via the normal tool resolution process when called via:

```python
execute(item_type="tool", action="run", item_id="registry", parameters={...})
```

The tool executor will:

1. Resolve tool location (checks `.ai/tools/core/` first, then user space)
2. Load tool manifest
3. Resolve executor chain: `registry → http_client`
4. Execute via `HttpClientPrimitive`

---

### Phase 3: Testing & Validation (1-2 days)

#### 3.1 Unit Tests

**New Test File:** `tests/tools/test_registry_tool.py` (or test via execute tool)

**Test Cases:**

- Tool can be discovered and loaded
- Tool executes via execute tool correctly
- All 12 actions work correctly
- HTTP requests are properly formatted
- Authentication headers are correct
- Error handling for missing Supabase config
- Error handling for network failures
- RAG vs keyword search
- Hybrid search merging
- Multi-file tool upload/download
- Visibility changes
- Tool executor chain resolution (registry → http_client)

#### 3.2 Integration Tests

**Update:** `tests/integration/test_registry_integration.py`

**Test Cases:**

- Upload → Download workflow
- Search → Get workflow
- Publish → Search (public) workflow
- Private → Public visibility change
- Version management

#### 3.3 Remove Supabase Mocks

**Files to update:**

- `tests/conftest.py` - Remove Supabase mock fixtures
- All test files that mock Supabase client

**Action:** Remove or update all Supabase-related test mocks

#### 3.4 Update Documentation

**Files to update:**

- `README.md` - Update tool list, remove Supabase from dependencies
- `docs/API.md` - Add registry tool documentation
- `docs/ARCHITECTURE.md` - Update architecture diagram

---

## Supabase REST API Reference

### Base URL

```
{SUPABASE_URL}/rest/v1/
```

### Authentication

```
Headers:
  apikey: {SUPABASE_KEY}
  Authorization: Bearer {SUPABASE_KEY}
  Content-Type: application/json
  Prefer: return=representation  # For POST/PATCH
```

### Common Query Parameters

**Select specific columns:**

```
?select=id,name,description
```

**Filter:**

```
?name=eq.{value}           # Equals
?name=ilike.*{value}*      # Case-insensitive like
?category=in.({val1},{val2}) # In array
```

**Order:**

```
?order=created_at.desc
```

**Limit:**

```
?limit=10
```

### RPC Functions

**Search Embeddings:**

```
POST /rest/v1/rpc/search_embeddings
Body: {
    "query_text": "search query text",  # Pass text, Supabase generates embedding server-side
    "item_type": "directive",
    "match_count": 10
}
```

**Note:** The registry tool passes `query_text` (plain text), not `query_embedding` (vector array). Supabase's RPC function handles embedding generation server-side.

---

## Migration Checklist

### Pre-Migration

- [ ] Backup current registry data
- [ ] Document current Supabase schema
- [ ] List all current registry operations in use

### Phase 1: Removal

- [ ] Delete `kiwi_mcp/api/base.py` (complete deletion, no stubs)
- [ ] Delete `kiwi_mcp/api/directive_registry.py` (complete deletion)
- [ ] Delete `kiwi_mcp/api/tool_registry.py` (complete deletion)
- [ ] Delete `kiwi_mcp/api/knowledge_registry.py` (complete deletion)
- [ ] Delete `kiwi_mcp/storage/vector/registry.py` (complete deletion, no stubs)
- [ ] Update `kiwi_mcp/storage/vector/manager.py` (remove registry store references)
- [ ] Remove registry from `DirectiveHandler`:
  - [ ] Delete `self.registry = DirectiveRegistry()` (no comments)
  - [ ] Delete `_publish_directive()` method completely
  - [ ] Delete `_delete_directive()` method completely
  - [ ] Remove publish/delete from execute() routing
  - [ ] Remove registry search/load code
  - [ ] **NO backwards compat code or comments**
- [ ] Remove registry from `ToolHandler`:
  - [ ] Delete `self.registry = ToolRegistry()` (no comments)
  - [ ] Delete `_publish_tool()` method completely
  - [ ] Delete `_delete_tool()` method completely
  - [ ] Delete `_search_registry()` method completely
  - [ ] Remove publish/delete from execute() routing
  - [ ] Remove registry search/load code
  - [ ] **NO backwards compat code or comments**
- [ ] Remove registry from `KnowledgeHandler`:
  - [ ] Delete `self.registry = KnowledgeRegistry()` (no comments)
  - [ ] Delete `_publish_knowledge()` method completely
  - [ ] Delete `_delete_knowledge()` method completely
  - [ ] Remove publish/delete from execute() routing
  - [ ] Remove registry search/load code
  - [ ] **NO backwards compat code or comments**
- [ ] Update `SearchTool` (remove registry source, no comments)
- [ ] Update `LoadTool` (remove registry source, no comments)
- [ ] Update `ExecuteTool`:
  - [ ] Remove "publish" and "delete" from enum (no comments)
  - [ ] Remove all publish/delete code paths
  - [ ] Update description (remove publish/delete mentions)
  - [ ] **NO backwards compat code or comments**
- [ ] Remove `supabase>=2.0.0` from `pyproject.toml`
- [ ] Search codebase for any remaining "publish" or "delete" references in execute context
- [ ] Remove any TODO/FIXME comments about registry migration
- [ ] Run tests to verify core still works

### Phase 2: Registry Tool

- [ ] Create `.ai/tools/core/registry.py` (or `.yaml` manifest)
- [ ] Ensure `.ai/tools/core/` directory exists
- [ ] Define tool manifest with executor: `http_client`
- [ ] Implement `upload` action handler
- [ ] Implement `download` action handler
- [ ] Implement `search` action handler (RAG + keyword)
- [ ] Implement `publish` action handler
- [ ] Implement `private` action handler
- [ ] Implement `unlist` action handler
- [ ] Implement `get` action handler
- [ ] Implement `list` action handler
- [ ] Implement `update` action handler
- [ ] Implement `delete` action handler
- [ ] Implement `versions` action handler
- [ ] Implement `stats` action handler
- [ ] Test tool discovery and loading
- [ ] Test execution via execute tool
- [ ] Test all 12 actions work correctly
- [ ] Verify executor chain resolution (registry → http_client)

### Phase 3: Testing

- [ ] Write unit tests for registry tool
- [ ] Write integration tests
- [ ] Remove Supabase mocks from tests
- [ ] Update documentation
- [ ] Test end-to-end workflows

### Post-Migration

- [ ] Verify all registry operations work
- [ ] Verify offline mode works (no Supabase)
- [ ] Update user documentation
- [ ] Create migration guide for users

---

## Complexity Assessment

**Overall Difficulty: Medium-Hard (6-8 days)**

### Easy Parts (Low Complexity)

- Removing Supabase dependency from `pyproject.toml`
- Deleting registry API classes
- Removing registry instantiation from handlers
- Making search/load local-only

### Medium Parts (Medium Complexity)

- Implementing registry tool with HTTP client
- Mapping Supabase SDK calls to REST API
- Handling authentication and headers
- Error handling for network failures

### Harder Parts (Higher Complexity)

- Multi-file tool uploads (tool_version_files)
- Comprehensive error handling
- Edge cases and race conditions
- Tool validation and metadata management

---

## Benefits

1. **Smaller Kernel Size**

   - No Supabase Python SDK dependency (~5MB reduction)
   - Faster installation
   - Smaller Docker images

2. **Full Offline Support**

   - Core MCP works without network
   - No hard dependency on external service
   - Better for air-gapped environments

3. **Better Modularity**

   - Registry as optional, swappable component
   - Can swap Supabase for different backend
   - Cleaner separation of concerns

4. **Private + Public Storage**

   - Users can save items privately
   - Users can share items publicly
   - Visibility control (public/private/unlisted)

5. **Dual Search Capabilities**

   - RAG (vector/semantic) search (handled server-side by Supabase)
   - Keyword search
   - Hybrid search combining both (handled server-side)

6. **Consistent Architecture**
   - Uses `HttpClientPrimitive` like other tools
   - Follows primitive-based design
   - No special cases

---

## Risks & Mitigations

### Risk 1: Breaking Changes for Users

**Risk:** Users relying on `publish`/`delete` in execute tool
**Mitigation:**

- **NO backwards compatibility code in core kernel**
- Clear migration guide in documentation (separate from code)
- Registry tool provides same functionality
- Update documentation with migration path
- **Code is clean - users must migrate to registry tool**

### Risk 2: RAG Search Complexity

**Risk:** RAG search may not work if Supabase doesn't have embeddings configured
**Mitigation:**

- Registry tool just passes query to Supabase
- Supabase handles RAG server-side (or returns empty if not configured)
- Fallback to keyword-only search if RAG unavailable
- Document that RAG requires Supabase-side configuration

### Risk 3: Network Failures

**Risk:** HTTP requests may fail
**Mitigation:**

- Comprehensive error handling
- Retry logic in HttpClientPrimitive
- Clear error messages

### Risk 4: Performance

**Risk:** HTTP requests slower than SDK
**Mitigation:**

- HttpClientPrimitive has connection pooling
- Async operations
- Batch operations where possible

---

## Success Criteria

1. ✅ Core kernel has no Supabase dependency
2. ✅ Meta MCP tools remain at 4 (search, load, execute, help)
3. ✅ Registry tool is a core tool (stored in `.ai/tools/core/`)
4. ✅ Registry tool is NOT a meta tool (not hardcoded in server)
5. ✅ Registry tool lives in `.ai/tools/core/registry.py`
6. ✅ Registry tool executed via `execute(item_type="tool", action="run", item_id="registry")`
7. ✅ Registry tool uses `http_client` primitive via executor chain
8. ✅ All registry operations work via registry tool
9. ✅ Search works locally (no registry dependency)
10. ✅ Load works locally (no registry dependency)
11. ✅ Execute tool works without publish/delete
12. ✅ **NO backwards compatibility code for publish/delete**
13. ✅ **NO deprecated warnings or migration comments in code**
14. ✅ **NO stub methods or error messages about removed features**
15. ✅ Registry tool supports all 12 actions
16. ✅ RAG and keyword search both work (RAG handled server-side by Supabase)
17. ✅ Visibility control works (public/private/unlisted)
18. ✅ Registry tool is Python file with metadata (for validation)
18. ✅ All tests pass
19. ✅ Documentation updated
20. ✅ **Codebase is clean with no legacy code or comments**

---

## Next Steps

1. **Review this plan** - Get approval before starting
2. **Start Phase 1** - Remove Supabase from core
3. **Implement Phase 2** - Create registry tool
4. **Test thoroughly** - Phase 3 testing
5. **Update documentation** - User guides and API docs

---

## References

- [Supabase REST API Docs](https://supabase.com/docs/reference/javascript/introduction)
- [HttpClientPrimitive Implementation](../kiwi_mcp/primitives/http_client.py)
- [Database Schema](../docs/DATABASE_SCHEMA_ALIGNMENT.md)
- [Unified Tools Architecture](../docs/UNIFIED_TOOLS_ARCHITECTURE.md)

---

_Generated: 2026-01-26_
