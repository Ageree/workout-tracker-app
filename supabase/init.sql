-- ============================================
-- Workout Tracker App - Database Schema
-- ============================================
-- Created: 2026-01-25
-- Description: Complete database schema with RLS policies
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLES
-- ============================================

-- Users table (extends auth.users)
-- Note: Supabase Auth automatically creates auth.users table
-- We create a public.users table for additional user data
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workouts table
-- Stores the main workout sessions
CREATE TABLE IF NOT EXISTS public.workouts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  notes TEXT,
  duration INTEGER, -- Duration in minutes (optional)
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Exercises table
-- Stores individual exercises within a workout
CREATE TABLE IF NOT EXISTS public.exercises (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workout_id UUID NOT NULL REFERENCES public.workouts(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  exercise_order INTEGER NOT NULL, -- Order of exercise in workout
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workout Sets table
-- Stores individual sets for each exercise
CREATE TABLE IF NOT EXISTS public.workout_sets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  exercise_id UUID NOT NULL REFERENCES public.exercises(id) ON DELETE CASCADE,
  set_number INTEGER NOT NULL, -- 1, 2, 3, etc.
  reps INTEGER NOT NULL, -- Number of repetitions
  weight NUMERIC(6,2), -- Weight in kg or lbs (optional)
  rpe INTEGER CHECK (rpe >= 1 AND rpe <= 10), -- Rate of Perceived Exertion (1-10)
  rir INTEGER CHECK (rir >= 0), -- Reps in Reserve (0+)
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
-- Optimize common query patterns

-- Workouts indexes
CREATE INDEX IF NOT EXISTS idx_workouts_user_id ON public.workouts(user_id);
CREATE INDEX IF NOT EXISTS idx_workouts_date ON public.workouts(date DESC);
CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON public.workouts(user_id, date DESC);

-- Exercises indexes
CREATE INDEX IF NOT EXISTS idx_exercises_workout_id ON public.exercises(workout_id);
CREATE INDEX IF NOT EXISTS idx_exercises_workout_order ON public.exercises(workout_id, exercise_order);

-- Sets indexes
CREATE INDEX IF NOT EXISTS idx_sets_exercise_id ON public.workout_sets(exercise_id);
CREATE INDEX IF NOT EXISTS idx_sets_exercise_number ON public.workout_sets(exercise_id, set_number);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_sets ENABLE ROW LEVEL SECURITY;

-- ============================================
-- RLS POLICIES - USERS TABLE
-- ============================================

-- Users can view their own profile
CREATE POLICY "Users can view own profile" ON public.users
  FOR SELECT
  USING (auth.uid() = id);

-- Users can insert their own profile (on signup)
CREATE POLICY "Users can insert own profile" ON public.users
  FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile" ON public.users
  FOR UPDATE
  USING (auth.uid() = id);

-- ============================================
-- RLS POLICIES - WORKOUTS TABLE
-- ============================================

-- Users can view their own workouts
CREATE POLICY "Users can view own workouts" ON public.workouts
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own workouts
CREATE POLICY "Users can insert own workouts" ON public.workouts
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own workouts
CREATE POLICY "Users can update own workouts" ON public.workouts
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can delete their own workouts
CREATE POLICY "Users can delete own workouts" ON public.workouts
  FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- RLS POLICIES - EXERCISES TABLE
-- ============================================

-- Users can view exercises from their own workouts
CREATE POLICY "Users can view own exercises" ON public.exercises
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.workouts
      WHERE workouts.id = exercises.workout_id
      AND workouts.user_id = auth.uid()
    )
  );

-- Users can insert exercises to their own workouts
CREATE POLICY "Users can insert own exercises" ON public.exercises
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.workouts
      WHERE workouts.id = exercises.workout_id
      AND workouts.user_id = auth.uid()
    )
  );

-- Users can update exercises in their own workouts
CREATE POLICY "Users can update own exercises" ON public.exercises
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.workouts
      WHERE workouts.id = exercises.workout_id
      AND workouts.user_id = auth.uid()
    )
  );

-- Users can delete exercises from their own workouts
CREATE POLICY "Users can delete own exercises" ON public.exercises
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.workouts
      WHERE workouts.id = exercises.workout_id
      AND workouts.user_id = auth.uid()
    )
  );

-- ============================================
-- RLS POLICIES - WORKOUT_SETS TABLE
-- ============================================

