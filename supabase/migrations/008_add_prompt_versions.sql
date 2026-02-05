-- Migration: Add system prompt versions table
-- Creates table for storing versioned system prompts

-- Create system_prompt_versions table
CREATE TABLE IF NOT EXISTS system_prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    version INTEGER NOT NULL,
    knowledge_snapshot JSONB NOT NULL,
    performance_score NUMERIC(4,3), -- 0.000 to 1.000
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Ensure unique version per category
    UNIQUE(category, version)
);

-- Index for fast lookup of active prompts
CREATE INDEX IF NOT EXISTS idx_prompt_versions_active 
ON system_prompt_versions(category, is_active) 
WHERE is_active = TRUE;

-- Index for getting latest version
CREATE INDEX IF NOT EXISTS idx_prompt_versions_category_version 
ON system_prompt_versions(category, version DESC);

-- Function to get active prompt for category
CREATE OR REPLACE FUNCTION get_active_system_prompt(
    p_category TEXT
)
RETURNS TABLE (
    id UUID,
    prompt_text TEXT,
    version INTEGER,
    knowledge_snapshot JSONB,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        spv.id,
        spv.prompt_text,
        spv.version,
        spv.knowledge_snapshot,
        spv.created_at
    FROM system_prompt_versions spv
    WHERE spv.category = p_category
      AND spv.is_active = TRUE
    ORDER BY spv.version DESC
    LIMIT 1;
END;
$$;

-- Function to get prompt by category and version
CREATE OR REPLACE FUNCTION get_system_prompt_version(
    p_category TEXT,
    p_version INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    prompt_text TEXT,
    version INTEGER,
    knowledge_snapshot JSONB,
    is_active BOOLEAN,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF p_version IS NULL THEN
        -- Return latest version
        RETURN QUERY
        SELECT 
            spv.id,
            spv.prompt_text,
            spv.version,
            spv.knowledge_snapshot,
            spv.is_active,
            spv.created_at
        FROM system_prompt_versions spv
        WHERE spv.category = p_category
        ORDER BY spv.version DESC
        LIMIT 1;
    ELSE
        -- Return specific version
        RETURN QUERY
        SELECT 
            spv.id,
            spv.prompt_text,
            spv.version,
            spv.knowledge_snapshot,
            spv.is_active,
            spv.created_at
        FROM system_prompt_versions spv
        WHERE spv.category = p_category
          AND spv.version = p_version;
    END IF;
END;
$$;

-- Function to activate a prompt version (deactivates others)
CREATE OR REPLACE FUNCTION activate_prompt_version(
    p_prompt_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_category TEXT;
BEGIN
    -- Get category for the prompt
    SELECT category INTO v_category
    FROM system_prompt_versions
    WHERE id = p_prompt_id;
    
    IF v_category IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Deactivate all prompts in category
    UPDATE system_prompt_versions
    SET is_active = FALSE
    WHERE category = v_category;
    
    -- Activate specified prompt
    UPDATE system_prompt_versions
    SET is_active = TRUE
    WHERE id = p_prompt_id;
    
    RETURN TRUE;
END;
$$;

-- RLS Policies
ALTER TABLE system_prompt_versions ENABLE ROW LEVEL SECURITY;

-- Allow read access to all authenticated users
CREATE POLICY "Allow read access to prompt versions"
ON system_prompt_versions
FOR SELECT
TO authenticated
USING (TRUE);

-- Allow insert/update only to service role
CREATE POLICY "Allow service role to manage prompts"
ON system_prompt_versions
FOR ALL
TO service_role
USING (TRUE)
WITH CHECK (TRUE);
