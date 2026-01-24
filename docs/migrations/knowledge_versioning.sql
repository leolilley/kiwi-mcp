-- Migration: Add knowledge versioning and rename knowledge_entries to knowledge
-- Description: Creates knowledge_versions table and restructures knowledge to match directive/tool pattern

-- Step 1: Create knowledge_versions table (following directive_versions/tool_versions pattern)
CREATE TABLE knowledge_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_id UUID NOT NULL,
    version TEXT NOT NULL CHECK (is_valid_semver(version)),
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    changelog TEXT,
    is_latest BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 2: Insert version data from knowledge_entries before removing content column
INSERT INTO knowledge_versions (
    knowledge_id,
    version,
    content,
    content_hash,
    is_latest,
    created_at
)
SELECT 
    id,
    COALESCE(version, '1.0.0') as version,
    content,
    md5(content) as content_hash,
    true as is_latest,
    created_at
FROM knowledge_entries;

-- Step 3: Add new columns to knowledge_entries (to match directive/tool pattern)
ALTER TABLE knowledge_entries
    ADD COLUMN IF NOT EXISTS author_id UUID,
    ADD COLUMN IF NOT EXISTS is_official BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS download_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quality_score NUMERIC DEFAULT 0;

-- Step 4: Remove version-specific columns from main table (now in knowledge_versions)
ALTER TABLE knowledge_entries
    DROP COLUMN IF EXISTS content,
    DROP COLUMN IF EXISTS version;

-- Step 5: Rename table to knowledge
ALTER TABLE knowledge_entries RENAME TO knowledge;

-- Step 6: Add foreign key constraint
ALTER TABLE knowledge_versions
ADD CONSTRAINT knowledge_versions_knowledge_id_fkey
FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE;

-- Step 7: Create indexes for knowledge_versions
CREATE INDEX idx_knowledge_versions_knowledge_id ON knowledge_versions (knowledge_id);
CREATE INDEX idx_knowledge_versions_version ON knowledge_versions (version);
CREATE INDEX idx_knowledge_versions_is_latest ON knowledge_versions (is_latest);

-- Step 8: Update search_vector generation for knowledge (if not already exists)
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

-- Drop existing trigger if it exists and recreate
DROP TRIGGER IF EXISTS knowledge_search_vector_update ON knowledge;
CREATE TRIGGER knowledge_search_vector_update
    BEFORE INSERT OR UPDATE ON knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_knowledge_search_vector();

-- Step 9: Enable Row Level Security (already enabled, but ensures it)
ALTER TABLE knowledge_versions ENABLE ROW LEVEL SECURITY;

-- Step 10: Create RLS policies for knowledge_versions (knowledge policies already exist)
CREATE POLICY "Users can view all knowledge versions" ON knowledge_versions
    FOR SELECT USING (true);

CREATE POLICY "Authenticated users can insert knowledge versions" ON knowledge_versions
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Step 11: Grant permissions
GRANT SELECT, INSERT ON knowledge_versions TO anon, authenticated;

-- Step 12: Add comment for documentation
COMMENT ON TABLE knowledge IS 'Knowledge base entries - stores metadata, content versions in knowledge_versions';
COMMENT ON TABLE knowledge_versions IS 'Version history for knowledge entries';
