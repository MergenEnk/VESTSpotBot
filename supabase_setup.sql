-- Create the leaderboard table in Supabase
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS leaderboard (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    points INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add an index for faster queries
CREATE INDEX IF NOT EXISTS idx_leaderboard_points ON leaderboard(points DESC);

-- Optional: Add a trigger to auto-update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_leaderboard_updated_at BEFORE UPDATE
    ON leaderboard FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