-- Users can view sets from their own exercises
CREATE POLICY "Users can view own sets" ON public.workout_sets
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.exercises
      JOIN public.workouts ON workouts.id = exercises.workout_id
      WHERE exercises.id = workout_sets.exercise_id
      AND workouts.user_id = auth.uid()
    )
  );

-- Users can insert sets to their own exercises
CREATE POLICY "Users can insert own sets" ON public.workout_sets
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.exercises
      JOIN public.workouts ON workouts.id = exercises.workout_id
      WHERE exercises.id = workout_sets.exercise_id
      AND workouts.user_id = auth.uid()
    )
  );

-- Users can update sets in their own exercises
CREATE POLICY "Users can update own sets" ON public.workout_sets
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.exercises
      JOIN public.workouts ON workouts.id = exercises.workout_id
      WHERE exercises.id = workout_sets.exercise_id
      AND workouts.user_id = auth.uid()
    )
  );

-- Users can delete sets from their own exercises
CREATE POLICY "Users can delete own sets" ON public.workout_sets
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.exercises
      JOIN public.workouts ON workouts.id = exercises.workout_id
      WHERE exercises.id = workout_sets.exercise_id
      AND workouts.user_id = auth.uid()
    )
  );

-- ============================================
-- TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for users table
CREATE TRIGGER set_users_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

-- Trigger for workouts table
CREATE TRIGGER set_workouts_updated_at
  BEFORE UPDATE ON public.workouts
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create user profile on auth.users insert
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- HELPFUL VIEWS (Optional)
-- ============================================

-- View: Complete workout details
CREATE OR REPLACE VIEW public.workout_details AS
SELECT
  w.id as workout_id,
  w.user_id,
  w.date,
  w.notes as workout_notes,
  w.duration,
  e.id as exercise_id,
  e.name as exercise_name,
  e.exercise_order,
  e.notes as exercise_notes,
  s.id as set_id,
  s.set_number,
  s.reps,
  s.weight,
  s.rpe,
  s.rir
FROM public.workouts w
LEFT JOIN public.exercises e ON e.workout_id = w.id
LEFT JOIN public.workout_sets s ON s.exercise_id = e.id
ORDER BY w.date DESC, e.exercise_order, s.set_number;

-- View: Workout summary statistics
CREATE OR REPLACE VIEW public.workout_summary AS
SELECT
  w.id,
  w.user_id,
  w.date,
  w.duration,
  COUNT(DISTINCT e.id) as total_exercises,
  COUNT(s.id) as total_sets,
  SUM(s.reps) as total_reps,
  ROUND(AVG(s.rpe)::numeric, 1) as avg_rpe
FROM public.workouts w
LEFT JOIN public.exercises e ON e.workout_id = w.id
LEFT JOIN public.workout_sets s ON s.exercise_id = e.id
GROUP BY w.id, w.user_id, w.date, w.duration
ORDER BY w.date DESC;

-- ============================================
-- GRANTS
-- ============================================

-- Grant access to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO authenticated;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE public.users IS 'User profiles (extends auth.users)';
COMMENT ON TABLE public.workouts IS 'Workout sessions';
COMMENT ON TABLE public.exercises IS 'Exercises within workouts';
COMMENT ON TABLE public.workout_sets IS 'Individual sets for exercises';

COMMENT ON COLUMN public.workout_sets.rpe IS 'Rate of Perceived Exertion (1-10 scale)';
COMMENT ON COLUMN public.workout_sets.rir IS 'Reps in Reserve (how many more reps could be done)';
COMMENT ON COLUMN public.exercises.exercise_order IS 'Order of exercise in the workout';

-- ============================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================

-- Uncomment below to insert sample data for testing
/*
-- Insert a test user (requires existing auth.users record)
-- INSERT INTO public.users (id, email)
-- VALUES ('00000000-0000-0000-0000-000000000000', 'test@example.com');

-- Insert a sample workout
-- INSERT INTO public.workouts (user_id, date, notes)
-- VALUES ('00000000-0000-0000-0000-000000000000', NOW(), 'Chest day');

-- Insert sample exercises and sets
-- (Add your test data here)
*/

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Verify tables were created
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Verify RLS is enabled
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- Verify policies
-- SELECT * FROM pg_policies WHERE schemaname = 'public';

-- ============================================
-- END OF SCHEMA
-- ============================================
