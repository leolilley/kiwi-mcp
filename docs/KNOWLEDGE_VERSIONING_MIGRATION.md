# Knowledge Versioning Migration Complete

**Date:** 2026-01-23  
**Status:** ✅ Complete  
**Related:** [UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md](./UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md), [SCRIPT_TO_TOOL_MIGRATION.md](./SCRIPT_TO_TOOL_MIGRATION.md)

---

## Summary

The knowledge storage structure has been updated to match the directive/tool pattern:
1. **Renamed:** `knowledge_entries` → `knowledge`
2. **Created:** `knowledge_versions` table for version history
3. **Migrated:** All 159 knowledge entries and their content to the new structure

---

## Database Changes

### Tables Renamed

**Old:** `knowledge_entries`  
**New:** `knowledge`

### Tables Created

**Table:** `knowledge_versions`  
**Purpose:** Store version history for knowledge entries (following directive_versions/tool_versions pattern)

### Migration Applied

**Database:** Agent Kiwi (mrecfyfjpwzrzxoiooew.supabase.co)  
**Migration:** `add_knowledge_versioning_and_rename`  
**Status:** ✅ Success

---

## Schema Changes

### knowledge (formerly knowledge_entries)

**Columns removed:**
- `content` - Moved to `knowledge_versions`
- `version` - Moved to `knowledge_versions`

**Columns added:**
- `author_id` (UUID) - References users.id
- `is_official` (BOOLEAN) - Official/community flag
- `download_count` (INTEGER) - Download statistics
- `quality_score` (NUMERIC) - Quality metric

**Final structure:**
```sql
CREATE TABLE knowledge (
    id UUID PRIMARY KEY,
    zettel_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    category TEXT,
    source_type TEXT,
    source_url TEXT,
    tags TEXT[] DEFAULT '{}',
    author_id UUID,
    is_official BOOLEAN DEFAULT false,
    download_count INTEGER DEFAULT 0,
    quality_score NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    search_vector TSVECTOR
);
```

### knowledge_versions (new table)

**Structure:**
```sql
CREATE TABLE knowledge_versions (
    id UUID PRIMARY KEY,
    knowledge_id UUID NOT NULL,
    version TEXT NOT NULL CHECK (is_valid_semver(version)),
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    changelog TEXT,
    is_latest BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
);
```

---

## Data Migration Stats

| Metric | Count |
|--------|-------|
| Knowledge entries migrated | 159 |
| Versions created | 159 |
| Latest versions | 159 |
| Data loss | 0 |

**Verification:**
```sql
SELECT COUNT(*) as total_knowledge, 
       (SELECT COUNT(*) FROM knowledge_versions) as total_versions,
       (SELECT COUNT(*) FROM knowledge_versions WHERE is_latest = true) as latest_versions 
FROM knowledge;

-- Result: 159, 159, 159 ✅
```

---

## Indexes Created

### knowledge table (preserved from knowledge_entries)
- `knowledge_pkey` - PRIMARY KEY on `id`
- `knowledge_zettel_id_key` - UNIQUE on `zettel_id`
- `idx_knowledge_zettel_id` - Index on `zettel_id`
- `idx_knowledge_entry_type` - Index on `entry_type`
- `idx_knowledge_category` - Index on `category`
- `idx_knowledge_search` - GIN index on `search_vector`
- `idx_knowledge_tags` - GIN index on `tags`

### knowledge_versions table (new)
- `knowledge_versions_pkey` - PRIMARY KEY on `id`
- `idx_knowledge_versions_knowledge_id` - Index on `knowledge_id`
- `idx_knowledge_versions_version` - Index on `version`
- `idx_knowledge_versions_is_latest` - Index on `is_latest`

---

## Triggers and Functions

### Search Vector Update

