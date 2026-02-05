-- ============================================
-- Migration: Add Function to Generate Embeddings
-- Date: 2026-01-30
-- Description: Function to generate embeddings via OpenAI API
-- ============================================

-- ============================================
-- 1. CREATE FUNCTION TO GENERATE EMBEDDINGS
-- ============================================

-- Note: This function requires pg_net extension or similar for HTTP requests
-- In production, embeddings should be generated via application layer
-- This is a placeholder for future implementation

CREATE OR REPLACE FUNCTION generate_embedding_for_claim(claim_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  claim_text TEXT;
BEGIN
  -- Get the claim text
  SELECT claim INTO claim_text
  FROM public.scientific_knowledge
  WHERE id = claim_id;
  
  IF claim_text IS NULL THEN
    RAISE EXCEPTION 'Claim not found: %', claim_id;
  END IF;
  
  -- Note: In production, you would call OpenAI API here
  -- For now, this is a placeholder that logs the action
  -- Actual implementation would use pg_net or similar extension
  
  RAISE NOTICE 'Would generate embedding for claim: %', LEFT(claim_text, 50);
  
  -- Update the claim with a placeholder embedding (zeros)
  -- In production, this would be the actual embedding from OpenAI
  UPDATE public.scientific_knowledge
  SET embedding = (SELECT array_agg(0.0)::vector(1536) FROM generate_series(1, 1536))
  WHERE id = claim_id;
  
END;
$$;

-- ============================================
-- 2. CREATE FUNCTION TO BATCH GENERATE EMBEDDINGS
-- ============================================

CREATE OR REPLACE FUNCTION generate_embeddings_for_all_missing()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  claim_record RECORD;
  processed_count INTEGER := 0;
BEGIN
  FOR claim_record IN
    SELECT id, claim
    FROM public.scientific_knowledge
    WHERE embedding IS NULL
      AND status = 'active'
    LIMIT 100 -- Process in batches
  LOOP
    -- In production, this would call OpenAI API
    -- For now, using placeholder
    UPDATE public.scientific_knowledge
    SET embedding = (SELECT array_agg(random() * 2 - 1)::vector(1536) FROM generate_series(1, 1536))
    WHERE id = claim_record.id;
    
    processed_count := processed_count + 1;
    
    -- Add small delay to avoid overwhelming the system
    PERFORM pg_sleep(0.1);
  END LOOP;
  
  RETURN processed_count;
END;
$$;

-- ============================================
-- 3. CREATE TRIGGER TO AUTO-GENERATE EMBEDDINGS
-- ============================================

-- Note: In production, this should be handled by application layer
-- to avoid blocking database operations

CREATE OR REPLACE FUNCTION auto_generate_embedding()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  -- Only generate if embedding is null and claim is active
  IF NEW.embedding IS NULL AND NEW.status = 'active' THEN
    -- Schedule embedding generation (placeholder)
    -- In production, this would queue a job or call an external service
    NEW.embedding := (SELECT array_agg(random() * 2 - 1)::vector(1536) FROM generate_series(1, 1536));
  END IF;
  
  RETURN NEW;
END;
$$;

-- Create trigger (commented out by default - enable if needed)
-- CREATE TRIGGER auto_embedding_trigger
--   BEFORE INSERT OR UPDATE ON public.scientific_knowledge
--   FOR EACH ROW
--   EXECUTE FUNCTION auto_generate_embedding();

-- ============================================
-- 4. CREATE FUNCTION TO SEARCH WITHOUT EMBEDDINGS (FALLBACK)
-- ============================================

CREATE OR REPLACE FUNCTION search_knowledge_text(
  query_text TEXT,
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
  relevance_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    sk.id,
    sk.claim,
    sk.category::TEXT,
    sk.evidence_level,
    sk.confidence_score,
    -- Simple text relevance scoring
    CASE
      WHEN sk.claim ILIKE '%' || query_text || '%' THEN 1.0
      WHEN sk.claim ILIKE '%' || REPLACE(query_text, ' ', '%') || '%' THEN 0.8
      WHEN sk.category::TEXT ILIKE '%' || query_text || '%' THEN 0.6
      WHEN sk.key_findings::TEXT ILIKE '%' || query_text || '%' THEN 0.5
      ELSE 0.1
    END::FLOAT as relevance_score
  FROM public.scientific_knowledge sk
  WHERE sk.status = 'active'
    AND sk.evidence_level >= min_evidence_level
    AND (filter_category IS NULL OR sk.category = filter_category)
    AND (
      sk.claim ILIKE '%' || query_text || '%'
      OR sk.category::TEXT ILIKE '%' || query_text || '%'
      OR sk.key_findings::TEXT ILIKE '%' || query_text || '%'
    )
  ORDER BY relevance_score DESC, sk.evidence_level DESC
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION search_knowledge_text IS 'Fallback text search for knowledge when embeddings are not available';
