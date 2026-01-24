# Database Schema Alignment Complete

**Date:** 2026-01-23  
**Status:** ✅ Complete  
**Database:** Agent Kiwi (mrecfyfjpwzrzxoiooew.supabase.co)

---

## Overview

All three main content types in the Kiwi MCP registry now follow a consistent two-table pattern with proper versioning support.

---

## Schema Alignment

### Main Tables Comparison

| Column | directives | tools | knowledge | Notes |
|--------|-----------|-------|-----------|-------|
| **Identity** |
| `id` | ✅ uuid | ✅ uuid | ✅ uuid | Primary key |
| `name` / identifier | ✅ name | ✅ tool_id | ✅ zettel_id | Unique identifier |
| **Metadata** |
| `category` | ✅ text | ✅ text | ✅ text | Classification |
| `subcategory` | ✅ text | ✅ text | ❌ | Tools/Directives only |
| `description` | ✅ text | ✅ text | ❌ | Tools/Directives only |
| `title` | ❌ | ❌ | ✅ text | Knowledge only |
| `tags` | ✅ jsonb | ✅ array | ✅ array | Different types! |
| **Content Type** |
| `entry_type` | ❌ | ❌ | ✅ text | Knowledge only |
| `tool_type` | ❌ | ✅ text | ❌ | Tools only |
| `dependencies` | ✅ jsonb | ❌ | ❌ | Directives only |
| **Source Info** |
| `source_type` | ❌ | ❌ | ✅ text | Knowledge only |
| `source_url` | ❌ | ❌ | ✅ text | Knowledge only |
| **Author & Quality** |
| `author_id` | ✅ uuid | ✅ uuid | ✅ uuid | ✅ **Aligned** |
| `is_official` | ✅ boolean | ✅ boolean | ✅ boolean | ✅ **Aligned** |
| `download_count` | ✅ integer | ✅ integer | ✅ integer | ✅ **Aligned** |
| `quality_score` | ✅ numeric | ✅ numeric | ✅ numeric | ✅ **Aligned** |
| **Tool-specific Metrics** |
| `success_rate` | ❌ | ✅ numeric | ❌ | Tools only |
| `total_executions` | ❌ | ✅ integer | ❌ | Tools only |
| `avg_execution_time` | ❌ | ✅ numeric | ❌ | Tools only |
| `estimated_cost_usd` | ❌ | ✅ numeric | ❌ | Tools only |
| **Versioning** |
| `latest_version` | ❌ | ✅ text | ❌ | Tools only (cached) |
| **Search** |
| `search_vector` | ✅ tsvector | ❌ | ✅ tsvector | Auto-generated |
| **Timestamps** |
| `created_at` | ✅ timestamptz | ✅ timestamptz | ✅ timestamptz | ✅ **Aligned** |
| `updated_at` | ✅ timestamptz | ✅ timestamptz | ✅ timestamptz | ✅ **Aligned** |
| **Tool-specific** |
| `namespace` | ❌ | ✅ text | ❌ | Tools only |
| `executor_id` | ❌ | ✅ text | ❌ | Tools only |
| `is_builtin` | ❌ | ✅ boolean | ❌ | Tools only |
| `visibility` | ❌ | ✅ text | ❌ | Tools only |

### Version Tables Comparison

| Column | directive_versions | tool_versions | knowledge_versions | Aligned? |
|--------|-------------------|---------------|-------------------|----------|
| `id` | ✅ uuid | ✅ uuid | ✅ uuid | ✅ |
| `*_id` | ✅ directive_id | ✅ tool_id | ✅ knowledge_id | ✅ |
| `version` | ✅ text + semver | ✅ text | ✅ text + semver | ⚠️ tools missing check |
| `content` | ✅ text | ❌ (manifest) | ✅ text | ⚠️ tools different |
| `manifest` | ❌ | ✅ jsonb | ❌ | Tools only |
| `manifest_yaml` | ❌ | ✅ text | ❌ | Tools only |
| `content_hash` | ✅ text | ✅ text | ✅ text | ✅ |
| `changelog` | ✅ text | ✅ text | ✅ text | ✅ |
| `is_latest` | ✅ boolean | ✅ boolean | ✅ boolean | ✅ |
| `deprecated` | ❌ | ✅ boolean | ❌ | Tools only |
| `deprecation_message` | ❌ | ✅ text | ❌ | Tools only |
| `published_at` | ❌ | ✅ timestamptz | ❌ | Tools only |
| `created_at` | ✅ timestamptz | ✅ timestamptz | ✅ timestamptz | ✅ |

---

## Key Achievements

### ✅ Core Consistency

All three types now have:
- **Main table** for metadata
- **Versions table** for version history
- **author_id** for attribution
- **is_official** for certification
- **download_count** for popularity
- **quality_score** for quality metrics
- **Foreign key cascade** for data integrity
- **RLS policies** for security
- **Timestamps** for auditing

### ✅ Version Management

All three types support:
- Multiple versions per item
- Version history tracking
- `is_latest` flag
- Content hashing
- Changelog support
- Semver validation (directives, knowledge)

### ✅ Search Capabilities

- **directives**: Full-text search via `search_vector`
- **knowledge**: Full-text search via `search_vector`
- **tools**: Tag-based search (no search_vector)
- **All types**: Vector embeddings in `item_embeddings` table

---

## Type-Specific Differences

These differences are **intentional** and reflect the unique needs of each content type:

### Directives
- **dependencies** - Other directives needed
- No version in main table (only in directive_versions)