**Function:** `update_knowledge_search_vector()`
```sql
CREATE OR REPLACE FUNCTION update_knowledge_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', 
        COALESCE(NEW.title, '') || ' ' || 
        COALESCE(NEW.category, '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Trigger:** `knowledge_search_vector_update`
- Fires: BEFORE INSERT OR UPDATE
- Updates `search_vector` automatically

---

## RLS Policies

### knowledge table (inherited from knowledge_entries)
- "Users can view all knowledge" - SELECT for all
- "Authenticated users can insert knowledge" - INSERT with auth
- "Users can update their own knowledge" - UPDATE with auth
- "Users can delete their own knowledge" - DELETE with auth

### knowledge_versions table (new)
- "Users can view all knowledge versions" - SELECT for all
- "Authenticated users can insert knowledge versions" - INSERT with auth

---

## Consistency with Other Tables

Now all three main content types follow the same pattern:

| Feature | directives | tools | knowledge |
|---------|-----------|-------|-----------|
| Main table | ✅ | ✅ | ✅ |
| Versions table | ✅ directive_versions | ✅ tool_versions | ✅ knowledge_versions |
| author_id | ✅ | ✅ | ✅ |
| is_official | ✅ | ✅ | ✅ |
| download_count | ✅ | ✅ | ✅ |
| quality_score | ✅ | ✅ | ✅ |
| search_vector | ✅ | ❌ | ✅ |
| Foreign key CASCADE | ✅ | ✅ | ✅ |

---

## Version Management

### Creating New Versions

```sql
-- When updating knowledge, create a new version
INSERT INTO knowledge_versions (
    knowledge_id,
    version,
    content,
    content_hash,
    is_latest,
    created_at
)
VALUES (
    '...', -- knowledge.id
    '1.1.0',
    'Updated content...',
    md5('Updated content...'),
    true,
    NOW()
);

-- Mark previous version as not latest
UPDATE knowledge_versions 
SET is_latest = false 
WHERE knowledge_id = '...' AND version != '1.1.0';
```

### Retrieving Latest Version

```sql
SELECT k.*, v.content, v.version, v.content_hash
FROM knowledge k
JOIN knowledge_versions v ON v.knowledge_id = k.id
WHERE v.is_latest = true AND k.zettel_id = 'example_zettel';
```

### Version History

```sql
SELECT v.version, v.changelog, v.created_at, v.is_latest
FROM knowledge_versions v
WHERE v.knowledge_id = '...'
ORDER BY v.created_at DESC;
```

---

## Migration File

**Location:** `docs/migrations/knowledge_versioning.sql`

**Steps executed:**
1. Create `knowledge_versions` table
2. Migrate content from `knowledge_entries` to `knowledge_versions`
3. Add new columns to `knowledge_entries` (author_id, is_official, etc.)
4. Remove version-specific columns from `knowledge_entries` (content, version)
5. Rename `knowledge_entries` to `knowledge`
6. Add foreign key constraint
7. Create indexes
8. Update search vector function and trigger
9. Enable RLS and create policies
10. Grant permissions
11. Add table comments

---

## Breaking Changes

### For Application Code

⚠️ **Content retrieval pattern changed:**

**Old (knowledge_entries):**
```python
# Single query gets everything
entry = db.query("SELECT * FROM knowledge_entries WHERE zettel_id = ?")
content = entry['content']
```

**New (knowledge + knowledge_versions):**
```python
# Need to join with versions table
result = db.query("""
    SELECT k.*, v.content, v.version 
    FROM knowledge k
    JOIN knowledge_versions v ON v.knowledge_id = k.id
    WHERE k.zettel_id = ? AND v.is_latest = true
""")
content = result['content']
```

### For Database Queries

⚠️ **Table name changed:**
- Replace `knowledge_entries` → `knowledge` in all queries
- Replace `SELECT content FROM knowledge_entries` → Join with `knowledge_versions`

---

## Handler Updates Needed

The KnowledgeHandler in the codebase needs updates:

### Files to Update

1. **`kiwi_mcp/handlers/knowledge/handler.py`**
   - Update queries to join with `knowledge_versions`
   - Update version creation logic
   - Handle version history retrieval

2. **`kiwi_mcp/api/knowledge_registry.py`** (if exists)
   - Update API queries
   - Handle version parameters

3. **`kiwi_mcp/storage/knowledge/resolver.py`** (if exists)
   - Update resolution logic
   - Join with versions table

### Example Update Pattern

**Before:**
```python
cursor.execute("""
    SELECT id, zettel_id, title, content, version
    FROM knowledge_entries
    WHERE zettel_id = %s
""", (zettel_id,))
```

**After:**
```python
cursor.execute("""
    SELECT k.id, k.zettel_id, k.title, v.content, v.version
    FROM knowledge k
    JOIN knowledge_versions v ON v.knowledge_id = k.id
    WHERE k.zettel_id = %s AND v.is_latest = true
""", (zettel_id,))
```

---

## Benefits

### Consistency
- ✅ All three content types (directive, tool, knowledge) now follow the same pattern
- ✅ Easier to understand and maintain
- ✅ Consistent API patterns across all content types

### Version History
- ✅ Full version history preserved
- ✅ Can retrieve any previous version
- ✅ Changelog support for tracking changes
- ✅ Semver validation enforced

### Performance
- ✅ Lighter main table (no large content field)
- ✅ Faster metadata queries
- ✅ Can query versions independently
- ✅ Better index utilization

### Future Features
- ✅ Ready for version comparison
- ✅ Can implement rollback functionality
- ✅ Can track version popularity
- ✅ Can deprecate old versions

---

## Rollback Plan

If needed, the migration can be rolled back:

```sql
-- 1. Recreate knowledge_entries with old structure
CREATE TABLE knowledge_entries AS
SELECT 
    k.id,
    k.zettel_id,
    k.title,
    v.content,
    k.entry_type,
    k.source_type,
    k.source_url,
    k.tags,
    v.version,
    k.created_at,
    k.updated_at,
    k.search_vector,
    k.category
