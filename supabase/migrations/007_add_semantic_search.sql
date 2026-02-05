-- ============================================
-- Migration: Add Semantic Search Function
-- Date: 2026-01-30
-- Description: Create pgvector function for semantic search
-- ============================================

-- ============================================
-- 1. CREATE SEMANTIC SEARCH FUNCTION
-- ============================================

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
  RETURN QUERY
  SELECT
    sk.id,
    sk.claim,
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

-- ============================================
-- 2. CREATE ALTERNATIVE SEARCH WITH MORE DETAILS
-- ============================================

CREATE OR REPLACE FUNCTION match_scientific_knowledge_detailed(
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
  source_authors TEXT[],
  publication_date DATE,
  study_design TEXT,
  sample_size INTEGER,
  effect_size TEXT,
  key_findings TEXT[],
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
    sk.source_authors,
    sk.publication_date,
    sk.study_design,
    sk.sample_size,
    sk.effect_size,
    sk.key_findings,
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

-- ============================================
-- 3. CREATE HYBRID SEARCH (TEXT + SEMANTIC)
-- ============================================

CREATE OR REPLACE FUNCTION hybrid_search_knowledge(
  query_text TEXT,
  query_embedding VECTOR(1536),
  match_threshold FLOAT DEFAULT 0.5,
  match_count INT DEFAULT 5,
  semantic_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  id UUID,
  claim TEXT,
  category TEXT,
  evidence_level INTEGER,
  confidence_score NUMERIC,
  source_title TEXT,
  semantic_similarity FLOAT,
  text_similarity FLOAT,
  combined_score FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  WITH semantic_scores AS (
    SELECT
      sk.id,
      1 - (sk.embedding <=> query_embedding) AS similarity
    FROM public.scientific_knowledge sk
    WHERE sk.status = 'active'
      AND sk.embedding IS NOT NULL
      AND 1 - (sk.embedding <=> query_embedding) > 0.3
  ),
  text_scores AS (
    SELECT
      sk.id,
      GREATEST(
        similarity(sk.claim, query_text),
        similarity(sk.source_title, query_text),
        COALESCE(similarity(sk.claim_summary, query_text), 0)
      ) AS similarity
    FROM public.scientific_knowledge sk
    WHERE sk.status = 'active'
  ),
  combined AS (
    SELECT
      s.id,
      s.similarity AS semantic_sim,
      COALESCE(t.similarity, 0) AS text_sim,
      (s.similarity * semantic_weight + COALESCE(t.similarity, 0) * (1 - semantic_weight)) AS combined
    FROM semantic_scores s
    LEFT JOIN text_scores t ON s.id = t.id
  )
  SELECT
    sk.id,
    sk.claim,
    sk.category::TEXT,
    sk.evidence_level,
    sk.confidence_score,
    sk.source_title,
    c.semantic_sim AS semantic_similarity,
    c.text_sim AS text_similarity,
    c.combined AS combined_score
  FROM combined c
  JOIN public.scientific_knowledge sk ON sk.id = c.id
  WHERE c.combined > match_threshold
  ORDER BY c.combined DESC
  LIMIT match_count;
END;
$$;

-- ============================================
-- 4. CREATE FUNCTION TO FIND SIMILAR CLAIMS BY ID
-- ============================================

CREATE OR REPLACE FUNCTION find_similar_claims(
  claim_id UUID,
  match_threshold FLOAT DEFAULT 0.8,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  claim TEXT,
  category TEXT,
  evidence_level INTEGER,
  confidence_score NUMERIC,
  source_title TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  target_embedding VECTOR(1536);
BEGIN
  -- Get the embedding of the target claim
  SELECT embedding INTO target_embedding
  FROM public.scientific_knowledge
  WHERE id = claim_id AND status = 'active';
  
  IF target_embedding IS NULL THEN
    RAISE EXCEPTION 'Claim not found or has no embedding: %', claim_id;
  END IF;
  
  -- Find similar claims (excluding the target itself)
  RETURN QUERY
  SELECT
    sk.id,
    sk.claim,
    sk.category::TEXT,
    sk.evidence_level,
    sk.confidence_score,
    sk.source_title,
    1 - (sk.embedding <=> target_embedding) AS similarity
  FROM public.scientific_knowledge sk
  WHERE sk.status = 'active'
    AND sk.embedding IS NOT NULL
    AND sk.id != claim_id
    AND 1 - (sk.embedding <=> target_embedding) > match_threshold
  ORDER BY sk.embedding <=> target_embedding
  LIMIT match_count;
END;
$$;

-- ============================================
-- 5. CREATE INDEX FOR FASTER SEARCH (if not exists)
-- ============================================

-- Note: The pgvector extension must be enabled
-- The vector index should already exist from previous migration

-- Create index on evidence_level for faster filtering
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_evidence_level 
ON public.scientific_knowledge(evidence_level) 
WHERE status = 'active';

-- Create index on category for faster filtering
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_category 
ON public.scientific_knowledge(category) 
WHERE status = 'active';

-- Create composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_active_category 
ON public.scientific_knowledge(status, category, evidence_level) 
WHERE status = 'active';

-- ============================================
-- 6. GRANT PERMISSIONS
-- ============================================

GRANT EXECUTE ON FUNCTION match_scientific_knowledge(VECTOR(1536), FLOAT, INT, TEXT, INT) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION match_scientific_knowledge_detailed(VECTOR(1536), FLOAT, INT, TEXT, INT) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_knowledge(TEXT, VECTOR(1536), FLOAT, INT, FLOAT) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION find_similar_claims(UUID, FLOAT, INT) TO anon, authenticated, service_role;

-- ============================================
-- 7. ADD COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON FUNCTION match_scientific_knowledge IS 'Performs semantic search on scientific knowledge using pgvector cosine similarity';
COMMENT ON FUNCTION match_scientific_knowledge_detailed IS 'Extended version of match_scientific_knowledge with more result fields';
COMMENT ON FUNCTION hybrid_search_knowledge IS 'Combines semantic and text similarity for improved search results';
COMMENT ON FUNCTION find_similar_claims IS 'Finds claims similar to a given claim ID';
