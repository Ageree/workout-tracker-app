-- ============================================
-- Migration: Add Knowledge System for AI Coach
-- Date: 2026-01-30
-- Description: Agent swarm knowledge system tables
-- ============================================

-- ============================================
-- 1. Enable pgvector extension for semantic search
-- ============================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 2. CREATE TABLE research_sources
-- ============================================

CREATE TABLE IF NOT EXISTS public.research_sources (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('pubmed', 'crossref', 'google_scholar', 'arxiv', 'rss_feed', 'manual')),
  base_url TEXT,
  api_key TEXT,
  is_active BOOLEAN DEFAULT true,
  config JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.research_sources IS 'Configuration for research data sources';

-- ============================================
-- 3. CREATE TABLE research_queue
-- ============================================

CREATE TABLE IF NOT EXISTS public.research_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id UUID REFERENCES public.research_sources(id),
  title TEXT NOT NULL,
  authors TEXT[],
  abstract TEXT,
  doi TEXT,
  url TEXT,
  publication_date DATE,
  source_type TEXT NOT NULL CHECK (source_type IN ('pubmed', 'crossref', 'google_scholar', 'arxiv', 'rss_feed', 'manual')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'rejected')),
  priority INTEGER DEFAULT 5,
  raw_data JSONB DEFAULT '{}',
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  processed_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE public.research_queue IS 'Queue of research papers to be processed';

-- ============================================
-- 4. CREATE TABLE scientific_knowledge
-- ============================================

CREATE TABLE IF NOT EXISTS public.scientific_knowledge (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim TEXT NOT NULL,
  claim_summary TEXT,
  category TEXT NOT NULL CHECK (category IN (
    'hypertrophy', 'strength', 'endurance', 'nutrition', 'recovery', 
    'injury_prevention', 'technique', 'programming', 'supplements', 'general'
  )),
  evidence_level INTEGER NOT NULL CHECK (evidence_level BETWEEN 1 AND 5),
  confidence_score NUMERIC(3,2) CHECK (confidence_score BETWEEN 0 AND 1),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'under_review', 'draft')),
  source_doi TEXT,
  source_url TEXT,
  source_title TEXT,
  source_authors TEXT[],
  publication_date DATE,
  sample_size INTEGER,
  study_design TEXT CHECK (study_design IN ('meta_analysis', 'systematic_review', 'rct', 'cohort', 'case_control', 'cross_sectional', 'case_study', 'expert_opinion')),
  population TEXT,
  effect_size TEXT,
  key_findings TEXT[],
  limitations TEXT,
  conflicting_evidence BOOLEAN DEFAULT false,
  embedding VECTOR(1536),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES auth.users(id),
  reviewed_by UUID REFERENCES auth.users(id),
  reviewed_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE public.scientific_knowledge IS 'Core knowledge base of evidence-based fitness claims';

-- ============================================
-- 5. CREATE TABLE evidence_hierarchy
-- ============================================

CREATE TABLE IF NOT EXISTS public.evidence_hierarchy (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  topic TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN (
    'hypertrophy', 'strength', 'endurance', 'nutrition', 'recovery', 
    'injury_prevention', 'technique', 'programming', 'supplements', 'general'
  )),
  aggregated_score NUMERIC(3,2) NOT NULL CHECK (aggregated_score BETWEEN 0 AND 1),
  evidence_count INTEGER NOT NULL DEFAULT 0,
  average_evidence_level NUMERIC(2,1) CHECK (average_evidence_level BETWEEN 1 AND 5),
  strongest_claim_id UUID REFERENCES public.scientific_knowledge(id),
  consensus_level TEXT CHECK (consensus_level IN ('strong', 'moderate', 'weak', 'conflicting')),
  last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.evidence_hierarchy IS 'Aggregated evidence scores by topic';

-- ============================================
-- 6. CREATE TABLE knowledge_relationships
-- ============================================

