-- Supabase Table Setup for Spotted Leaderboard
-- Run this in your Supabase SQL Editor

-- Create the scores table
CREATE TABLE IF NOT EXISTS scores (
    user_id TEXT PRIMARY KEY,
    user_name TEXT,
    score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create an index on score for faster leaderboard queries
CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations (adjust based on your security needs)
-- For a bot that needs full access, you can use the service role key
-- or create a permissive policy for the anon key
CREATE POLICY "Enable all access for authenticated users" ON scores
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Optional: Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update updated_at
CREATE TRIGGER update_scores_updated_at
    BEFORE UPDATE ON scores
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

