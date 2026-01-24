-- Migration: Fix Supabase database linter security warnings
-- Description: Set search_path for functions and move vector extension to extensions schema

-- Step 1: Fix search_embeddings function - set search_path
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(384),
    match_count INT DEFAULT 20,
    filter_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    item_id TEXT,
    item_type TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ie.item_id,
        ie.item_type,
        ie.content,
        ie.metadata,
        1 - (ie.embedding <=> query_embedding) AS similarity
    FROM item_embeddings ie
    WHERE (filter_type IS NULL OR ie.item_type = filter_type)
    ORDER BY ie.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Step 2: Fix update_updated_at_column function - set search_path
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER 
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Step 3: Fix update_knowledge_search_vector function - set search_path
CREATE OR REPLACE FUNCTION update_knowledge_search_vector()
RETURNS TRIGGER 
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', 
        COALESCE(NEW.title, '') || ' ' || 
        COALESCE(NEW.category, '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '')
    );
    RETURN NEW;
END;
$$;

-- Step 4: Move vector extension to extensions schema (if not already there)
-- Note: This requires superuser privileges and may need to be done manually via Supabase dashboard
-- CREATE SCHEMA IF NOT EXISTS extensions;
-- ALTER EXTENSION vector SET SCHEMA extensions;

-- Explanation: The vector extension is typically installed in 'public' by default.
-- Moving it requires recreating objects that depend on it, which is complex.
-- Supabase recommends installing new extensions in the 'extensions' schema from the start.
-- For existing installations, this is informational only - the warning can be acknowledged.

COMMENT ON FUNCTION search_embeddings IS 'Vector similarity search with secure search_path';
COMMENT ON FUNCTION update_updated_at_column IS 'Update timestamp trigger with secure search_path';
COMMENT ON FUNCTION update_knowledge_search_vector IS 'Update search vector with secure search_path';
