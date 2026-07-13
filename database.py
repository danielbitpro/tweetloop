"""
Database connection layer for TweetLoop.

Supports two modes:
  1. Supabase PostgreSQL (cloud + local with Supabase)
  2. SQLite (fully offline, no external dependencies)

Mode is selected based on environment variables:
  - SUPABASE_URL + SUPABASE_SERVICE_KEY -> Supabase mode
  - Neither set -> SQLite mode (fallback)

All queries go through a unified interface so app.py doesn't need to know
which backend is active.
"""

import json
import os
import sqlite3
from typing import Any, Optional, List, Dict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY: Optional[str] = os.environ.get("SUPABASE_SERVICE_KEY")
USE_SUPABASE: bool = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

LOCAL_DB_PATH: str = os.path.join(
    os.path.dirname(__file__), "data", "tweetloop.db"
)

# ---------------------------------------------------------------------------
# Supabase client (lazy import — only loaded when needed)
# ---------------------------------------------------------------------------

_supabase_client = None


def get_supabase_client():
    """Lazy-load and cache the Supabase client."""
    global _supabase_client
    if _supabase_client is None and USE_SUPABASE:
        from supabase import create_client, Client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase_client


# ---------------------------------------------------------------------------
# SQLite helpers (for offline / fallback mode)
# ---------------------------------------------------------------------------


def _get_sqlite_connection() -> sqlite3.Connection:
    """Get a SQLite connection, creating the DB and tables if needed."""
    os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_sqlite(conn: sqlite3.Connection) -> None:
    """Create all tables in SQLite if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            subscription_status TEXT DEFAULT 'free',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            is_suspended INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            key_encrypted TEXT NOT NULL,
            secret_encrypted TEXT,
            access_token_encrypted TEXT,
            access_token_secret_encrypted TEXT,
            label TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            x_api_key_encrypted TEXT NOT NULL,
            x_api_secret_encrypted TEXT NOT NULL,
            x_access_token_encrypted TEXT NOT NULL,
            x_access_token_secret_encrypted TEXT NOT NULL,
            x_account_id TEXT,
            account_name TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tweets (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            account_id TEXT REFERENCES accounts(id) ON DELETE SET NULL,
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
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, key)
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            tweet_id TEXT REFERENCES tweets(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            event_count INTEGER DEFAULT 1,
            event_value TEXT,
            recorded_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'running',
            stories_found INTEGER,
            tweets_generated INTEGER,
            tweets_verified INTEGER,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            error_message TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tweets_user_id ON tweets(user_id);
        CREATE INDEX IF NOT EXISTS idx_tweets_status ON tweets(status);
        CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at);
        CREATE INDEX IF NOT EXISTS idx_settings_user_key ON settings(user_id, key);
        CREATE INDEX IF NOT EXISTS idx_analytics_tweet_id ON analytics(tweet_id);
        CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_id ON pipeline_runs(user_id);
        CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
        CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);

        INSERT OR IGNORE INTO users (id, email, full_name)
        VALUES ('00000000-0000-0000-0000-000000000001', 'local@localhost', 'Local User');
    """)


# ---------------------------------------------------------------------------
# Unified query interface
# ---------------------------------------------------------------------------


def select(
    table: str,
    columns: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    fetch_one: bool = False,
) -> Any:
    """
    SELECT query — unified interface for both backends.

    Args:
        table:     Table name
        columns:   List of column names (default: all)
        filters:   Dict of column=value pairs for WHERE clause
        order_by:  ORDER BY clause (e.g., "created_at DESC")
        limit:     LIMIT clause
        offset:    OFFSET clause
        fetch_one: Return single row instead of list

    Returns:
        List of dicts, or single dict if fetch_one=True
    """
    if USE_SUPABASE:
        return _select_supabase(table, columns, filters, order_by, limit, offset, fetch_one)
    else:
        return _select_sqlite(table, columns, filters, order_by, limit, offset, fetch_one)


