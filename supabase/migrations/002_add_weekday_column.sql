-- Add weekday column to workouts table
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS weekday TEXT;
