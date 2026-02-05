-- ============================================
-- Migration: Add AI Coach Feature
-- Date: 2026-01-28
-- Description: Add user profile fields and chat tables
-- ============================================

-- ============================================
-- 1. ALTER TABLE users - Add profile fields
-- ============================================

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS height NUMERIC(5,2);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS weight NUMERIC(5,2);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS gender TEXT CHECK (gender IN ('male', 'female', 'other'));
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS body_fat_percentage NUMERIC(4,2);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS birth_date DATE;

COMMENT ON COLUMN public.users.height IS 'User height in cm';
COMMENT ON COLUMN public.users.weight IS 'User weight in kg';
COMMENT ON COLUMN public.users.gender IS 'User gender (male/female/other)';
COMMENT ON COLUMN public.users.body_fat_percentage IS 'Body fat percentage';
COMMENT ON COLUMN public.users.birth_date IS 'User birth date for age calculation';

-- ============================================
-- 2. CREATE TABLE chat_sessions
-- ============================================

CREATE TABLE IF NOT EXISTS public.chat_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  title TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.chat_sessions IS 'AI Coach chat sessions';

-- ============================================
-- 3. CREATE TABLE chat_messages
-- ============================================

CREATE TABLE IF NOT EXISTS public.chat_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public.chat_messages IS 'Messages within chat sessions';

-- ============================================
-- 4. INDEXES for chat tables
-- ============================================

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON public.chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON public.chat_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON public.chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON public.chat_messages(session_id, created_at);

-- ============================================
-- 5. Enable RLS on new tables
-- ============================================

ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 6. RLS POLICIES - CHAT_SESSIONS
-- ============================================

CREATE POLICY "Users can view own chat sessions" ON public.chat_sessions
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chat sessions" ON public.chat_sessions
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own chat sessions" ON public.chat_sessions
  FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own chat sessions" ON public.chat_sessions
  FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- 7. RLS POLICIES - CHAT_MESSAGES
-- ============================================

CREATE POLICY "Users can view own chat messages" ON public.chat_messages
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert own chat messages" ON public.chat_messages
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete own chat messages" ON public.chat_messages
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.user_id = auth.uid()
    )
  );

-- ============================================
-- 8. TRIGGER for chat_sessions updated_at
-- ============================================

CREATE TRIGGER set_chat_sessions_updated_at
  BEFORE UPDATE ON public.chat_sessions
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

-- ============================================
-- 9. GRANTS for authenticated users
-- ============================================

GRANT ALL ON public.chat_sessions TO authenticated;
GRANT ALL ON public.chat_messages TO authenticated;

-- ============================================
-- END OF MIGRATION
-- ============================================
