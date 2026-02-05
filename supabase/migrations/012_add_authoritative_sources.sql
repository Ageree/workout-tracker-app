-- ============================================
-- Migration: Add Authoritative Sources Tables
-- Date: 2026-02-05
-- Description: Add tables for trusted authors and journals
--              to improve research quality prioritization
-- ============================================

-- ============================================
-- 1. CREATE TABLE trusted_authors
-- ============================================

CREATE TABLE IF NOT EXISTS public.trusted_authors (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  normalized_name TEXT NOT NULL,  -- lowercase, no dots, for matching
  affiliation TEXT,
  lab_name TEXT,
  research_areas TEXT[],
  priority_boost INTEGER DEFAULT 2 CHECK (priority_boost BETWEEN 1 AND 5),
  orcid TEXT,
  h_index INTEGER,
  is_active BOOLEAN DEFAULT true,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.trusted_authors IS 'Authoritative researchers whose work should be prioritized';
COMMENT ON COLUMN public.trusted_authors.normalized_name IS 'Lowercase name without dots for fuzzy matching (e.g., brad schoenfeld)';
COMMENT ON COLUMN public.trusted_authors.priority_boost IS 'Priority boost 1-5, subtracted from default priority (higher = more important)';

-- Index for name matching
CREATE INDEX IF NOT EXISTS idx_trusted_authors_normalized_name ON public.trusted_authors(normalized_name);
CREATE INDEX IF NOT EXISTS idx_trusted_authors_active ON public.trusted_authors(is_active) WHERE is_active = true;

-- ============================================
-- 2. CREATE TABLE trusted_journals
-- ============================================

CREATE TABLE IF NOT EXISTS public.trusted_journals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  short_name TEXT,  -- JSCR, BJSM, etc.
  normalized_name TEXT NOT NULL,  -- lowercase for matching
  issn TEXT,
  eissn TEXT,
  publisher TEXT,
  priority_boost INTEGER DEFAULT 2 CHECK (priority_boost BETWEEN 1 AND 5),
  impact_factor NUMERIC(4,2),
  rss_feed_url TEXT,
  is_active BOOLEAN DEFAULT true,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.trusted_journals IS 'Authoritative journals whose articles should be prioritized';
COMMENT ON COLUMN public.trusted_journals.short_name IS 'Common abbreviation (JSCR, BJSM, JAP)';
COMMENT ON COLUMN public.trusted_journals.normalized_name IS 'Lowercase name for fuzzy matching';
COMMENT ON COLUMN public.trusted_journals.priority_boost IS 'Priority boost 1-5, subtracted from default priority';

-- Indexes for journal matching
CREATE INDEX IF NOT EXISTS idx_trusted_journals_normalized_name ON public.trusted_journals(normalized_name);
CREATE INDEX IF NOT EXISTS idx_trusted_journals_short_name ON public.trusted_journals(short_name);
CREATE INDEX IF NOT EXISTS idx_trusted_journals_issn ON public.trusted_journals(issn);
CREATE INDEX IF NOT EXISTS idx_trusted_journals_active ON public.trusted_journals(is_active) WHERE is_active = true;

-- ============================================
-- 3. ALTER TABLE scientific_knowledge
-- ============================================

-- Add source journal column
ALTER TABLE public.scientific_knowledge
  ADD COLUMN IF NOT EXISTS source_journal TEXT;

-- Add trusted source flag
ALTER TABLE public.scientific_knowledge
  ADD COLUMN IF NOT EXISTS trusted_source BOOLEAN DEFAULT false;

-- Add auto-validated flag
ALTER TABLE public.scientific_knowledge
  ADD COLUMN IF NOT EXISTS auto_validated BOOLEAN DEFAULT false;

-- Add index for trusted sources
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_trusted ON public.scientific_knowledge(trusted_source) WHERE trusted_source = true;

COMMENT ON COLUMN public.scientific_knowledge.source_journal IS 'Journal where the research was published';
COMMENT ON COLUMN public.scientific_knowledge.trusted_source IS 'True if from a trusted author or journal';
COMMENT ON COLUMN public.scientific_knowledge.auto_validated IS 'True if auto-validated based on source trust + evidence level';

-- ============================================
-- 4. ENABLE RLS
-- ============================================

ALTER TABLE public.trusted_authors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trusted_journals ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 5. RLS POLICIES - trusted_authors
-- ============================================

CREATE POLICY "Anyone can view trusted authors" ON public.trusted_authors
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins can modify trusted authors" ON public.trusted_authors
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role = 'admin'
    )
  );

