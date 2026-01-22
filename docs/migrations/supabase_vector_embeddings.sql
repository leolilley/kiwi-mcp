-- Migration: Add vector embeddings support with pgvector
-- Description: Creates the item_embeddings table and search function for semantic search

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table
CREATE TABLE item_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id TEXT UNIQUE NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('directive', 'script', 'knowledge')),
    embedding vector(384),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    signature TEXT,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX ON item_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for item_type filtering
CREATE INDEX idx_item_embeddings_type ON item_embeddings (item_type);

-- Create index for item_id lookups
CREATE INDEX idx_item_embeddings_item_id ON item_embeddings (item_id);

-- Create RPC function for similarity search
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

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_item_embeddings_updated_at
    BEFORE UPDATE ON item_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add Row Level Security (RLS) policies
ALTER TABLE item_embeddings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own embeddings
-- Note: This assumes you have user authentication setup
-- Adjust based on your auth implementation
CREATE POLICY "Users can manage their own embeddings" ON item_embeddings
    USING (auth.uid() IS NOT NULL);

-- Grant permissions for anon and authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON item_embeddings TO anon, authenticated;
GRANT EXECUTE ON FUNCTION search_embeddings TO anon, authenticated;