CREATE TABLE IF NOT EXISTS public.knowledge_relationships (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_knowledge_id UUID NOT NULL REFERENCES public.scientific_knowledge(id) ON DELETE CASCADE,
  target_knowledge_id UUID NOT NULL REFERENCES public.scientific_knowledge(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL CHECK (relationship_type IN ('supports', 'contradicts', 'related_to', 'supersedes', 'prerequisite')),
  strength NUMERIC(2,1) CHECK (strength BETWEEN 0 AND 1),
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(source_knowledge_id, target_knowledge_id, relationship_type)
);

COMMENT ON TABLE public.knowledge_relationships IS 'Graph relationships between knowledge entries';

-- ============================================
-- 7. CREATE TABLE system_prompt_versions
-- ============================================

CREATE TABLE IF NOT EXISTS public.system_prompt_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  version INTEGER NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  prompt_text TEXT NOT NULL,
  is_active BOOLEAN DEFAULT false,
  knowledge_context TEXT,
  included_categories TEXT[],
  min_evidence_level INTEGER CHECK (min_evidence_level BETWEEN 1 AND 5),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES auth.users(id),
  activated_at TIMESTAMP WITH TIME ZONE,
  deactivated_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE public.system_prompt_versions IS 'Versioned system prompts for AI Coach';

-- ============================================
-- 8. CREATE TABLE knowledge_feedback
-- ============================================

CREATE TABLE IF NOT EXISTS public.knowledge_feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  message_id UUID REFERENCES public.chat_messages(id),
  session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  feedback_type TEXT NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down', 'report_inaccurate', 'request_source', 'other')),
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  ai_response TEXT,
  user_query TEXT,
  related_knowledge_ids UUID[],
  is_addressed BOOLEAN DEFAULT false,
  addressed_by UUID REFERENCES auth.users(id),
  addressed_at TIMESTAMP WITH TIME ZONE,
  resolution_notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.knowledge_feedback IS 'User and expert feedback on AI responses';

-- ============================================
-- 9. CREATE TABLE validation_log
-- ============================================

CREATE TABLE IF NOT EXISTS public.validation_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  knowledge_id UUID REFERENCES public.scientific_knowledge(id) ON DELETE CASCADE,
  validator_id UUID REFERENCES auth.users(id),
  validation_type TEXT NOT NULL CHECK (validation_type IN ('initial_review', 'expert_review', 'community_flag', 'automated_check', 'periodic_review')),
  action TEXT NOT NULL CHECK (action IN ('approved', 'rejected', 'flagged', 'deprecated', 'updated')),
  previous_status TEXT,
  new_status TEXT,
  notes TEXT,
  evidence_changes JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.validation_log IS 'Audit trail of all validation activities';

-- ============================================
-- 10. CREATE TABLE knowledge_versions
-- ============================================

CREATE TABLE IF NOT EXISTS public.knowledge_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  knowledge_id UUID NOT NULL REFERENCES public.scientific_knowledge(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  claim TEXT NOT NULL,
  evidence_level INTEGER NOT NULL,
  confidence_score NUMERIC(3,2),
  source_doi TEXT,
  change_summary TEXT,
  changed_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.knowledge_versions IS 'Historical versions of knowledge entries';

-- ============================================
-- 11. INDEXES
-- ============================================

-- Research queue indexes
CREATE INDEX IF NOT EXISTS idx_research_queue_status ON public.research_queue(status);
CREATE INDEX IF NOT EXISTS idx_research_queue_priority ON public.research_queue(priority, created_at);
CREATE INDEX IF NOT EXISTS idx_research_queue_doi ON public.research_queue(doi);

-- Scientific knowledge indexes
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_category ON public.scientific_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_status ON public.scientific_knowledge(status);
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_evidence ON public.scientific_knowledge(evidence_level, confidence_score);
CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_embedding ON public.scientific_knowledge USING ivfflat (embedding vector_cosine_ops);

-- Evidence hierarchy indexes
CREATE INDEX IF NOT EXISTS idx_evidence_hierarchy_topic ON public.evidence_hierarchy(topic);
CREATE INDEX IF NOT EXISTS idx_evidence_hierarchy_category ON public.evidence_hierarchy(category);

-- Knowledge relationships indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_source ON public.knowledge_relationships(source_knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_target ON public.knowledge_relationships(target_knowledge_id);

-- System prompt indexes
CREATE INDEX IF NOT EXISTS idx_system_prompt_versions_active ON public.system_prompt_versions(is_active);

-- Feedback indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_feedback_user ON public.knowledge_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_feedback_session ON public.knowledge_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_feedback_type ON public.knowledge_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_feedback_addressed ON public.knowledge_feedback(is_addressed);

-- Validation log indexes
CREATE INDEX IF NOT EXISTS idx_validation_log_knowledge ON public.validation_log(knowledge_id);
CREATE INDEX IF NOT EXISTS idx_validation_log_created ON public.validation_log(created_at);

-- ============================================
-- 12. ENABLE RLS
-- ============================================

ALTER TABLE public.research_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scientific_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_hierarchy ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_prompt_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.validation_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_versions ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 13. RLS POLICIES - research_sources (admin only for write, read for all)
-- ============================================

CREATE POLICY "Anyone can view research sources" ON public.research_sources
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins can modify research sources" ON public.research_sources
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role = 'admin'
    )
  );

-- ============================================
-- 14. RLS POLICIES - research_queue
-- ============================================

CREATE POLICY "Anyone can view research queue" ON public.research_queue
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins can modify research queue" ON public.research_queue
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role = 'admin'
    )
  );