def insert(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    INSERT query — unified interface for both backends.

    Args:
        table: Table name
        data:  Dict of column=value pairs

    Returns:
        The inserted row (dict)
    """
    if USE_SUPABASE:
        return _insert_supabase(table, data)
    else:
        return _insert_sqlite(table, data)


def update(table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    UPDATE query — unified interface for both backends.

    Args:
        table:   Table name
        data:    Dict of column=value pairs to set
        filters: Dict of column=value pairs for WHERE clause

    Returns:
        The updated row (dict), or None if not found
    """
    if USE_SUPABASE:
        return _update_supabase(table, data, filters)
    else:
        return _update_sqlite(table, data, filters)


def delete(table: str, filters: Dict[str, Any]) -> bool:
    """
    DELETE query — unified interface for both backends.

    Args:
        table:   Table name
        filters: Dict of column=value pairs for WHERE clause

    Returns:
        True if rows were deleted, False otherwise
    """
    if USE_SUPABASE:
        return _delete_supabase(table, filters)
    else:
        return _delete_sqlite(table, filters)


# ---------------------------------------------------------------------------
# Supabase implementation
# ---------------------------------------------------------------------------


def _select_supabase(
    table: str,
    columns: Optional[List[str]],
    filters: Optional[Dict[str, Any]],
    order_by: Optional[str],
    limit: Optional[int],
    offset: Optional[int],
    fetch_one: bool,
) -> Any:
    """Execute SELECT via Supabase PostgREST."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not initialized")

    query = client.table(table).select("*")

    if columns:
        query = client.table(table).select(",".join(columns))

    if filters:
        for col, val in filters.items():
            query = query.eq(col, val)

    if order_by:
        # Parse "created_at DESC" into column and direction
        parts = order_by.strip().split()
        if len(parts) == 2 and parts[1].upper() in ("ASC", "DESC"):
            query = query.order(parts[0], desc=(parts[1].upper() == "DESC"))
        else:
            query = query.order(order_by)

    if limit:
        query = query.limit(limit)

    if offset:
        query = query.range(offset, offset + limit - 1 if limit else None)

    response = query.execute()
    results = response.data if hasattr(response, "data") else []

    if fetch_one:
        return results[0] if results else None
    return results


def _insert_supabase(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute INSERT via Supabase PostgREST."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not initialized")

    response = client.table(table).insert(data).execute()
    results = response.data if hasattr(response, "data") else []
    return results[0] if results else data


def _update_supabase(table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Execute UPDATE via Supabase PostgREST."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not initialized")

    query = client.table(table).update(data)
    for col, val in filters.items():
        query = query.eq(col, val)

    response = query.execute()
    results = response.data if hasattr(response, "data") else []
    return results[0] if results else None


def _delete_supabase(table: str, filters: Dict[str, Any]) -> bool:
    """Execute DELETE via Supabase PostgREST."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not initialized")

    query = client.table(table).delete()
    for col, val in filters.items():
        query = query.eq(col, val)

    response = query.execute()
    # PostgREST returns data (deleted rows) on success, or empty list
    # The response object has a 'data' attribute, not 'status_code'
    if hasattr(response, "data"):
        return len(response.data) > 0
    return True  # No error means success


# ---------------------------------------------------------------------------
# SQLite implementation
# ---------------------------------------------------------------------------


def _select_sqlite(
    table: str,
    columns: Optional[List[str]],
    filters: Optional[Dict[str, Any]],
    order_by: Optional[str],
    limit: Optional[int],
    offset: Optional[int],
    fetch_one: bool,
) -> Any:
    """Execute SELECT against SQLite."""
    conn = _get_sqlite_connection()
    _init_sqlite(conn)

    col_str = ", ".join(columns) if columns else "*"
    query = f"SELECT {col_str} FROM {table}"

    params = []
    if filters:
        where_parts = []
        for col, val in filters.items():
            where_parts.append(f"{col} = ?")
            params.append(val)
        query += " WHERE " + " AND ".join(where_parts)

    if order_by:
        query += f" ORDER BY {order_by}"

    if limit:
        query += f" LIMIT {limit}"

    if offset:
        query += f" OFFSET {offset}"

    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    if fetch_one:
        return results[0] if results else None
    return results


