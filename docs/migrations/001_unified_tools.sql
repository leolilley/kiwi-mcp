-- Migration: Unified Tools with Executor Chain
-- Description: Create unified tools system with "only two primitives" architecture
-- Date: 2026-01-23
-- Version: 1.0.0
--
-- PHILOSOPHY: Only two primitives are hard-coded (subprocess, http_client).
-- Everything else (runtimes, MCP servers, scripts, APIs) is configuration
-- stored in the tools table, resolved via executor chains.
--
-- COEXISTENCE: Old tables (scripts, directives, knowledge_entries) remain 
-- untouched. New system runs alongside until migration is verified.

-- ============================================================================
-- PART 0: EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Vector extension deferred until embeddings are needed
-- CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- ============================================================================
-- PART 1: TOOLS TABLE (Unified Entity)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    tool_id TEXT NOT NULL,                -- Stable identifier (e.g., "subprocess", "python_runtime", "enrich_emails")
    namespace TEXT DEFAULT 'public',       -- For future multi-tenancy
    name TEXT,                             -- Human-readable display name
    
    -- Classification
    tool_type TEXT NOT NULL,               -- See constraint below
    category TEXT,                         -- User-defined category
    subcategory TEXT,
    tags TEXT[] DEFAULT '{}',
    
    -- Executor Chain (THE KEY INNOVATION)
    executor_id TEXT,                      -- References another tool's tool_id
                                           -- NULL only for primitives
                                           -- Creates execution chain: script → runtime → primitive
    
    -- Builtin Marker
    is_builtin BOOLEAN DEFAULT false,      -- True for primitives and core runtimes (protected from deletion)
    
    -- Metadata
    description TEXT,
    author_id UUID,                        -- References users(id) if needed
    is_official BOOLEAN DEFAULT false,
    visibility TEXT DEFAULT 'public',
    
    -- Stats
    download_count INTEGER DEFAULT 0,
    quality_score NUMERIC(3,2),
    success_rate NUMERIC(3,2),
    total_executions INTEGER DEFAULT 0,
    avg_execution_time NUMERIC,
    estimated_cost_usd NUMERIC(10,4),
    
    -- Versioning
    latest_version TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT tools_tool_type_check CHECK (tool_type IN (
        -- PRIMITIVES: Hard-coded execution (only these two!)
        'primitive',
        
        -- RUNTIMES: Execute code using primitives
        'runtime',
        
        -- MCP: External tool servers
        'mcp_server',    -- Server connection config (uses subprocess primitive)
        'mcp_tool',      -- Individual tool from an MCP server
        
        -- USER TOOLS: Scripts and APIs
        'script',        -- Executable code (uses a runtime)
        'api'            -- HTTP API call (uses http_client primitive)
    )),
    
    CONSTRAINT tools_visibility_check CHECK (visibility IN ('public', 'unlisted', 'private')),
    
    -- Non-primitives MUST have an executor
    CONSTRAINT tools_executor_required CHECK (
        tool_type = 'primitive' OR executor_id IS NOT NULL
    ),
    
    UNIQUE (namespace, tool_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tools_tool_id ON tools (tool_id);
CREATE INDEX IF NOT EXISTS idx_tools_executor_id ON tools (executor_id);
CREATE INDEX IF NOT EXISTS idx_tools_tool_type ON tools (tool_type);
CREATE INDEX IF NOT EXISTS idx_tools_category ON tools (category);
CREATE INDEX IF NOT EXISTS idx_tools_is_builtin ON tools (is_builtin) WHERE is_builtin = true;

-- Full-text search (add if needed)
-- ALTER TABLE tools ADD COLUMN IF NOT EXISTS search_vector tsvector 
--     GENERATED ALWAYS AS (
--         setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
--         setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
--         setweight(to_tsvector('english', coalesce(tool_id, '')), 'A')
--     ) STORED;
-- CREATE INDEX IF NOT EXISTS idx_tools_search ON tools USING gin(search_vector);

-- ============================================================================
-- PART 2: TOOL VERSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS tool_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    version TEXT NOT NULL,                 -- Semver string
    
    -- Manifest: The complete configuration for this version
    -- Contains: executor_config, parameters, validation rules, etc.
    manifest JSONB NOT NULL,
    manifest_yaml TEXT,                    -- Original YAML for round-trip fidelity
    
    -- Integrity
    content_hash TEXT NOT NULL,            -- SHA256 of canonical content
    
    -- Metadata
    changelog TEXT,
    is_latest BOOLEAN DEFAULT false,
    deprecated BOOLEAN DEFAULT false,
    deprecation_message TEXT,
    
    -- Timestamps
    published_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (tool_id, version)
);

