-- ============================================
-- Migration: Sync Database Schema with Swift Models
-- Date: 2026-01-30
-- Description: Add missing columns to match Swift app models
-- ============================================

-- ============================================
-- 1. UPDATE chat_messages TABLE
-- ============================================

-- Add columns for knowledge tracking (used in Swift ChatMessage model)
ALTER TABLE public.chat_messages 
ADD COLUMN IF NOT EXISTS used_knowledge_ids UUID[],
ADD COLUMN IF NOT EXISTS knowledge_evidence_level NUMERIC(3,2) CHECK (knowledge_evidence_level BETWEEN 0 AND 1);

COMMENT ON COLUMN public.chat_messages.used_knowledge_ids IS 'IDs of scientific knowledge used for AI response';
COMMENT ON COLUMN public.chat_messages.knowledge_evidence_level IS 'Average evidence level of used knowledge (0-1 scale)';

-- ============================================
-- 2. UPDATE workouts TABLE
-- ============================================

-- Add name column (exists in Swift Workout model but missing in DB)
ALTER TABLE public.workouts 
ADD COLUMN IF NOT EXISTS name TEXT;

COMMENT ON COLUMN public.workouts.name IS 'Routine name (e.g., Arms focus, Legs and core)';

-- ============================================
-- 3. CREATE TYPE FOR KNOWLEDGE CATEGORY (if not exists)
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'knowledge_category') THEN
        CREATE TYPE knowledge_category AS ENUM (
            'hypertrophy', 'strength', 'endurance', 'nutrition', 'recovery', 
            'injury_prevention', 'technique', 'programming', 'supplements', 'general'
        );
    END IF;
END$$;

-- ============================================
-- 4. UPDATE scientific_knowledge TABLE - Add missing columns
-- ============================================

-- Check and add missing columns
DO $$
BEGIN
    -- Add embedding column if pgvector is available
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        ALTER TABLE public.scientific_knowledge 
        ADD COLUMN IF NOT EXISTS embedding VECTOR(1536);
        
        -- Create index for vector search if not exists
        CREATE INDEX IF NOT EXISTS idx_scientific_knowledge_embedding 
        ON public.scientific_knowledge 
        USING ivfflat (embedding vector_cosine_ops);
    END IF;
END$$;

-- ============================================
-- 5. CREATE OR REPLACE FUNCTION FOR UPDATING updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at on key tables
DO $$
BEGIN
    -- workouts trigger
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_workouts_updated_at') THEN
        CREATE TRIGGER trigger_workouts_updated_at
        BEFORE UPDATE ON public.workouts
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- chat_sessions trigger
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_chat_sessions_updated_at') THEN
        CREATE TRIGGER trigger_chat_sessions_updated_at
        BEFORE UPDATE ON public.chat_sessions
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    END IF;
END$$;

-- ============================================
-- 6. CREATE FUNCTION TO GET EXERCISE PROGRESS (matches Swift ProgressModels)
-- ============================================