### Tools
- **tool_type** - Execution type (primitive, runtime, mcp, etc.)
- **executor_id** - Which executor to use
- **namespace** - Tool organization
- **is_builtin** - System vs user tools
- **visibility** - public/unlisted/private
- **Execution metrics** - success_rate, executions, timing, cost
- **manifest** - YAML/JSON tool definition (instead of plain content)
- **deprecated** - Deprecation support in versions
- **latest_version** - Cached for performance

### Knowledge
- **entry_type** - Type of knowledge (pattern, concept, learning, etc.)
- **title** - Display title
- **source_type** - Where it came from (youtube, docs, manual, etc.)
- **source_url** - Original URL
- **zettel_id** - Zettelkasten-style ID
- Content in versions table (like directives)

---

## Database Statistics

| Table | Rows | Has Versions? | Version Count |
|-------|------|---------------|---------------|
| `directives` | 141 | ✅ | 351 |
| `tools` | 15 | ✅ | 15 |
| `knowledge` | 159 | ✅ | 159 |
| `item_embeddings` | 0 | N/A | N/A |

**Total content items:** 315 (141 + 15 + 159)  
**Total versions:** 525 (351 + 15 + 159)

---

## Tags Implementation Note

⚠️ **Inconsistency:** Tags are implemented differently:
- **directives**: `tags JSONB` (array stored as JSON)
- **tools**: `tags TEXT[]` (native array)
- **knowledge**: `tags TEXT[]` (native array)

**Recommendation:** Consider standardizing on `TEXT[]` for all types in future migration.

---

## Foreign Key Cascade

All version tables properly cascade deletes:

```sql
-- directives
FOREIGN KEY (directive_id) REFERENCES directives(id) ON DELETE CASCADE

-- tools
FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE

-- knowledge
FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
```

This ensures that deleting a main item also deletes all its versions.

---

## Query Patterns

### Get Latest Version

**Directives:**
```sql
SELECT d.*, v.content, v.version
FROM directives d
JOIN directive_versions v ON v.directive_id = d.id
WHERE d.name = ? AND v.is_latest = true;
```

**Tools:**
```sql
SELECT t.*, v.manifest, v.version
FROM tools t
JOIN tool_versions v ON v.tool_id = t.id
WHERE t.tool_id = ? AND v.is_latest = true;
```

**Knowledge:**
```sql
SELECT k.*, v.content, v.version
FROM knowledge k
JOIN knowledge_versions v ON v.knowledge_id = k.id
WHERE k.zettel_id = ? AND v.is_latest = true;
```

### Get All Versions

**Pattern (same for all types):**
```sql
SELECT v.*
FROM {type}_versions v
WHERE v.{type}_id = ?
ORDER BY v.created_at DESC;
```

---

## Vector Embeddings

All three types can be embedded in the `item_embeddings` table:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'item_embeddings';

-- Results:
-- item_type CHECK (item_type IN ('directive', 'tool', 'knowledge'))
```

This enables semantic search across all content types.

---

## Next Steps

### Recommended Improvements

1. **Standardize tags** - Use `TEXT[]` for all types
2. **Add search_vector to tools** - Enable full-text search
3. **Add semver check to tool_versions** - Enforce version format
4. **Add subcategory to knowledge** - Improve organization

### Handler Updates Required

All handlers need updates to work with the new versioning structure:

- [ ] **DirectiveHandler** - Already updated ✅
- [ ] **ToolHandler** - Needs version table integration
- [ ] **KnowledgeHandler** - Needs updates for renamed table and versions
- [ ] **SearchTool** - Verify works with all three types
- [ ] **LoadTool** - Update to join with version tables
- [ ] **ExecuteTool** - Update version creation logic

---

## Related Migrations

1. **`add_vector_embeddings_support`** - Created `item_embeddings` table
2. **`add_knowledge_versioning_and_rename`** - Created `knowledge_versions`, renamed `knowledge_entries` → `knowledge`

---

## Verification Queries

### Check Schema Consistency

```sql
-- Verify all types have required columns
SELECT 
    'directives' as table_name,
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='directives' AND column_name='author_id') as has_author,
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='directives' AND column_name='is_official') as has_official,
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='directives' AND column_name='download_count') as has_downloads,
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='directives' AND column_name='quality_score') as has_quality
UNION ALL
SELECT 'tools', 
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tools' AND column_name='author_id'),
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tools' AND column_name='is_official'),
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tools' AND column_name='download_count'),
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='tools' AND column_name='quality_score')
UNION ALL
SELECT 'knowledge',
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='knowledge' AND column_name='author_id'),
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='knowledge' AND column_name='is_official'),
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='knowledge' AND column_name='download_count'),
    EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='knowledge' AND column_name='quality_score');

-- Expected: All TRUE
```

### Check Version Tables

```sql
-- Verify all version tables exist and have correct structure
SELECT table_name, column_name 
FROM information_schema.columns 
WHERE table_name LIKE '%_versions' 
  AND column_name IN ('id', 'version', 'content_hash', 'is_latest', 'created_at')
ORDER BY table_name, column_name;
```

---

## Success Metrics

- ✅ All three content types have main + versions tables
- ✅ All three types have author_id, is_official, download_count, quality_score
- ✅ All three types support version history
- ✅ All three types have foreign key cascade
- ✅ All three types have RLS policies
- ✅ Data migration successful (0 data loss)
- ✅ 525 total versions tracked across 315 items

---

## Database Connection

**Project:** Agent Kiwi  
**Project ID:** mrecfyfjpwzrzxoiooew  
**URL:** https://mrecfyfjpwzrzxoiooew.supabase.co  
**Region:** ap-northeast-2  
**PostgreSQL:** 17.6.1.054  
**Last Updated:** 2026-01-23