CREATE INDEX IF NOT EXISTS idx_tool_versions_tool_id ON tool_versions (tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_versions_is_latest ON tool_versions (is_latest) WHERE is_latest = true;

-- ============================================================================
-- PART 3: TOOL VERSION FILES TABLE (Multi-file support)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tool_version_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_version_id UUID NOT NULL REFERENCES tool_versions(id) ON DELETE CASCADE,
    
    -- File identity
    path TEXT NOT NULL,                    -- e.g., 'main.py', 'requirements.txt', 'tool.yaml'
    media_type TEXT,                       -- MIME type
    
    -- Content (choose one)
    content_text TEXT,                     -- For text files < 64KB
    storage_key TEXT,                      -- Supabase Storage key for larger files
    
    -- Integrity
    sha256 TEXT NOT NULL,
    size_bytes INTEGER,
    
    -- Metadata
    is_executable BOOLEAN DEFAULT false,   -- Marks entrypoint files
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (tool_version_id, path)
);

CREATE INDEX IF NOT EXISTS idx_tool_version_files_version ON tool_version_files (tool_version_id);

-- ============================================================================
-- PART 4: SEED PRIMITIVES (The only two hard-coded executors)
-- ============================================================================

-- These are the ONLY tools with executor_id = NULL
-- All other tools MUST reference one of these (directly or via chain)

INSERT INTO tools (tool_id, name, tool_type, executor_id, is_builtin, is_official, description, latest_version)
VALUES 
    ('subprocess', 'Subprocess Primitive', 'primitive', NULL, true, true,
     'Spawns and manages OS processes. Handles stdin/stdout/stderr, signals, timeouts.', '1.0.0'),
    ('http_client', 'HTTP Client Primitive', 'primitive', NULL, true, true,
     'Makes HTTP/HTTPS requests. Handles streaming, retries, authentication.', '1.0.0')
ON CONFLICT (namespace, tool_id) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Seed primitive manifests in tool_versions
INSERT INTO tool_versions (tool_id, version, manifest, content_hash, is_latest)
SELECT 
    t.id,
    '1.0.0',
    CASE t.tool_id
        WHEN 'subprocess' THEN jsonb_build_object(
            'tool_id', 'subprocess',
            'tool_type', 'primitive',
            'version', '1.0.0',
            'description', 'Subprocess execution primitive',
            'config_schema', jsonb_build_object(
                'type', 'object',
                'properties', jsonb_build_object(
                    'command', jsonb_build_object('type', 'string', 'description', 'Command to execute'),
                    'args', jsonb_build_object('type', 'array', 'items', jsonb_build_object('type', 'string')),
                    'env', jsonb_build_object('type', 'object', 'additionalProperties', jsonb_build_object('type', 'string')),
                    'cwd', jsonb_build_object('type', 'string'),
                    'timeout', jsonb_build_object('type', 'integer', 'default', 300),
                    'capture_output', jsonb_build_object('type', 'boolean', 'default', true)
                ),
                'required', jsonb_build_array('command')
            )
        )
        WHEN 'http_client' THEN jsonb_build_object(
            'tool_id', 'http_client',
            'tool_type', 'primitive',
            'version', '1.0.0',
            'description', 'HTTP client primitive',
            'config_schema', jsonb_build_object(
                'type', 'object',
                'properties', jsonb_build_object(
                    'method', jsonb_build_object('type', 'string', 'enum', jsonb_build_array('GET', 'POST', 'PUT', 'PATCH', 'DELETE')),
                    'url', jsonb_build_object('type', 'string', 'description', 'URL or URL template with {param} placeholders'),
                    'headers', jsonb_build_object('type', 'object'),
                    'body', jsonb_build_object('type', 'object'),
                    'timeout', jsonb_build_object('type', 'integer', 'default', 30),
                    'retry', jsonb_build_object('type', 'object', 'properties', jsonb_build_object(
                        'max_attempts', jsonb_build_object('type', 'integer', 'default', 3),
                        'backoff', jsonb_build_object('type', 'string', 'default', 'exponential')
                    ))
                ),
                'required', jsonb_build_array('method', 'url')
            )
        )
    END,
    md5(t.tool_id),
    true
