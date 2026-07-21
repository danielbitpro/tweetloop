-- TweetLoop Database Schema Reference
-- This file documents the SQLite schema used by the app.
-- The app creates tables automatically on first run.
-- No manual migration is needed.

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT 'local',
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tweets table
CREATE TABLE IF NOT EXISTS tweets (
    id TEXT PRIMARY KEY,
    user_id TEXT DEFAULT 'local',
    text TEXT NOT NULL,
    label TEXT,
    hashtags TEXT,
    why_it_works TEXT,
    section_number INTEGER,
    status TEXT DEFAULT 'draft',
    schedule_time TEXT,
    posted_at TEXT,
    post_message TEXT,
    source TEXT DEFAULT 'manual',
    source_url TEXT,
    date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id TEXT PRIMARY KEY DEFAULT 'local',
    user_id TEXT DEFAULT 'local',
    key TEXT NOT NULL,
    value TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tweets_status ON tweets(status);
CREATE INDEX IF NOT EXISTS idx_tweets_date ON tweets(date);
CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at DESC);