def _insert_sqlite(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute INSERT against SQLite (INSERT OR IGNORE to prevent duplicate key errors)."""
    conn = _get_sqlite_connection()
    _init_sqlite(conn)

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    query = f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})"

    conn.execute(query, list(data.values()))
    conn.commit()

    # Return the inserted row
    last_id = data.get("id")
    if last_id:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (last_id,)).fetchone()
        conn.close()
        return dict(row) if row else data

    conn.close()
    return data


def _update_sqlite(table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Execute UPDATE against SQLite."""
    conn = _get_sqlite_connection()
    _init_sqlite(conn)

    set_parts = ", ".join([f"{col} = ?" for col in data.keys()])
    query = f"UPDATE {table} SET {set_parts}"

    params = list(data.values())
    where_parts = []
    for col, val in filters.items():
        where_parts.append(f"{col} = ?")
        params.append(val)
    query += " WHERE " + " AND ".join(where_parts)

    cursor = conn.execute(query, params)
    conn.commit()

    # Return the updated row
    if "id" in filters:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (filters["id"],)).fetchone()
        conn.close()
        return dict(row) if row else None

    conn.close()
    return {"status": "ok", "rowcount": cursor.rowcount}


def _delete_sqlite(table: str, filters: Dict[str, Any]) -> bool:
    """Execute DELETE against SQLite."""
    conn = _get_sqlite_connection()
    _init_sqlite(conn)

    query = f"DELETE FROM {table}"
    params = []
    where_parts = []
    for col, val in filters.items():
        where_parts.append(f"{col} = ?")
        params.append(val)
    if where_parts:
        query += " WHERE " + " AND ".join(where_parts)

    cursor = conn.execute(query, params)
    conn.commit()
    conn.close()

    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Convenience helpers (tweets)
# ---------------------------------------------------------------------------


def get_user(user_id: str) -> Optional[dict]:
    """Get a user by ID."""
    return select("users", filters={"id": user_id}, fetch_one=True)


def get_tweets(user_id: str, limit: int = 100, offset: int = 0) -> list:
    """Get tweets for a user, ordered by created_at DESC."""
    return select(
        "tweets",
        filters={"user_id": user_id},
        order_by="created_at DESC",
        limit=limit,
        offset=offset,
    )


def get_tweet(user_id: str, tweet_id: str) -> Optional[dict]:
    """Get a single tweet by ID."""
    return select(
        "tweets",
        filters={"id": tweet_id, "user_id": user_id},
        fetch_one=True,
    )


def create_tweet(user_id: str, tweet_data: dict) -> dict:
    """Create a new tweet."""
    return insert("tweets", {
        "id": tweet_data["id"],
        "user_id": user_id,
        "text": tweet_data["text"],
        "label": tweet_data.get("label"),
        "hashtags": tweet_data.get("hashtags"),
        "why_it_works": tweet_data.get("why_it_works"),
        "section_number": tweet_data.get("section_number"),
        "status": tweet_data.get("status", "draft"),
        "schedule_time": tweet_data.get("schedule_time"),
        "source": tweet_data.get("source", "manual"),
        "source_url": tweet_data.get("source_url"),
    })


def update_tweet(user_id: str, tweet_id: str, updates: dict) -> Optional[dict]:
    """Update a tweet. Returns the updated tweet or None if not found."""
    if not updates:
        return get_tweet(user_id, tweet_id)

    # Don't allow changing these fields
    for key in ("id", "user_id", "created_at"):
        updates.pop(key, None)

    result = update(
        "tweets",
        data=updates,
        filters={"id": tweet_id, "user_id": user_id},
    )
    return result