FROM tools t
WHERE t.tool_type = 'primitive'
ON CONFLICT (tool_id, version) DO NOTHING;

-- ============================================================================
-- PART 5: SEED CORE RUNTIMES
-- ============================================================================

-- Python Runtime (uses subprocess)
INSERT INTO tools (tool_id, name, tool_type, executor_id, is_builtin, is_official, description, latest_version)
VALUES 
    ('python_runtime', 'Python Runtime', 'runtime', 'subprocess', true, true,
     'Executes Python scripts with venv support, dependency installation, and environment management.', '1.0.0'),
    ('bash_runtime', 'Bash Runtime', 'runtime', 'subprocess', true, true,
     'Executes shell scripts with proper error handling and environment.', '1.0.0'),
    ('node_runtime', 'Node.js Runtime', 'runtime', 'subprocess', true, true,
     'Executes Node.js/TypeScript scripts with npm dependency support.', '1.0.0')
ON CONFLICT (namespace, tool_id) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Seed runtime manifests
INSERT INTO tool_versions (tool_id, version, manifest, content_hash, is_latest)
SELECT 
    t.id,
    '1.0.0',
    CASE t.tool_id
        WHEN 'python_runtime' THEN jsonb_build_object(
            'tool_id', 'python_runtime',
            'tool_type', 'runtime',
            'version', '1.0.0',
            'executor', 'subprocess',
            'description', 'Python execution runtime',
            'config', jsonb_build_object(
                'command', 'python3',
                'venv', jsonb_build_object(
                    'enabled', true,
                    'path', '.venv',
                    'auto_create', true
                ),
                'install_deps', true,
                'python_path_includes', jsonb_build_array('.')
            ),
            'config_schema', jsonb_build_object(
                'type', 'object',
                'properties', jsonb_build_object(
                    'entrypoint', jsonb_build_object('type', 'string', 'default', 'main.py'),
                    'requirements', jsonb_build_object('type', 'array', 'items', jsonb_build_object('type', 'string')),
                    'env', jsonb_build_object('type', 'object')
                )
            )
        )
        WHEN 'bash_runtime' THEN jsonb_build_object(
            'tool_id', 'bash_runtime',
            'tool_type', 'runtime',
            'version', '1.0.0',
            'executor', 'subprocess',
            'description', 'Bash execution runtime',
            'config', jsonb_build_object(
                'command', 'bash',
                'args', jsonb_build_array('-e', '-o', 'pipefail')
            )
        )
        WHEN 'node_runtime' THEN jsonb_build_object(
            'tool_id', 'node_runtime',
            'tool_type', 'runtime',
            'version', '1.0.0',
            'executor', 'subprocess',
            'description', 'Node.js execution runtime',
            'config', jsonb_build_object(
                'command', 'node',
                'package_manager', 'npm',
                'install_deps', true
            )
        )
    END,
    md5(t.tool_id),
    true
FROM tools t
WHERE t.tool_id IN ('python_runtime', 'bash_runtime', 'node_runtime')
ON CONFLICT (tool_id, version) DO NOTHING;

-- ============================================================================
-- PART 6: SEED MCP SERVERS AS TOOLS
-- ============================================================================

-- MCP servers are tools that use subprocess to spawn MCP server processes
INSERT INTO tools (tool_id, name, tool_type, executor_id, is_builtin, is_official, category, description, latest_version)
VALUES 
    ('mcp_supabase', 'Supabase MCP Server', 'mcp_server', 'subprocess', true, true, 'database',
     'Supabase MCP server for database operations', '1.0.0'),
    ('mcp_github', 'GitHub MCP Server', 'mcp_server', 'subprocess', true, true, 'version-control',
     'GitHub MCP server for repository operations', '1.0.0'),
    ('mcp_filesystem', 'Filesystem MCP Server', 'mcp_server', 'subprocess', true, true, 'files',
     'Filesystem MCP server for file operations', '1.0.0'),
    ('mcp_postgres', 'Postgres MCP Server', 'mcp_server', 'subprocess', true, true, 'database',
     'Direct Postgres MCP server', '1.0.0'),
    ('mcp_slack', 'Slack MCP Server', 'mcp_server', 'subprocess', true, true, 'communication',
     'Slack MCP server for messaging', '1.0.0')
