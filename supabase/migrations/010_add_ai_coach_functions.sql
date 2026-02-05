-- ============================================
-- Migration: Add AI Coach Functions
-- Date: 2026-01-31
-- Description: SQL functions for AI Coach with Agent Swarm integration
-- ============================================

-- ============================================
-- 1. ADD EMBEDDING STATUS COLUMN
-- ============================================

-- Add embedding_status column for tracking embedding generation
ALTER TABLE public.scientific_knowledge 
ADD COLUMN IF NOT EXISTS embedding_status TEXT 
DEFAULT 'pending' 
CHECK (embedding_status IN ('pending', 'processing', 'completed', 'failed'));

-- Add error_message column for tracking embedding failures
ALTER TABLE public.scientific_knowledge 
ADD COLUMN IF NOT EXISTS embedding_error TEXT;

COMMENT ON COLUMN public.scientific_knowledge.embedding_status IS 'Status of embedding generation: pending, processing, completed, failed';
COMMENT ON COLUMN public.scientific_knowledge.embedding_error IS 'Error message if embedding generation failed';

-- ============================================
-- 2. CREATE TRIGGER FUNCTION FOR EMBEDDING STATUS
-- ============================================

CREATE OR REPLACE FUNCTION trigger_set_embedding_pending()
RETURNS TRIGGER AS $$
BEGIN
    -- If embedding is null or being reset, set status to pending
    IF NEW.embedding IS NULL THEN
        NEW.embedding_status = 'pending';
        NEW.embedding_error = NULL;
    -- If embedding is being set, mark as completed
    ELSIF OLD.embedding IS NULL AND NEW.embedding IS NOT NULL THEN
        NEW.embedding_status = 'completed';
        NEW.embedding_error = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS auto_update_embedding ON public.scientific_knowledge;

-- Create trigger
CREATE TRIGGER auto_update_embedding
    BEFORE INSERT OR UPDATE ON public.scientific_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_embedding_pending();

COMMENT ON FUNCTION trigger_set_embedding_pending() IS 'Automatically sets embedding_status based on embedding column';

-- ============================================
-- 3. CREATE FUNCTION: match_knowledge_vectors
-- ============================================

