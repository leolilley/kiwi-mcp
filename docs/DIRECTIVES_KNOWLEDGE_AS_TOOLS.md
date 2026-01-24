# Directives & Knowledge as Tools: Design Exploration

**Date:** 2026-01-24  
**Status:** Draft - Design Exploration  
**Goal:** Evaluate how directives and knowledge can become data-driven tools while preserving their unique characteristics

---

## Executive Summary

This document explores making directives and knowledge first-class tools with `executor: null` (pure retrieval), while:

1. **Preserving formats** - XML for directives, markdown+frontmatter for knowledge
2. **Maintaining specialized features** - Relationships for knowledge, permissions for directives
3. **Leveraging unified validation** - Integrity verification, chain validation
4. **Keeping separate storage** - Own tables with unified API layer

---

## Current Architecture

### Directives

```
┌─────────────────────────────────────────────────────────────────┐
│                     DIRECTIVE SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Format: Markdown with embedded XML                             │
│                                                                 │
│  ```markdown                                                    │
│  # Research Topic Directive                                     │
│                                                                 │
│  <directive name="research_topic" version="1.0.0">              │
│    <metadata>                                                   │
│      <category>research</category>                              │
│      <model tier="balanced" />                                  │
│    </metadata>                                                  │
│    <permissions>                                                │
│      <execute resource="tool" action="web_search" />            │
│    </permissions>                                               │
│    <inputs>                                                     │
│      <input name="topic" type="string" required="true" />       │
│    </inputs>                                                    │
│    <process>                                                    │
│      <step name="search">...</step>                             │
│    </process>                                                   │
│  </directive>                                                   │
│  ```                                                            │
│                                                                 │
│  Storage:                                                       │
│    - Local: .ai/directives/*.md, ~/.ai/directives/*.md          │
│    - Registry: directives, directive_versions tables            │
│                                                                 │
│  Handler: DirectiveHandler                                      │
│    - search(): Local files + registry                           │
│    - load(): Parse XML, extract metadata                        │
│    - execute(run): Return parsed directive for agent            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Knowledge

```
┌─────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Format: Markdown with YAML frontmatter (Zettelkasten)          │
│                                                                 │
│  ```markdown                                                    │
│  ---                                                            │
│  zettel_id: 20260124-api-patterns                               │
│  title: REST API Design Patterns                                │
│  entry_type: pattern                                            │
│  category: architecture                                         │
│  tags: [api, rest, design]                                      │
│  references:                                                    │
│    - 20260101-http-methods                                      │
│  extends:                                                       │
│    - 20260115-web-fundamentals                                  │
│  version: 1.0.0                                                 │
│  ---                                                            │
│                                                                 │
│  # REST API Design Patterns                                     │
│                                                                 │
│  Content here...                                                │
│  ```                                                            │
│                                                                 │
│  Storage:                                                       │
│    - Local: .ai/knowledge/*.md, ~/.ai/knowledge/*.md            │
│    - Registry: knowledge_entries, knowledge_relationships       │
│                                                                 │
│  Handler: KnowledgeHandler                                      │
│    - search(): Local files + registry + relationships           │
│    - load(): Parse frontmatter, optionally include related      │
│    - execute(run): Return content for agent context             │
│                                                                 │
│  Special: Graph relationships (extends, references, contradicts)│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tools

```
┌─────────────────────────────────────────────────────────────────┐
│                       TOOL SYSTEM                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Format: YAML manifest + source files                           │
│                                                                 │
│  ```yaml                                                        │
│  tool_id: enrich_emails                                         │
│  tool_type: script                                              │
│  executor_id: python_runtime                                    │
│  version: 1.0.0                                                 │
│  manifest:                                                      │
│    entrypoint: main.py                                          │
│    language: python                                             │
│  ```                                                            │
│                                                                 │
│  Storage:                                                       │
│    - Local: .ai/tools/*.py + manifest.yaml                      │
│    - Registry: tools, tool_versions, tool_version_files         │
│                                                                 │
│  Execution: Chain resolution → primitive (subprocess/http)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Unification Question

### What "Tool" Means

A tool in our system is:

1. **Identifiable** - Has a unique ID and version
2. **Searchable** - Can be found by query
3. **Loadable** - Can be retrieved from storage
4. **Executable** - Can be "run" (even if "run" means "return content")
5. **Verifiable** - Has integrity hash, can be validated

Both directives and knowledge satisfy criteria 1-4. With `executor: null`, they can satisfy 5.

### The Key Difference: Execution Model

| Type | What "Execute" Does | Primitive? |
|------|---------------------|------------|
| script | Runs code via runtime → subprocess | Yes |
| api | Makes HTTP request | Yes |
| mcp_server | Spawns MCP process | Yes |
| **directive** | Returns XML for agent to interpret | **No** |
| **knowledge** | Returns content for agent context | **No** |

Directives and knowledge are **agent-interpreted**, not **primitive-executed**.

---

## Proposed Model: Unified API, Separate Storage

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED KIWI API                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   UnifiedHandler                         │   │
│  │                                                          │   │
│  │  search(item_type, query) ──────────────────────────────►│   │
│  │  load(item_type, item_id, source) ──────────────────────►│   │
│  │  execute(item_type, action, item_id, params) ───────────►│   │
│  │                                                          │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│           ┌───────────────┼───────────────┐                    │
│           ▼               ▼               ▼                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Directive   │  │ Knowledge   │  │    Tool     │             │
│  │  Handler    │  │  Handler    │  │   Handler   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ directives  │  │ knowledge_  │  │   tools     │             │
│  │ directive_  │  │ entries     │  │ tool_       │             │
│  │ versions    │  │ knowledge_  │  │ versions    │             │
│  │             │  │ relationships│  │ tool_       │             │
│  │             │  │             │  │ version_    │             │
│  │             │  │             │  │ files       │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Shared Services                          │   │
│  │                                                          │   │
│  │  IntegrityVerifier  ChainValidator  LockfileManager      │   │
│  │  ValidationManager  MetadataManager  VectorStore         │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why Separate Tables?

| Reason | Directives | Knowledge | Tools |
|--------|------------|-----------|-------|
| **Specialized columns** | permissions_xml, model_tier | entry_type, source_type | executor_id, tool_type |
| **Relationships** | None | Graph relationships table | Executor chain |
| **Content format** | XML in markdown | Markdown + frontmatter | YAML + source files |
| **Search semantics** | "Find workflow for X" | "What do I know about X" | "Find tool that does X" |
| **Versioning** | Directive-specific | Zettel-specific | Semver |

Forcing everything into one table loses these specializations.

---

## Detailed Design: Search

### Current Search Behavior

```python
# DirectiveHandler.search()
- Searches local .ai/directives/ files
- Searches registry via DirectiveRegistry.search()
- Parses XML to extract metadata for filtering
- Scores by relevance to query

# KnowledgeHandler.search()  
- Searches local .ai/knowledge/ files
- Searches registry via KnowledgeRegistry.search()
- Can include related entries (graph traversal)
- Filters by entry_type, category, tags

# ToolHandler.search()
- Searches local .ai/tools/ files
- Searches registry via ToolRegistry.search()
- Filters by tool_type, category
```

### Unified Search Proposal

```python
class UnifiedSearch:
    """Unified search across all item types."""
    
    async def search(
        self,
        query: str,
        item_types: List[str] = ["directive", "tool", "knowledge"],
        source: str = "all",  # local, registry, all
        limit: int = 10,
        filters: Optional[Dict] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Search across multiple item types.
        
        Returns:
            {
                "directives": [...],
                "tools": [...],
                "knowledge": [...],
                "total": N,
            }
        """
        results = {}
        
        if "directive" in item_types:
            results["directives"] = await self.directive_handler.search(
                query, source, limit, **self._filter_for("directive", filters)
            )
            
        if "tool" in item_types:
            results["tools"] = await self.tool_handler.search(
                query, source, limit, **self._filter_for("tool", filters)
            )
            
        if "knowledge" in item_types:
            results["knowledge"] = await self.knowledge_handler.search(
                query, source, limit, **self._filter_for("knowledge", filters)
            )
        
        return results
```

### Search Considerations

1. **Vector search unification**: All three already use the same `LocalVectorStore`. Embeddings are compatible.

2. **Result ranking**: How to rank across types? Options:
   - Separate rankings per type (current proposal)
   - Unified ranking with type as a feature
   - User preference for type priority

3. **Filter compatibility**: Each type has different filters:
   - Directives: category, tech_stack, model_tier
   - Knowledge: entry_type, tags, relationships
   - Tools: tool_type, executor, category

---

## Detailed Design: Load

### Current Load Behavior

```python
# DirectiveHandler.load()
- source: project, user, registry
- destination: project, user (for copying)
- Returns: Parsed directive with XML structure

# KnowledgeHandler.load()
- source: project, user, registry  
- destination: project, user (for copying)
- include_relationships: bool (graph traversal)
- Returns: Entry with optional related entries

# ToolHandler.load()
- source: project, user, registry
- destination: project, user (for copying)
- Returns: Tool with manifest and files
```

### Load Considerations

1. **Copying between spaces**: All three support copying from registry → project/user. This should remain.

2. **Knowledge relationships**: `include_relationships=True` triggers graph traversal. This is unique to knowledge and must be preserved.

3. **Directive parsing**: `parse_directive_file()` extracts XML structure. This parsing logic stays in DirectiveHandler.

4. **Tool files**: Tools have multiple files (main.py, requirements.txt). Directives and knowledge are single-file.

### Unified Load API (No Changes Needed)

The current MCP tools already provide unified API:

```python
# Current kiwi-mcp tools
mcp__kiwi_mcp__load(item_type="directive", item_id="X", source="project")
mcp__kiwi_mcp__load(item_type="tool", item_id="X", source="project")
mcp__kiwi_mcp__load(item_type="knowledge", item_id="X", source="project")
```

Each routes to the appropriate handler. **No changes needed here.**

---

## Detailed Design: Execute

### Current Execute Behavior

```python
# DirectiveHandler.execute(action="run")
- Parses directive XML
- Extracts inputs, process steps, permissions
- Returns structured data for agent to interpret
- Agent then follows the steps

# KnowledgeHandler.execute(action="run")
- Returns entry content
- Optionally includes relationships
- Agent uses content as context

# ToolHandler.execute(action="run")
- Resolves executor chain
- Validates integrity at each step
- Validates parent→child relationships
- Merges configs
- Executes via subprocess or http_client primitive
```

### The `executor: null` Question

For tools, execution means running code. For directives/knowledge, "execution" means retrieval.

**Option A: Separate execution paths (Current)**
```python
# Directive/Knowledge: Handler returns content directly
# Tool: Handler delegates to PrimitiveExecutor
```

**Option B: Unified with null executor**
```python
# All go through PrimitiveExecutor
# executor: null → return content directly (no primitive)
```

**Recommendation: Keep Option A**

Reason: Forcing directives/knowledge through PrimitiveExecutor adds complexity without benefit. The chain validation/integrity systems are designed for **executor chains**, not content retrieval.

However, we CAN add integrity verification to directive/knowledge handlers directly:

```python
class DirectiveHandler:
    async def execute(self, action: str, directive_name: str, ...):
        if action == "run":
            # Load directive
            directive = self._load_directive(directive_name, source)
            
            # NEW: Verify integrity (if stored)
            if directive.get("content_hash"):
                computed = compute_directive_integrity(directive)
                if computed != directive["content_hash"]:
                    return {"error": "Integrity verification failed"}
            
            # Return for agent interpretation
            return self._run_directive(directive, inputs)
```

---

## Detailed Design: Publishing

### Current Publishing

```python
# DirectiveHandler.execute(action="publish")
- Validates directive XML structure
- Computes hash
- Uploads to directives/directive_versions tables

# KnowledgeHandler.execute(action="publish")
- Validates frontmatter
- Computes hash
- Uploads to knowledge_entries table
- Creates knowledge_relationships entries

# ToolHandler.execute(action="publish")
- Validates manifest
- Computes canonical integrity hash
- Uploads to tools/tool_versions/tool_version_files tables
```

### Publishing with Unified Integrity

We can use the same `compute_tool_integrity()` pattern for all:

```python
# For directives
def compute_directive_integrity(
    directive_name: str,
    version: str,
    xml_content: str,
    metadata: Dict,
) -> str:
    """Canonical hash for directive version."""
    payload = {
        "directive_name": directive_name,
        "version": version,
        "content_hash": hashlib.sha256(xml_content.encode()).hexdigest(),
        "metadata": metadata,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


# For knowledge
def compute_knowledge_integrity(
    zettel_id: str,
    version: str,
    content: str,
    frontmatter: Dict,
) -> str:
    """Canonical hash for knowledge entry version."""
    payload = {
        "zettel_id": zettel_id,
        "version": version,
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        "frontmatter": frontmatter,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
```

---

## Detailed Design: Relationships

### Knowledge Relationships (Keep As-Is)

Knowledge has graph relationships that are fundamental to Zettelkasten:

```sql
CREATE TABLE knowledge_relationships (
    id UUID PRIMARY KEY,
    from_zettel_id TEXT NOT NULL,
    to_zettel_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- extends, references, contradicts, supersedes
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

This is **unique to knowledge** and should NOT be unified with tools.

### Directive Relationships (New?)

Directives could benefit from relationships:

```yaml
# Directive that extends another
directive: research_topic_advanced
extends: research_topic  # Base directive
version: 2.0.0
```

But this is lower priority. Directives are more standalone than knowledge.

### Tool Relationships (Executor Chain)

Tools already have relationships via `executor_id`:

```
my_script → python_runtime → subprocess
```

This is a different kind of relationship (execution dependency) than knowledge relationships (semantic links).

---

## Detailed Design: Database Schema

### Option 1: Keep Completely Separate (Recommended)

```sql
-- Directives (existing)
CREATE TABLE directives (...);
CREATE TABLE directive_versions (...);

-- Knowledge (existing)  
CREATE TABLE knowledge_entries (...);
CREATE TABLE knowledge_relationships (...);

-- Tools (existing)
CREATE TABLE tools (...);
CREATE TABLE tool_versions (...);
CREATE TABLE tool_version_files (...);
```

**Pros:**
- Each optimized for its use case
- No migration needed
- Relationships preserved
- Type-specific columns

**Cons:**
- Three separate search implementations
- Three separate publish flows

### Option 2: Unified Table with Type Discrimination

```sql
CREATE TABLE items (
    id UUID PRIMARY KEY,
    item_type TEXT NOT NULL,  -- 'directive', 'tool', 'knowledge'
    item_id TEXT NOT NULL,
    namespace TEXT,
    name TEXT,
    description TEXT,
    -- Type-specific in JSONB
    type_data JSONB,  -- executor_id, entry_type, permissions, etc.
    ...
);

-- Keep relationships separate (knowledge-specific)
CREATE TABLE knowledge_relationships (...);

-- Keep files separate (tool-specific)
CREATE TABLE item_version_files (...);
```

**Pros:**
- Single search query across types
- Unified versioning

**Cons:**
- JSONB loses strong typing
- Queries become complex
- Migration risk

### Option 3: Hybrid with Views (Best of Both)

```sql
-- Keep separate tables (source of truth)
CREATE TABLE directives (...);
CREATE TABLE tools (...);
CREATE TABLE knowledge_entries (...);

-- Create unified view for search
CREATE VIEW unified_items AS
SELECT 
    'directive' as item_type,
    directive_id as item_id,
    name,
    description,
    category,
    NULL as executor_id,
    NULL as entry_type,
    latest_version,
    created_at
FROM directives
UNION ALL
SELECT 
    'tool' as item_type,
    tool_id as item_id,
    name,
    description,
    category,
    executor_id,
    NULL as entry_type,
    latest_version,
    created_at
FROM tools
UNION ALL
SELECT 
    'knowledge' as item_type,
    zettel_id as item_id,
    title as name,
    NULL as description,
    category,
    NULL as executor_id,
    entry_type,
    version as latest_version,
    created_at
FROM knowledge_entries;

-- Search function uses the view
CREATE FUNCTION search_all_items(p_query TEXT, p_types TEXT[] DEFAULT NULL)
RETURNS TABLE(...) AS $$
    SELECT * FROM unified_items
    WHERE (p_types IS NULL OR item_type = ANY(p_types))
    AND (name ILIKE '%' || p_query || '%' 
         OR description ILIKE '%' || p_query || '%')
    ORDER BY ...
$$;
```

**Pros:**
- Unified search without migration
- Each table keeps its optimizations
- Relationships preserved
- Gradual adoption

**Cons:**
- View maintenance
- Slightly more complex queries

---

## Detailed Design: Validation Schemas

### Directive Validation

Directives already have XML schema validation via `DirectiveValidator`:

```python
class DirectiveValidator:
    """Validates directive XML structure."""
    
    REQUIRED_TAGS = ["metadata", "process"]
    OPTIONAL_TAGS = ["inputs", "outputs", "permissions", "context"]
    
    def validate_xml(self, xml_content: str) -> ValidationResult:
        # Parse XML
        # Check required tags
        # Validate metadata structure
        # Validate permissions format
        ...
```

This is **definition-time validation** (Layer 1). It's already data-driven via the tag lists.

### Knowledge Validation

Knowledge already has frontmatter validation via `KnowledgeValidator`:

```python
class KnowledgeValidator:
    """Validates knowledge entry frontmatter."""
    
    REQUIRED_FIELDS = ["zettel_id", "title"]
    VALID_ENTRY_TYPES = ["pattern", "learning", "reference", "concept", ...]
    
    def validate_frontmatter(self, frontmatter: Dict) -> ValidationResult:
        # Check required fields
        # Validate zettel_id format
        # Validate relationships exist
        ...
```

### Adding JSON Schema Support

For tools, we added `config_schema` for runtime validation. We could do the same for directives/knowledge:

```yaml
# Directive manifest (optional schema for inputs)
directive: research_topic
version: 1.0.0
input_schema:
  type: object
  properties:
    topic:
      type: string
      minLength: 3
    depth:
      type: string
      enum: [shallow, deep, exhaustive]
  required: [topic]
```

```yaml
# Knowledge manifest (optional schema for frontmatter extensions)
zettel_id: 20260124-api-patterns
frontmatter_schema:
  type: object
  properties:
    complexity:
      type: string
      enum: [beginner, intermediate, advanced]
```

---

## What Changes vs What Stays

### Stays the Same

| Component | Status |
|-----------|--------|
| XML format for directives | ✅ Preserved |
| Markdown + frontmatter for knowledge | ✅ Preserved |
| Separate database tables | ✅ Preserved |
| Knowledge relationships | ✅ Preserved |
| Local file structure (.ai/directives/, etc.) | ✅ Preserved |
| Existing handlers (DirectiveHandler, etc.) | ✅ Preserved |
| MCP tool interface | ✅ Preserved |

### Changes/Additions

| Component | Change |
|-----------|--------|
| Integrity hashing | Add `compute_directive_integrity()`, `compute_knowledge_integrity()` |
| Integrity verification | Add to DirectiveHandler, KnowledgeHandler |
| Unified search view | New database view (optional) |
| Validation schemas | Optional JSON Schema for inputs/frontmatter |
| Publish flow | Compute and store integrity hash |

---

## Implementation Plan

### Phase 1: Integrity for Directives/Knowledge ✅ COMPLETE

1. ✅ Created `kiwi_mcp/primitives/integrity.py` functions:
   - `compute_directive_integrity(directive_name, version, xml_content, metadata)`
   - `verify_directive_integrity(...)` 
   - `compute_knowledge_integrity(zettel_id, version, content, frontmatter)`
   - `verify_knowledge_integrity(...)`

2. ✅ Updated DirectiveHandler:
   - `_compute_directive_integrity()` helper method
   - `_verify_directive_integrity()` helper method
   - Compute and return integrity on create/update
   - Include integrity in run response

3. ✅ Updated KnowledgeHandler:
   - `_compute_knowledge_integrity()` helper method
   - `_verify_knowledge_integrity()` helper method
   - Compute and return integrity on create/update
   - Include integrity in run response

4. ✅ Added 23 tests for directive/knowledge integrity in:
   - `tests/primitives/test_directive_knowledge_integrity.py`

5. ⏳ Add `content_hash` column to directive_versions, knowledge_entries (if missing) - DB migration pending

### Phase 2: Unified Search (Optional)

1. Create `unified_items` view in database
2. Create `search_all_items()` RPC
3. Add `UnifiedSearch` class for cross-type search

### Phase 3: Validation Schemas ✅ COMPLETE

1. ✅ Added `input_schema` support to directive validation:
   - `_extract_input_schema()` - Extracts JSON Schema from `<schema>` element in `<inputs>`
   - `_build_input_schema_from_spec()` - Auto-generates schema from `<input>` elements
   - `_validate_inputs_with_schema()` - Validates params against schema before execution
   - Returns `inputs_validated: true` and optional `input_schema` in run response

2. ✅ Added `frontmatter_schema` support to knowledge validation:
   - `_extract_frontmatter_schema()` - Extracts custom schema from frontmatter
   - `_build_base_frontmatter_schema()` - Base schema for standard fields (zettel_id, title, etc.)
   - `_validate_frontmatter_with_schema()` - Validates frontmatter against combined schema
   - Returns `frontmatter_validated: true` in run response

3. ✅ Runtime validation before execution:
   - DirectiveHandler: Validates inputs after required check, before MCP processing
   - KnowledgeHandler: Validates frontmatter after centralized validation, before returning
   - Both return validation_warnings if any non-blocking issues

4. ✅ Added 16 tests in `tests/unit/test_input_schema_validation.py`

---

## Decision Matrix

| Question | Recommendation | Rationale |
|----------|----------------|-----------|
| Keep separate tables? | **Yes** | Preserves specializations |
| Add integrity to directives/knowledge? | **Yes** | Enables verification |
| Force through PrimitiveExecutor? | **No** | Adds complexity without benefit |
| Create unified search view? | **Optional** | Nice-to-have, not critical |
| Add JSON Schema for inputs? | **Optional** | Useful for complex directives |
| Make directives/knowledge `executor: null` tools? | **No** | They're not tools in the execution sense |

---

## Conclusion

The cleanest approach is:

1. **Keep directives and knowledge as their own item types** with separate tables
2. **Add integrity hashing** using the same canonical pattern as tools
3. **Keep handlers separate** but share common services (IntegrityVerifier, etc.)
4. **Optionally add unified search** via database view
5. **Don't force the tool execution model** on non-executable items

The `executor: null` concept from UNIFIED_TOOLS_DEFERRED.md works conceptually but doesn't provide enough value to justify routing everything through PrimitiveExecutor. Instead, we extract the valuable parts (integrity verification, validation) and apply them directly to the existing handlers.

---

## Related Documents

- [UNIFIED_TOOLS_DEFERRED.md](./UNIFIED_TOOLS_DEFERRED.md) - Original deferred vision
- [TOOL_CHAIN_VALIDATION_DESIGN.md](../TOOL_CHAIN_VALIDATION_DESIGN.md) - Validation architecture
- [DATA_DRIVEN_VALIDATION_DECISION.md](./DATA_DRIVEN_VALIDATION_DECISION.md) - Two-layer validation
