-- ============================================================================
-- Migration 002: Integrity Verification for Tool Chains
-- ============================================================================
-- 
-- This migration adds support for package-manager-style integrity verification:
-- 1. Updates resolve_executor_chain to return version, content_hash, and file_hashes
-- 2. Updates resolve_executor_chains_batch similarly
-- 3. Adds index for content_hash lookups
--
-- Date: 2026-01-24
-- ============================================================================

-- ============================================================================
-- PART 1: UPDATE RESOLVE_EXECUTOR_CHAIN FUNCTION
-- ============================================================================
-- 
-- Now returns additional fields needed for integrity verification:
-- - version: The tool version (for lockfile)
-- - content_hash: The integrity hash stored at publish time
-- - file_hashes: JSONB array of {path, sha256, is_executable} for each file

CREATE OR REPLACE FUNCTION resolve_executor_chain(p_tool_id TEXT, p_max_depth INTEGER DEFAULT 10)
RETURNS TABLE (
    depth INTEGER,
    tool_id TEXT,
    version TEXT,
    tool_type TEXT,
    executor_id TEXT,
    manifest JSONB,
    content_hash TEXT,
    file_hashes JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE chain AS (
        -- Start with the requested tool
        SELECT 
            0 AS depth,
            t.tool_id,
            tv.version,
            t.tool_type,
            t.executor_id,
            tv.manifest,
            tv.content_hash,
            (
                SELECT COALESCE(jsonb_agg(jsonb_build_object(
                    'path', tvf.path,
                    'sha256', tvf.sha256,
                    'is_executable', tvf.is_executable
                ) ORDER BY tvf.path), '[]'::jsonb)
                FROM tool_version_files tvf
                WHERE tvf.tool_version_id = tv.id
            ) AS file_hashes
        FROM tools t
        LEFT JOIN tool_versions tv ON tv.tool_id = t.id AND tv.is_latest = true
        WHERE t.tool_id = p_tool_id
        
        UNION ALL
        
        -- Follow executor chain
        SELECT 
            c.depth + 1,
            t.tool_id,
            tv.version,
            t.tool_type,
            t.executor_id,
            tv.manifest,
            tv.content_hash,
            (
                SELECT COALESCE(jsonb_agg(jsonb_build_object(
                    'path', tvf.path,
                    'sha256', tvf.sha256,
                    'is_executable', tvf.is_executable
                ) ORDER BY tvf.path), '[]'::jsonb)
                FROM tool_version_files tvf
                WHERE tvf.tool_version_id = tv.id
            ) AS file_hashes
        FROM chain c
        JOIN tools t ON t.tool_id = c.executor_id
        LEFT JOIN tool_versions tv ON tv.tool_id = t.id AND tv.is_latest = true
        WHERE c.executor_id IS NOT NULL
          AND c.depth < p_max_depth
    )
    SELECT * FROM chain
    ORDER BY chain.depth;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- PART 2: UPDATE RESOLVE_EXECUTOR_CHAINS_BATCH FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION resolve_executor_chains_batch(p_tool_ids TEXT[])
RETURNS TABLE (
    requested_tool_id TEXT,
    depth INTEGER,
    tool_id TEXT,
    version TEXT,
    tool_type TEXT,
    executor_id TEXT,
    manifest JSONB,
    content_hash TEXT,
    file_hashes JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE chain AS (
        SELECT 
            t.tool_id AS requested_tool_id,
            0 AS depth,
            t.tool_id,
            tv.version,
            t.tool_type,
            t.executor_id,
            tv.manifest,
            tv.content_hash,
            (
                SELECT COALESCE(jsonb_agg(jsonb_build_object(
                    'path', tvf.path,
                    'sha256', tvf.sha256,
                    'is_executable', tvf.is_executable
                ) ORDER BY tvf.path), '[]'::jsonb)
                FROM tool_version_files tvf
                WHERE tvf.tool_version_id = tv.id
            ) AS file_hashes
        FROM tools t
        LEFT JOIN tool_versions tv ON tv.tool_id = t.id AND tv.is_latest = true
        WHERE t.tool_id = ANY(p_tool_ids)
        
        UNION ALL
        
        SELECT 
            c.requested_tool_id,
            c.depth + 1,
            t.tool_id,
            tv.version,
            t.tool_type,
            t.executor_id,
            tv.manifest,
            tv.content_hash,
            (
                SELECT COALESCE(jsonb_agg(jsonb_build_object(
                    'path', tvf.path,
                    'sha256', tvf.sha256,
                    'is_executable', tvf.is_executable
                ) ORDER BY tvf.path), '[]'::jsonb)
                FROM tool_version_files tvf
                WHERE tvf.tool_version_id = tv.id
            ) AS file_hashes
        FROM chain c
        JOIN tools t ON t.tool_id = c.executor_id
        LEFT JOIN tool_versions tv ON tv.tool_id = t.id AND tv.is_latest = true
        WHERE c.executor_id IS NOT NULL
          AND c.depth < 10
    )
    SELECT * FROM chain
    ORDER BY chain.requested_tool_id, chain.depth;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- PART 3: ADD INDEX FOR CONTENT_HASH LOOKUPS
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_tool_versions_content_hash 
ON tool_versions(content_hash);

-- ============================================================================
-- PART 4: GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION resolve_executor_chain TO anon, authenticated;
GRANT EXECUTE ON FUNCTION resolve_executor_chains_batch TO anon, authenticated;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- 
-- Test the updated functions:
-- 
-- -- Check that version, content_hash, and file_hashes are returned
-- SELECT tool_id, version, content_hash, file_hashes 
-- FROM resolve_executor_chain('python_runtime');
-- 
-- -- Check batch version
-- SELECT requested_tool_id, tool_id, version, content_hash
-- FROM resolve_executor_chains_batch(ARRAY['data_processor', 'web_scraper']);