ON CONFLICT (namespace, tool_id) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Seed MCP server manifests
INSERT INTO tool_versions (tool_id, version, manifest, content_hash, is_latest)
SELECT 
    t.id,
    '1.0.0',
    CASE t.tool_id
        WHEN 'mcp_supabase' THEN jsonb_build_object(
            'tool_id', 'mcp_supabase',
            'tool_type', 'mcp_server',
            'version', '1.0.0',
            'executor', 'subprocess',
            'description', 'Supabase MCP server',
            'config', jsonb_build_object(
                'transport', 'stdio',
                'command', 'npx',
                'args', jsonb_build_array('-y', '@supabase/mcp-server-supabase@latest'),
                'env', jsonb_build_object(
                    'SUPABASE_ACCESS_TOKEN', '${SUPABASE_ACCESS_TOKEN}'
                )
            )
        )
        WHEN 'mcp_github' THEN jsonb_build_object(
            'tool_id', 'mcp_github',
            'tool_type', 'mcp_server',
            'version', '1.0.0',
            'executor', 'subprocess',
            'config', jsonb_build_object(
                'transport', 'stdio',
                'command', 'npx',
                'args', jsonb_build_array('-y', '@modelcontextprotocol/server-github'),
                'env', jsonb_build_object('GITHUB_TOKEN', '${GITHUB_TOKEN}')
            )
        )
        WHEN 'mcp_filesystem' THEN jsonb_build_object(
            'tool_id', 'mcp_filesystem',
            'tool_type', 'mcp_server',
            'version', '1.0.0',
            'executor', 'subprocess',
            'config', jsonb_build_object(
                'transport', 'stdio',
                'command', 'npx',
                'args', jsonb_build_array('-y', '@modelcontextprotocol/server-filesystem')
            )
        )
        WHEN 'mcp_postgres' THEN jsonb_build_object(
            'tool_id', 'mcp_postgres',
            'tool_type', 'mcp_server',
            'version', '1.0.0',
            'executor', 'subprocess',
            'config', jsonb_build_object(
                'transport', 'stdio',
                'command', 'npx',
                'args', jsonb_build_array('-y', '@modelcontextprotocol/server-postgres'),
                'env', jsonb_build_object('DATABASE_URL', '${DATABASE_URL}')
            )
        )
        WHEN 'mcp_slack' THEN jsonb_build_object(
            'tool_id', 'mcp_slack',
            'tool_type', 'mcp_server',
            'version', '1.0.0',
            'executor', 'subprocess',
            'config', jsonb_build_object(
                'transport', 'stdio',
                'command', 'npx',
                'args', jsonb_build_array('-y', '@modelcontextprotocol/server-slack'),
                'env', jsonb_build_object('SLACK_BOT_TOKEN', '${SLACK_BOT_TOKEN}')
            )
        )
    END,
    md5(t.tool_id),
    true
FROM tools t
WHERE t.tool_id LIKE 'mcp_%'
ON CONFLICT (tool_id, version) DO NOTHING;

-- ============================================================================
-- PART 7: EXECUTOR CHAIN RESOLUTION FUNCTION
-- ============================================================================

-- Resolves the complete executor chain for a tool
-- Returns array of tool_ids from leaf to primitive
-- Example: ['enrich_emails', 'python_runtime', 'subprocess']