-- ============================================
-- 6. RLS POLICIES - trusted_journals
-- ============================================

CREATE POLICY "Anyone can view trusted journals" ON public.trusted_journals
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins can modify trusted journals" ON public.trusted_journals
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role = 'admin'
    )
  );

-- ============================================
-- 7. FUNCTIONS
-- ============================================

-- Function to check if an author is trusted
CREATE OR REPLACE FUNCTION is_trusted_author(author_name TEXT)
RETURNS TABLE (
  is_trusted BOOLEAN,
  priority_boost INTEGER,
  author_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  normalized TEXT;
BEGIN
  -- Normalize the input name
  normalized := lower(regexp_replace(author_name, '[.]', '', 'g'));
  normalized := trim(normalized);

  RETURN QUERY
  SELECT
    true AS is_trusted,
    ta.priority_boost,
    ta.id AS author_id
  FROM public.trusted_authors ta
  WHERE ta.is_active = true
    AND (
      ta.normalized_name = normalized
      OR normalized LIKE '%' || ta.normalized_name || '%'
      OR ta.normalized_name LIKE '%' || normalized || '%'
    )
  LIMIT 1;

  -- If no match found, return false
  IF NOT FOUND THEN
    RETURN QUERY SELECT false, 0, NULL::UUID;
  END IF;
END;
$$;

-- Function to check if a journal is trusted
CREATE OR REPLACE FUNCTION is_trusted_journal(journal_name TEXT)
RETURNS TABLE (
  is_trusted BOOLEAN,
  priority_boost INTEGER,
  journal_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  normalized TEXT;
BEGIN
  -- Normalize the input name
  normalized := lower(trim(journal_name));

  RETURN QUERY
  SELECT
    true AS is_trusted,
    tj.priority_boost,
    tj.id AS journal_id
  FROM public.trusted_journals tj
  WHERE tj.is_active = true
    AND (
      tj.normalized_name = normalized
      OR lower(tj.short_name) = normalized
      OR normalized LIKE '%' || tj.normalized_name || '%'
      OR tj.normalized_name LIKE '%' || normalized || '%'
    )
  LIMIT 1;

  -- If no match found, return false
  IF NOT FOUND THEN
    RETURN QUERY SELECT false, 0, NULL::UUID;
  END IF;
END;
$$;

-- Function to get all trusted journal names for PubMed search
CREATE OR REPLACE FUNCTION get_trusted_journal_names()
RETURNS TABLE (
  journal_name TEXT,
  short_name TEXT
)
LANGUAGE sql
AS $$
  SELECT name, short_name
  FROM public.trusted_journals
  WHERE is_active = true;
$$;

-- Function to get all trusted author names for PubMed search
CREATE OR REPLACE FUNCTION get_trusted_author_names()
RETURNS TABLE (
  author_name TEXT,
  normalized_name TEXT
)
LANGUAGE sql
AS $$
  SELECT name, normalized_name
  FROM public.trusted_authors
  WHERE is_active = true;
$$;

-- ============================================
-- 8. UPDATE TIMESTAMP TRIGGERS
-- ============================================

CREATE OR REPLACE FUNCTION update_trusted_sources_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER update_trusted_authors_updated_at
  BEFORE UPDATE ON public.trusted_authors
  FOR EACH ROW
  EXECUTE FUNCTION update_trusted_sources_updated_at();

CREATE TRIGGER update_trusted_journals_updated_at
  BEFORE UPDATE ON public.trusted_journals
  FOR EACH ROW
  EXECUTE FUNCTION update_trusted_sources_updated_at();