-- Updated semantic search function with claim_summary
CREATE OR REPLACE FUNCTION match_knowledge_vectors(
  query_embedding VECTOR(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5,
  filter_category TEXT DEFAULT NULL,
  min_evidence_level INT DEFAULT 1
)
RETURNS TABLE (
  id UUID,
  claim TEXT,
  claim_summary TEXT,
  category TEXT,
  evidence_level INTEGER,
  confidence_score NUMERIC,
  source_title TEXT,
  source_doi TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    sk.id,
    sk.claim,
    sk.claim_summary,
    sk.category::TEXT,
    sk.evidence_level,
    sk.confidence_score,
    sk.source_title,
    sk.source_doi,
    1 - (sk.embedding <=> query_embedding) AS similarity
  FROM public.scientific_knowledge sk
  WHERE sk.status = 'active'
    AND sk.embedding IS NOT NULL
    AND sk.evidence_level >= min_evidence_level
    AND (filter_category IS NULL OR sk.category::TEXT = filter_category)
    AND 1 - (sk.embedding <=> query_embedding) > match_threshold
  ORDER BY sk.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_knowledge_vectors(VECTOR(1536), FLOAT, INT, TEXT, INT) IS 
'Semantic search over scientific knowledge using vector similarity. Returns claims with similarity scores.';

-- ============================================
-- 4. CREATE FUNCTION: get_knowledge_context
-- ============================================

CREATE OR REPLACE FUNCTION get_knowledge_context(
  query_text TEXT,
  max_results INT DEFAULT 5,
  min_evidence_level INT DEFAULT 2
)
RETURNS TABLE (
  context_text TEXT,
  knowledge_ids UUID[],
  avg_evidence_level NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_context_text TEXT := '';
  v_knowledge_ids UUID[] := ARRAY[]::UUID[];
  v_avg_evidence NUMERIC;
  v_total_evidence INTEGER := 0;
  v_count INTEGER := 0;
  rec RECORD;
BEGIN
  -- Find relevant knowledge using text search
  FOR rec IN
    SELECT
      sk.id,
      sk.claim,
      sk.claim_summary,
      sk.evidence_level,
      sk.confidence_score,
      sk.source_title,
      sk.study_design
    FROM public.scientific_knowledge sk
    WHERE sk.status = 'active'
      AND sk.evidence_level >= min_evidence_level
      AND (
        sk.claim ILIKE '%' || query_text || '%'
        OR sk.claim_summary ILIKE '%' || query_text || '%'
      )
    ORDER BY 
      sk.evidence_level DESC,
      sk.confidence_score DESC
    LIMIT max_results
  LOOP
    -- Build context text
    v_context_text := v_context_text || E'\n---\n';
    v_context_text := v_context_text || 'Claim: ' || rec.claim || E'\n';
    
    IF rec.claim_summary IS NOT NULL THEN
      v_context_text := v_context_text || 'Summary: ' || rec.claim_summary || E'\n';
    END IF;
    
    v_context_text := v_context_text || 'Evidence Level: ' || rec.evidence_level || '/5';
    
    IF rec.source_title IS NOT NULL THEN
      v_context_text := v_context_text || E'\nSource: ' || rec.source_title;
    END IF;
    
    IF rec.study_design IS NOT NULL THEN
      v_context_text := v_context_text || E'\nStudy Design: ' || rec.study_design;
    END IF;
    
    -- Collect IDs
    v_knowledge_ids := array_append(v_knowledge_ids, rec.id);
    
    -- Calculate average evidence level
    v_total_evidence := v_total_evidence + rec.evidence_level;
    v_count := v_count + 1;
  END LOOP;
  
  -- Calculate average
  IF v_count > 0 THEN
    v_avg_evidence := v_total_evidence::NUMERIC / v_count;
  ELSE
    v_avg_evidence := 0;
  END IF;
  
  RETURN QUERY SELECT v_context_text, v_knowledge_ids, v_avg_evidence;
END;
$$;

COMMENT ON FUNCTION get_knowledge_context(TEXT, INT, INT) IS 
'Retrieves combined knowledge context for AI system prompt based on text query. Returns formatted context, knowledge IDs, and average evidence level.';

-- ============================================
-- 5. CREATE FUNCTION: save_message_knowledge
-- ============================================

CREATE OR REPLACE FUNCTION save_message_knowledge(
  p_message_id UUID,
  p_knowledge_ids UUID[],
  p_evidence_level NUMERIC
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE public.chat_messages
  SET 
    used_knowledge_ids = p_knowledge_ids,
    knowledge_evidence_level = p_evidence_level,
    updated_at = NOW()
  WHERE id = p_message_id;
  
  RETURN FOUND;
END;
$$;

COMMENT ON FUNCTION save_message_knowledge(UUID, UUID[], NUMERIC) IS 
'Saves the relationship between a chat message and the scientific knowledge used to generate it.';

-- ============================================
-- 6. CREATE FUNCTION: get_relevant_knowledge_for_query
-- ============================================

CREATE OR REPLACE FUNCTION get_relevant_knowledge_for_query(
  query_text TEXT,
  max_results INT DEFAULT 5,
  min_evidence_level INT DEFAULT 2,
  filter_categories TEXT[] DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  claim TEXT,
  claim_summary TEXT,
  category TEXT,
  evidence_level INTEGER,
  confidence_score NUMERIC,
  source_title TEXT,
  source_authors TEXT[],
  publication_date DATE,
  sample_size INTEGER,
  study_design TEXT,
  key_findings TEXT[]
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    sk.id,
    sk.claim,
    sk.claim_summary,
    sk.category::TEXT,
    sk.evidence_level,
    sk.confidence_score,
    sk.source_title,
    sk.source_authors,
    sk.publication_date,
    sk.sample_size,
    sk.study_design::TEXT,
    sk.key_findings
  FROM public.scientific_knowledge sk
  WHERE sk.status = 'active'
    AND sk.evidence_level >= min_evidence_level
    AND (filter_categories IS NULL OR sk.category::TEXT = ANY(filter_categories))
    AND (
      sk.claim ILIKE '%' || query_text || '%'
      OR sk.claim_summary ILIKE '%' || query_text || '%'
    )
  ORDER BY 
    sk.evidence_level DESC,
    sk.confidence_score DESC
  LIMIT max_results;
END;
$$;

COMMENT ON FUNCTION get_relevant_knowledge_for_query(TEXT, INT, INT, TEXT[]) IS 
'Returns full scientific knowledge records relevant to a query for UI display.';

-- ============================================
-- 7. CREATE FUNCTION: get_pending_embeddings
-- ============================================

CREATE OR REPLACE FUNCTION get_pending_embeddings(
  max_results INT DEFAULT 10
)
RETURNS TABLE (
  id UUID,
  claim TEXT,
  claim_summary TEXT,
  category TEXT,
  evidence_level INTEGER,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Update status to processing for selected records
  RETURN QUERY
  WITH selected AS (
    SELECT sk.id
    FROM public.scientific_knowledge sk
    WHERE sk.embedding_status = 'pending'
      AND sk.status = 'active'
    ORDER BY sk.created_at ASC
    LIMIT max_results
    FOR UPDATE SKIP LOCKED
  )
  UPDATE public.scientific_knowledge sk
  SET embedding_status = 'processing'
  FROM selected
  WHERE sk.id = selected.id
  RETURNING 
    sk.id,
    sk.claim,
    sk.claim_summary,
    sk.category::TEXT,
    sk.evidence_level,
    sk.created_at;
END;
$$;

COMMENT ON FUNCTION get_pending_embeddings(INT) IS 
'Atomically fetches and locks pending embeddings for processing by KB Agent. Returns records with processing status.';

-- ============================================
-- 8. CREATE FUNCTION: update_embedding_status
-- ============================================

CREATE OR REPLACE FUNCTION update_embedding_status(
  p_claim_id UUID,
  p_embedding VECTOR(1536),
  p_status TEXT DEFAULT 'completed'
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE public.scientific_knowledge
  SET 
    embedding = p_embedding,
    embedding_status = p_status,
    embedding_error = CASE WHEN p_status = 'failed' THEN 'Failed to generate embedding' ELSE NULL END,
    updated_at = NOW()
  WHERE id = p_claim_id;
  
  RETURN FOUND;
END;
$$;

COMMENT ON FUNCTION update_embedding_status(UUID, VECTOR(1536), TEXT) IS 
'Updates embedding and status for a claim. Used by KB Agent after embedding generation.';

-- ============================================
-- 9. CREATE INDEXES (without pg_trgm)
-- ============================================

-- Index for embedding status (used by KB Agent)
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_embedding_status 
ON public.scientific_knowledge(embedding_status) 
WHERE embedding_status = 'pending';

-- Composite index for active knowledge filtering
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_active 
ON public.scientific_knowledge(status, evidence_level, category) 
WHERE status = 'active';

-- Index for category filtering
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_category 
ON public.scientific_knowledge(category, evidence_level DESC, confidence_score DESC)
WHERE status = 'active';

-- ============================================
-- 10. CREATE OR REPLACE LEGACY FUNCTIONS (Backward Compatibility)
-- ============================================

-- Keep existing match_scientific_knowledge as alias
CREATE OR REPLACE FUNCTION match_scientific_knowledge(
  query_embedding VECTOR(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5,
  filter_category TEXT DEFAULT NULL,
  min_evidence_level INT DEFAULT 1
)
RETURNS TABLE (
  id UUID,
  claim TEXT,
  category TEXT,
  evidence_level INTEGER,
  confidence_score NUMERIC,
  source_title TEXT,
  source_doi TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Call the new function (without claim_summary for backward compatibility)
  RETURN QUERY
  SELECT 
    mkv.id,
    mkv.claim,
    mkv.category,
    mkv.evidence_level,
    mkv.confidence_score,
    mkv.source_title,
    mkv.source_doi,
    mkv.similarity
  FROM match_knowledge_vectors(
    query_embedding,
    match_threshold,
    match_count,
    filter_category,
    min_evidence_level
  ) mkv;
END;
$$;

COMMENT ON FUNCTION match_scientific_knowledge(VECTOR(1536), FLOAT, INT, TEXT, INT) IS 
'Legacy function for backward compatibility. Delegates to match_knowledge_vectors.';

-- ============================================
-- 11. ENABLE ROW LEVEL SECURITY FOR NEW FUNCTIONS
-- ============================================

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION match_knowledge_vectors(VECTOR(1536), FLOAT, INT, TEXT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_knowledge_context(TEXT, INT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION save_message_knowledge(UUID, UUID[], NUMERIC) TO authenticated;
GRANT EXECUTE ON FUNCTION get_relevant_knowledge_for_query(TEXT, INT, INT, TEXT[]) TO authenticated;

-- Service role only functions (for Agent Swarm)
GRANT EXECUTE ON FUNCTION get_pending_embeddings(INT) TO service_role;
GRANT EXECUTE ON FUNCTION update_embedding_status(UUID, VECTOR(1536), TEXT) TO service_role;

-- ============================================
-- Migration Complete
-- ============================================