CREATE OR REPLACE FUNCTION resolve_executor_chain(p_tool_id TEXT, p_max_depth INTEGER DEFAULT 10)
RETURNS TABLE (
    depth INTEGER,
    tool_id TEXT,
    tool_type TEXT,
    executor_id TEXT,
    manifest JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE chain AS (
        -- Start with the requested tool
        SELECT 
            0 AS depth,
            t.tool_id,
            t.tool_type,
            t.executor_id,
            tv.manifest
        FROM tools t
        LEFT JOIN tool_versions tv ON tv.tool_id = t.id AND tv.is_latest = true
        WHERE t.tool_id = p_tool_id
        
        UNION ALL
        
        -- Follow executor chain
        SELECT 
            c.depth + 1,
            t.tool_id,
            t.tool_type,
            t.executor_id,
            tv.manifest
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

-- Batch version for multiple tools (avoids N+1)
CREATE OR REPLACE FUNCTION resolve_executor_chains_batch(p_tool_ids TEXT[])
RETURNS TABLE (
    requested_tool_id TEXT,
    depth INTEGER,
    tool_id TEXT,
    tool_type TEXT,
    executor_id TEXT,
    manifest JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE chain AS (
        SELECT 
            t.tool_id AS requested_tool_id,
            0 AS depth,
            t.tool_id,
            t.tool_type,
            t.executor_id,
            tv.manifest
        FROM tools t
        LEFT JOIN tool_versions tv ON tv.tool_id = t.id AND tv.is_latest = true
        WHERE t.tool_id = ANY(p_tool_ids)
        
        UNION ALL
        
        SELECT 
            c.requested_tool_id,
            c.depth + 1,
            t.tool_id,
            t.tool_type,
            t.executor_id,
            tv.manifest
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
-- PART 8: TOOL SEARCH FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION search_tools(
    p_query TEXT,
    p_tool_type TEXT DEFAULT NULL,
    p_category TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    tool_id TEXT,
    name TEXT,
    tool_type TEXT,
    category TEXT,
    description TEXT,
    executor_id TEXT,
    latest_version TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.tool_id,
        t.name,
        t.tool_type,
        t.category,
        t.description,
        t.executor_id,
        t.latest_version,
        ts_rank(
            to_tsvector('english', coalesce(t.name, '') || ' ' || coalesce(t.description, '') || ' ' || coalesce(t.tool_id, '')),
            plainto_tsquery('english', p_query)
        ) AS rank
    FROM tools t
    WHERE 
        (p_tool_type IS NULL OR t.tool_type = p_tool_type)
        AND (p_category IS NULL OR t.category = p_category)
        AND (
            p_query IS NULL 
            OR p_query = ''
            OR to_tsvector('english', coalesce(t.name, '') || ' ' || coalesce(t.description, '') || ' ' || coalesce(t.tool_id, ''))
               @@ plainto_tsquery('english', p_query)
            OR t.tool_id ILIKE '%' || p_query || '%'
            OR t.name ILIKE '%' || p_query || '%'
        )
    ORDER BY rank DESC, t.download_count DESC NULLS LAST
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- PART 9: RLS POLICIES
-- ============================================================================

ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_version_files ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Public read access" ON tools FOR SELECT USING (true);
CREATE POLICY "Public read access" ON tool_versions FOR SELECT USING (true);
CREATE POLICY "Public read access" ON tool_version_files FOR SELECT USING (true);

-- Authenticated write access (but protect builtins)
CREATE POLICY "Authenticated write non-builtin" ON tools
    FOR ALL USING (auth.role() = 'authenticated' AND NOT is_builtin);

CREATE POLICY "Authenticated write versions" ON tool_versions
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated write files" ON tool_version_files
    FOR ALL USING (auth.role() = 'authenticated');

-- Grant permissions
GRANT SELECT ON tools TO anon, authenticated;
GRANT SELECT ON tool_versions TO anon, authenticated;
GRANT SELECT ON tool_version_files TO anon, authenticated;

GRANT INSERT, UPDATE, DELETE ON tools TO authenticated;
GRANT INSERT, UPDATE, DELETE ON tool_versions TO authenticated;
GRANT INSERT, UPDATE, DELETE ON tool_version_files TO authenticated;

GRANT EXECUTE ON FUNCTION resolve_executor_chain TO anon, authenticated;
GRANT EXECUTE ON FUNCTION resolve_executor_chains_batch TO anon, authenticated;
GRANT EXECUTE ON FUNCTION search_tools TO anon, authenticated;

-- ============================================================================
-- PART 10: UPDATED_AT TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_tools_updated_at ON tools;
CREATE TRIGGER update_tools_updated_at
    BEFORE UPDATE ON tools
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these to verify migration:
-- 
-- -- Check primitives seeded
-- SELECT tool_id, tool_type, executor_id FROM tools WHERE tool_type = 'primitive';
-- 
-- -- Check runtimes seeded
-- SELECT tool_id, tool_type, executor_id FROM tools WHERE tool_type = 'runtime';
-- 
-- -- Check MCP servers seeded
-- SELECT tool_id, tool_type, executor_id FROM tools WHERE tool_type = 'mcp_server';
-- 
-- -- Test executor chain resolution
-- SELECT * FROM resolve_executor_chain('python_runtime');
-- SELECT * FROM resolve_executor_chain('mcp_supabase');
-- 
-- -- Test batch resolution
-- SELECT * FROM resolve_executor_chains_batch(ARRAY['python_runtime', 'mcp_github']);