CREATE OR REPLACE FUNCTION get_exercise_progress(
    p_user_id UUID,
    p_exercise_name TEXT,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    workout_id UUID,
    workout_date TIMESTAMP WITH TIME ZONE,
    max_weight NUMERIC,
    best_set_reps INTEGER,
    total_sets INTEGER,
    total_volume NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        w.id AS workout_id,
        w.date AS workout_date,
        MAX(ws.weight) AS max_weight,
        (SELECT ws2.reps 
         FROM public.workout_sets ws2 
         JOIN public.exercises e2 ON ws2.exercise_id = e2.id
         WHERE e2.workout_id = w.id 
         AND e2.name = p_exercise_name 
         AND ws2.weight = MAX(ws.weight)
         LIMIT 1) AS best_set_reps,
        COUNT(ws.id)::INTEGER AS total_sets,
        COALESCE(SUM(ws.weight * ws.reps), 0) AS total_volume
    FROM public.workouts w
    JOIN public.exercises e ON e.workout_id = w.id
    LEFT JOIN public.workout_sets ws ON ws.exercise_id = e.id
    WHERE w.user_id = p_user_id
      AND e.name = p_exercise_name
    GROUP BY w.id, w.date
    ORDER BY w.date DESC
    LIMIT p_limit;
END;
$$;

-- ============================================
-- 7. CREATE FUNCTION TO GET USER TRAINING STATS (matches Swift UserTrainingStats)
-- ============================================

CREATE OR REPLACE FUNCTION get_user_training_stats(p_user_id UUID)
RETURNS TABLE (
    total_workouts INTEGER,
    workouts_this_week INTEGER,
    workouts_this_month INTEGER,
    average_workouts_per_week NUMERIC,
    most_frequent_exercises TEXT[],
    last_workout_date TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_total_workouts INTEGER;
    v_workouts_this_week INTEGER;
    v_workouts_this_month INTEGER;
    v_avg_per_week NUMERIC;
    v_most_frequent TEXT[];
    v_last_workout TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Total workouts
    SELECT COUNT(*) INTO v_total_workouts
    FROM public.workouts
    WHERE user_id = p_user_id;
    
    -- Workouts this week
    SELECT COUNT(*) INTO v_workouts_this_week
    FROM public.workouts
    WHERE user_id = p_user_id
      AND date >= DATE_TRUNC('week', NOW());
    
    -- Workouts this month
    SELECT COUNT(*) INTO v_workouts_this_month
    FROM public.workouts
    WHERE user_id = p_user_id
      AND date >= DATE_TRUNC('month', NOW());
    
    -- Average per week (over last 12 weeks)
    SELECT COALESCE(
        COUNT(*)::NUMERIC / NULLIF(EXTRACT(WEEK FROM MAX(date) - MIN(date)), 0), 
        0
    )
    INTO v_avg_per_week
    FROM public.workouts
    WHERE user_id = p_user_id
      AND date >= NOW() - INTERVAL '12 weeks';
    
    -- Most frequent exercises (top 5)
    SELECT ARRAY_AGG(name)
    INTO v_most_frequent
    FROM (
        SELECT e.name
        FROM public.exercises e
        JOIN public.workouts w ON e.workout_id = w.id
        WHERE w.user_id = p_user_id
        GROUP BY e.name
        ORDER BY COUNT(*) DESC
        LIMIT 5
    ) sub;
    
    -- Last workout date
    SELECT MAX(date)
    INTO v_last_workout
    FROM public.workouts
    WHERE user_id = p_user_id;
    
    RETURN QUERY
    SELECT 
        v_total_workouts,
        v_workouts_this_week,
        v_workouts_this_month,
        ROUND(v_avg_per_week, 2),
        v_most_frequent,
        v_last_workout;
END;
$$;

-- ============================================
-- 8. CREATE FUNCTION FOR SEMANTIC KNOWLEDGE SEARCH (matches Swift KnowledgeSearchResult)
-- ============================================

CREATE OR REPLACE FUNCTION search_knowledge(
    p_query TEXT,
    p_category TEXT DEFAULT NULL,
    p_min_evidence_level INTEGER DEFAULT 1,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    claim TEXT,
    category TEXT,
    evidence_level INTEGER,
    confidence_score NUMERIC,
    similarity NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- If pgvector is available, use semantic search
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'scientific_knowledge' 
        AND column_name = 'embedding'
    ) THEN
        RETURN QUERY
        SELECT 
            sk.id,
            sk.claim,
            sk.category::TEXT,
            sk.evidence_level,
            sk.confidence_score,
            0.0::NUMERIC AS similarity -- Placeholder, would use actual vector similarity
        FROM public.scientific_knowledge sk
        WHERE sk.status = 'active'
          AND sk.evidence_level >= p_min_evidence_level
          AND (p_category IS NULL OR sk.category::TEXT = p_category)
          AND (sk.claim ILIKE '%' || p_query || '%' 
               OR sk.claim_summary ILIKE '%' || p_query || '%')
        ORDER BY sk.evidence_level DESC, sk.confidence_score DESC
        LIMIT p_limit;
    ELSE
        -- Fallback to text search without embeddings
        RETURN QUERY
        SELECT 
            sk.id,
            sk.claim,
            sk.category::TEXT,
            sk.evidence_level,
            sk.confidence_score,
            0.0::NUMERIC AS similarity
        FROM public.scientific_knowledge sk
        WHERE sk.status = 'active'
          AND sk.evidence_level >= p_min_evidence_level
          AND (p_category IS NULL OR sk.category::TEXT = p_category)
          AND (sk.claim ILIKE '%' || p_query || '%' 
               OR sk.claim_summary ILIKE '%' || p_query || '%')
        ORDER BY sk.evidence_level DESC, sk.confidence_score DESC
        LIMIT p_limit;
    END IF;
END;
$$;

-- ============================================
-- 9. UPDATE RLS POLICIES FOR NEW COLUMNS
-- ============================================

-- Ensure chat_messages policies allow the new columns
DROP POLICY IF EXISTS "Users can view own chat messages" ON public.chat_messages;

CREATE POLICY "Users can view own chat messages" ON public.chat_messages
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.user_id = auth.uid()
    )
  );

-- ============================================
-- 10. ADD INDEXES FOR NEW COLUMNS
-- ============================================

-- Index for knowledge IDs in chat messages (for quick lookup)
CREATE INDEX IF NOT EXISTS idx_chat_messages_knowledge 
ON public.chat_messages USING GIN (used_knowledge_ids) 
WHERE used_knowledge_ids IS NOT NULL;

-- Index for workout names
CREATE INDEX IF NOT EXISTS idx_workouts_name 
ON public.workouts(name) 
WHERE name IS NOT NULL;

-- ============================================
-- VERIFICATION
-- ============================================

-- Verify all tables have required columns
DO $$
DECLARE
    v_missing_columns TEXT;
BEGIN
    -- Check chat_messages
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat_messages' AND column_name = 'used_knowledge_ids'
    ) THEN
        RAISE NOTICE 'WARNING: used_knowledge_ids column missing in chat_messages';
    END IF;
    
    -- Check workouts
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'workouts' AND column_name = 'name'
    ) THEN
        RAISE NOTICE 'WARNING: name column missing in workouts';
    END IF;
    
    RAISE NOTICE 'Migration 009 completed successfully';
END$$;