-- ============================================
-- 15. RLS POLICIES - scientific_knowledge
-- ============================================

CREATE POLICY "Anyone can view active knowledge" ON public.scientific_knowledge
  FOR SELECT
  USING (status = 'active' OR auth.uid() = created_by OR
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

CREATE POLICY "Only admins and experts can modify knowledge" ON public.scientific_knowledge
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

-- ============================================
-- 16. RLS POLICIES - evidence_hierarchy
-- ============================================

CREATE POLICY "Anyone can view evidence hierarchy" ON public.evidence_hierarchy
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins and experts can modify evidence hierarchy" ON public.evidence_hierarchy
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

-- ============================================
-- 17. RLS POLICIES - knowledge_relationships
-- ============================================

CREATE POLICY "Anyone can view knowledge relationships" ON public.knowledge_relationships
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins and experts can modify relationships" ON public.knowledge_relationships
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

-- ============================================
-- 18. RLS POLICIES - system_prompt_versions
-- ============================================

CREATE POLICY "Anyone can view system prompts" ON public.system_prompt_versions
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins can modify system prompts" ON public.system_prompt_versions
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role = 'admin'
    )
  );

-- ============================================
-- 19. RLS POLICIES - knowledge_feedback
-- ============================================

CREATE POLICY "Users can view own feedback" ON public.knowledge_feedback
  FOR SELECT
  USING (user_id = auth.uid() OR
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

CREATE POLICY "Users can create feedback" ON public.knowledge_feedback
  FOR INSERT
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own feedback" ON public.knowledge_feedback
  FOR UPDATE
  USING (user_id = auth.uid());

CREATE POLICY "Admins and experts can address feedback" ON public.knowledge_feedback
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

-- ============================================
-- 20. RLS POLICIES - validation_log
-- ============================================

CREATE POLICY "Anyone can view validation log" ON public.validation_log
  FOR SELECT
  USING (true);

CREATE POLICY "Only admins and experts can create validation entries" ON public.validation_log
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

-- ============================================
-- 21. RLS POLICIES - knowledge_versions
-- ============================================

CREATE POLICY "Anyone can view knowledge versions" ON public.knowledge_versions
  FOR SELECT
  USING (true);

CREATE POLICY "Only system can create knowledge versions" ON public.knowledge_versions
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.users
      WHERE users.id = auth.uid()
      AND users.role IN ('admin', 'expert')
    )
  );