FROM knowledge k
JOIN knowledge_versions v ON v.knowledge_id = k.id
WHERE v.is_latest = true;

-- 2. Drop new tables
DROP TABLE knowledge_versions;
DROP TABLE knowledge;

-- 3. Restore indexes and constraints
-- (run original knowledge_entries schema)
```

**Note:** This would lose version history but preserve current data.

---

## Testing Checklist

- [ ] Verify KnowledgeHandler queries work with new schema
- [ ] Test knowledge entry retrieval
- [ ] Test knowledge entry creation (with version)
- [ ] Test knowledge entry updates (creates new version)
- [ ] Test version history retrieval
- [ ] Test search functionality
- [ ] Verify embeddings still work
- [ ] Test sync operations
- [ ] Verify foreign key cascades work
- [ ] Test RLS policies

---

## Related Documents

- [UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md](./UNIFIED_TOOLS_IMPLEMENTATION_PLAN.md) - Overall architecture
- [SCRIPT_TO_TOOL_MIGRATION.md](./SCRIPT_TO_TOOL_MIGRATION.md) - Related migration
- [RAG_INTEGRATION_COMPLETE.md](./RAG_INTEGRATION_COMPLETE.md) - Vector embeddings
- [DATABASE_EVOLUTION_DESIGN.md](./DATABASE_EVOLUTION_DESIGN.md) - Database design

---

## Database Connection Details

**Project:** Agent Kiwi  
**Project ID:** mrecfyfjpwzrzxoiooew  
**URL:** https://mrecfyfjpwzrzxoiooew.supabase.co  
**Region:** ap-northeast-2  
**PostgreSQL:** 17.6.1.054  

**Migration Name:** `add_knowledge_versioning_and_rename`  
**Applied:** 2026-01-23  
**Status:** ✅ Success  
**Data Migrated:** 159 entries → 159 knowledge + 159 versions
