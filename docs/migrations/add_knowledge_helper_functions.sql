-- Migration: Add helper functions for knowledge queries
-- Description: Creates RPC functions to simplify joining knowledge with knowledge_versions

-- Function to get knowledge entry with latest version content
CREATE OR REPLACE FUNCTION get_knowledge_with_content(p_zettel_id TEXT)
RETURNS TABLE (
    id UUID,
    zettel_id TEXT,
    title TEXT,
    entry_type TEXT,
    category TEXT,
    source_type TEXT,
    source_url TEXT,
    tags TEXT[],
    author_id UUID,
    is_official BOOLEAN,
    download_count INTEGER,
    quality_score NUMERIC,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    version TEXT,
    content TEXT,
    content_hash TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        k.id,
        k.zettel_id,
        k.title,
        k.entry_type,
        k.category,
        k.source_type,
        k.source_url,
        k.tags,
        k.author_id,
        k.is_official,
        k.download_count,
        k.quality_score,
        k.created_at,
        k.updated_at,
        v.version,
        v.content,
        v.content_hash
    FROM knowledge k
    LEFT JOIN knowledge_versions v ON v.knowledge_id = k.id AND v.is_latest = true
    WHERE k.zettel_id = p_zettel_id;
END;
$$;

-- Function to list all knowledge entries with their latest versions
CREATE OR REPLACE FUNCTION list_knowledge_with_versions(
    p_category TEXT DEFAULT NULL,
    p_entry_type TEXT DEFAULT NULL,
    p_limit INT DEFAULT 100
)
RETURNS TABLE (
    zettel_id TEXT,
    title TEXT,
    entry_type TEXT,
    category TEXT,
    tags TEXT[],
    version TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        k.zettel_id,
        k.title,
        k.entry_type,
        k.category,
        k.tags,
        v.version,
        k.created_at,
        k.updated_at
    FROM knowledge k
    LEFT JOIN knowledge_versions v ON v.knowledge_id = k.id AND v.is_latest = true
    WHERE 
        (p_category IS NULL OR k.category = p_category)
        AND (p_entry_type IS NULL OR k.entry_type = p_entry_type)
    ORDER BY k.updated_at DESC
    LIMIT p_limit;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION get_knowledge_with_content TO anon, authenticated;
GRANT EXECUTE ON FUNCTION list_knowledge_with_versions TO anon, authenticated;

-- Add comments
COMMENT ON FUNCTION get_knowledge_with_content IS 'Get knowledge entry with latest version content by zettel_id';
COMMENT ON FUNCTION list_knowledge_with_versions IS 'List knowledge entries with their latest version info';