-- ============================================
-- 22. FUNCTIONS
-- ============================================

-- Function to search knowledge by semantic similarity
CREATE OR REPLACE FUNCTION search_knowledge(
  query_embedding VECTOR(1536),
  match_threshold FLOAT,
  match_count INT,
  filter_category TEXT DEFAULT NULL,
  min_evidence_level INT DEFAULT 1
)
RETURNS TABLE (
  id UUID,
  claim TEXT,
  category TEXT,
  evidence_level INTEGER,
  confidence_score NUMERIC,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    sk.id,
    sk.claim,
    sk.category,
    sk.evidence_level,
    sk.confidence_score,
    1 - (sk.embedding <=> query_embedding) AS similarity
  FROM public.scientific_knowledge sk
  WHERE sk.status = 'active'
    AND sk.embedding IS NOT NULL
    AND 1 - (sk.embedding <=> query_embedding) > match_threshold
    AND sk.evidence_level >= min_evidence_level
    AND (filter_category IS NULL OR sk.category = filter_category)
  ORDER BY sk.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Function to get knowledge context for a query
CREATE OR REPLACE FUNCTION get_knowledge_context(
  query_embedding VECTOR(1536),
  max_results INT DEFAULT 5,
  min_evidence_level INT DEFAULT 3
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
  context TEXT := '';
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT
      sk.claim,
      sk.evidence_level,
      sk.confidence_score,
      sk.source_title,
      sk.sample_size,
      sk.study_design
    FROM public.scientific_knowledge sk
    WHERE sk.status = 'active'
      AND sk.embedding IS NOT NULL
      AND sk.evidence_level >= min_evidence_level
    ORDER BY sk.embedding <=> query_embedding
    LIMIT max_results
  LOOP
    context := context || E'\n- ' || rec.claim;
    context := context || E'\n  (Evidence Level: ' || rec.evidence_level || '/5';
    IF rec.confidence_score IS NOT NULL THEN
      context := context || ', Confidence: ' || ROUND(rec.confidence_score::numeric * 100, 1) || '%';
    END IF;
    context := context || ')';
  END LOOP;
  
  RETURN context;
END;
$$;

-- Function to create knowledge version on update
CREATE OR REPLACE FUNCTION create_knowledge_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  max_version INTEGER;
BEGIN
  -- Only create version if significant fields changed
  IF OLD.claim != NEW.claim 
     OR OLD.evidence_level != NEW.evidence_level 
     OR OLD.confidence_score != NEW.confidence_score THEN
    
    -- Get next version number
    SELECT COALESCE(MAX(version), 0) + 1 INTO max_version
    FROM public.knowledge_versions
    WHERE knowledge_id = OLD.id;
    
    -- Insert version record
    INSERT INTO public.knowledge_versions (
      knowledge_id,
      version,
      claim,
      evidence_level,
      confidence_score,
      source_doi,
      change_summary,
      changed_by
    ) VALUES (
      OLD.id,
      max_version,
      OLD.claim,
      OLD.evidence_level,
      OLD.confidence_score,
      OLD.source_doi,
      'Updated via trigger',
      auth.uid()
    );
  END IF;
  
  RETURN NEW;
END;
$$;

-- Trigger for knowledge versioning
CREATE TRIGGER knowledge_version_trigger
  BEFORE UPDATE ON public.scientific_knowledge
  FOR EACH ROW
  EXECUTE FUNCTION create_knowledge_version();

-- Function to get active system prompt
CREATE OR REPLACE FUNCTION get_active_system_prompt()
RETURNS TABLE (
  id UUID,
  version INTEGER,
  name TEXT,
  prompt_text TEXT,
  knowledge_context TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    spv.id,
    spv.version,
    spv.name,
    spv.prompt_text,
    spv.knowledge_context
  FROM public.system_prompt_versions spv
  WHERE spv.is_active = true
  ORDER BY spv.version DESC
  LIMIT 1;
END;
$$;

-- Function to update evidence hierarchy
CREATE OR REPLACE FUNCTION update_evidence_hierarchy(p_topic TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
  v_avg_evidence NUMERIC;
  v_count INTEGER;
  v_strongest_id UUID;
  v_category TEXT;
BEGIN
  -- Get category from first matching knowledge
  SELECT category INTO v_category
  FROM public.scientific_knowledge
  WHERE claim ILIKE '%' || p_topic || '%'
    AND status = 'active'
  LIMIT 1;
  
  -- Calculate aggregated metrics
  SELECT
    AVG(evidence_level),
    COUNT(*),
    (SELECT id FROM public.scientific_knowledge 
     WHERE claim ILIKE '%' || p_topic || '%' 
       AND status = 'active'
     ORDER BY evidence_level DESC, confidence_score DESC 
     LIMIT 1)
  INTO v_avg_evidence, v_count, v_strongest_id
  FROM public.scientific_knowledge
  WHERE claim ILIKE '%' || p_topic || '%'
    AND status = 'active';
  
  -- Insert or update hierarchy
  INSERT INTO public.evidence_hierarchy (
    topic, category, aggregated_score, evidence_count, 
    average_evidence_level, strongest_claim_id, last_updated
  )
  VALUES (
    p_topic, 
    v_category, 
    COALESCE(v_avg_evidence / 5.0, 0),
    v_count,
    v_avg_evidence,
    v_strongest_id,
    NOW()
  )
  ON CONFLICT (topic) DO UPDATE SET
    aggregated_score = EXCLUDED.aggregated_score,
    evidence_count = EXCLUDED.evidence_count,
    average_evidence_level = EXCLUDED.average_evidence_level,
    strongest_claim_id = EXCLUDED.strongest_claim_id,
    last_updated = NOW();
END;
$$;

-- ============================================
-- 23. SEED DATA - Initial System Prompt
-- ============================================

INSERT INTO public.system_prompt_versions (
  version,
  name,
  description,
  prompt_text,
  is_active,
  knowledge_context,
  included_categories,
  min_evidence_level
) VALUES (
  1,
  'Initial Knowledge-Based Coach',
  'First version with scientific knowledge integration',
  E'Ты — тренер по силовым видам спорта с 10+ годами практики. Специализация: гипертрофия, развитие силы, техника базовых движений.

Ты базируешь свои ответы на научных исследованиях. Используй предоставленный контекст знаний для формирования ответов.

ПРАВИЛА ОТВЕТОВ:

1. Начинай сразу с сути. Никаких вступлений типа "Отличный вопрос!" или "Рад помочь!".

2. Давай конкретику: проценты от 1RM, диапазоны повторений, названия упражнений. Избегай общих фраз вроде "постепенно увеличивай нагрузку".

3. Используй данные клиента. Если видишь его тренировки — анализируй их. Если нет данных — спроси.

4. Формат: короткие абзацы. Списки только если перечисляешь упражнения программы.

5. Без эмодзи, без восклицательных знаков в каждом предложении, без мотивационных клише ("Ты справишься!", "Верю в тебе!").

6. Если вопрос вне твоей компетенции (травмы, медицина) — скажи прямо и порекомендуй специалиста.

7. Отвечай на том же языке, на котором написано последнее сообщение пользователя.

8. Не используй звёздочки (*) и markdown-форматирование в ответах. Пиши простым текстом без какого-либо форматирования.

9. Если научный консенсус отсутствует или есть противоречивые данные — скажи об этом прямо.',
  true,
  'Base prompt without specific knowledge context - will be enhanced dynamically',
  ARRAY['hypertrophy', 'strength', 'nutrition', 'recovery', 'technique', 'programming'],
  3
);
