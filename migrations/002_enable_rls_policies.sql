-- Enable Row Level Security (RLS) on all tables
-- This replaces the default Supabase policies with proper multi-tenant isolation

-- Step 1: Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tweets ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Step 2: Drop default Supabase policies (too permissive for multi-tenant)
DROP POLICY IF EXISTS "Allow authenticated users full access" ON users;
DROP POLICY IF EXISTS "Allow authenticated users full access" ON api_keys;
DROP POLICY IF EXISTS "Allow authenticated users full access" ON accounts;
DROP POLICY IF EXISTS "Allow authenticated users full access" ON tweets;
DROP POLICY IF EXISTS "Allow authenticated users full access" ON settings;
DROP POLICY IF EXISTS "Allow authenticated users full access" ON analytics;
DROP POLICY IF EXISTS "Allow authenticated users full access" ON pipeline_runs;

DROP POLICY IF EXISTS "Allow public read access" ON users;
DROP POLICY IF EXISTS "Allow public read access" ON api_keys;
DROP POLICY IF EXISTS "Allow public read access" ON accounts;
DROP POLICY IF EXISTS "Allow public read access" ON tweets;
DROP POLICY IF EXISTS "Allow public read access" ON settings;
DROP POLICY IF EXISTS "Allow public read access" ON analytics;
DROP POLICY IF EXISTS "Allow public read access" ON pipeline_runs;

-- Step 3: Create proper per-user policies

-- users table — users can only read/update their own profile
CREATE POLICY "Users can read own profile"
  ON users FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  USING (auth.uid() = id);

-- api_keys table — users can only manage their own API keys
CREATE POLICY "Users can manage own api keys"
  ON api_keys
  USING (auth.uid() = user_id);

-- accounts table — users can only manage their own X accounts
CREATE POLICY "Users can manage own accounts"
  ON accounts
  USING (auth.uid() = user_id);

-- tweets table — users can only manage their own tweets
CREATE POLICY "Users can manage own tweets"
  ON tweets
  USING (auth.uid() = user_id);

-- settings table — users can only manage their own settings
CREATE POLICY "Users can manage own settings"
  ON settings
  USING (auth.uid() = user_id);

-- analytics table — users can only manage their own analytics
CREATE POLICY "Users can manage own analytics"
  ON analytics
  USING (auth.uid() = user_id);

-- pipeline_runs table — users can only manage their own pipeline runs
CREATE POLICY "Users can manage own pipeline runs"
  ON pipeline_runs
  USING (auth.uid() = user_id);