def delete_tweet(user_id: str, tweet_id: str) -> bool:
    """Delete a tweet. Returns True if deleted, False if not found."""
    return delete("tweets", filters={"id": tweet_id, "user_id": user_id})


# ---------------------------------------------------------------------------
# Convenience helpers (settings)
# ---------------------------------------------------------------------------


def get_settings(user_id: str) -> dict:
    """Get all settings for a user."""
    rows = select("settings", filters={"user_id": user_id})
    settings = {}
    for row in rows:
        try:
            settings[row["key"]] = json.loads(row["value"]) if isinstance(row["value"], str) else row["value"]
        except (json.JSONDecodeError, TypeError):
            settings[row["key"]] = row["value"]
    return settings


def save_setting(user_id: str, key: str, value: dict) -> None:
    """Save a setting for a user."""
    value_json = json.dumps(value)
    # Check if setting exists
    existing = select("settings", filters={"user_id": user_id, "key": key}, fetch_one=True)
    if existing:
        update("settings", data={"value": value_json}, filters={"user_id": user_id, "key": key})
    else:
        insert("settings", {
            "user_id": user_id,
            "key": key,
            "value": value_json,
        })


def delete_setting(user_id: str, key: str) -> bool:
    """Delete a setting."""
    return delete("settings", filters={"user_id": user_id, "key": key})


# ---------------------------------------------------------------------------
# Convenience helpers (pipeline runs)
# ---------------------------------------------------------------------------


def create_pipeline_run(user_id: str, run_data: dict) -> dict:
    """Create a pipeline run record."""
    return insert("pipeline_runs", {
        "id": run_data["id"],
        "user_id": user_id,
        "status": run_data.get("status", "running"),
        "stories_found": run_data.get("stories_found"),
        "tweets_generated": run_data.get("tweets_generated"),
        "tweets_verified": run_data.get("tweets_verified"),
        "started_at": run_data.get("started_at"),
        "completed_at": run_data.get("completed_at"),
        "error_message": run_data.get("error_message"),
    })


def update_pipeline_run(run_id: str, updates: dict) -> Optional[dict]:
    """Update a pipeline run."""
    return update("pipeline_runs", data=updates, filters={"id": run_id})


# ---------------------------------------------------------------------------
# Data migration helpers (JSON -> Database)
# ---------------------------------------------------------------------------


def migrate_tweets_from_json(json_path: str) -> int:
    """Migrate tweets from tweets.json into the database."""
    if not os.path.exists(json_path):
        return 0

    with open(json_path, "r") as f:
        tweets = json.load(f)

    if not isinstance(tweets, list):
        return 0

    user_id = "00000000-0000-0000-0000-000000000001"  # local user
    migrated = 0

    for tweet in tweets:
        existing = get_tweet(user_id, tweet.get("id", ""))
        if existing:
            continue

        create_tweet(user_id, {
            "id": tweet.get("id"),
            "text": tweet.get("text", ""),
            "label": tweet.get("label"),
            "hashtags": tweet.get("hashtags"),
            "why_it_works": tweet.get("why_it_works"),
            "section_number": tweet.get("section_number"),
            "status": tweet.get("status", "draft"),
            "schedule_time": tweet.get("schedule_time"),
            "source": tweet.get("source", "manual"),
            "source_url": None,
            "date": tweet.get("date"),
        })
        migrated += 1

    return migrated


def migrate_settings_from_json(json_path: str) -> int:
    """Migrate settings from settings.json into the database."""
    if not os.path.exists(json_path):
        return 0

    with open(json_path, "r") as f:
        settings = json.load(f)

    if not isinstance(settings, dict):
        return 0

    user_id = "00000000-0000-0000-0000-000000000001"  # local user
    migrated = 0

    for key, value in settings.items():
        save_setting(user_id, key, value)
        migrated += 1

    return migrated
