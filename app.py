"""
TweetLoop — Flask backend for the TweetLoop dashboard.

Dual auth:
  - Supabase JWT (when SUPABASE_URL is set)
  - Password from .env (when SUPABASE_URL is NOT set)

Database:
  - Supabase PostgreSQL (when SUPABASE_URL is set)
  - SQLite fallback (when SUPABASE_URL is NOT set)
"""

import json
import os
import subprocess
import uuid
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session

from database import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    get_tweets as db_get_tweets,
    get_tweet as db_get_tweet,
    create_tweet as db_create_tweet,
    update_tweet as db_update_tweet,
    delete_tweet as db_delete_tweet,
    get_settings as db_get_settings,
    save_setting as db_save_setting,
    migrate_tweets_from_json,
    migrate_settings_from_json,
)

from auth import (
    require_auth,
    login_endpoint,
    logout_endpoint,
    status_endpoint,
    PASSWORD_HASH,
    USE_PASSWORD_AUTH,
    SUPABASE_URL as AUTH_SUPABASE_URL,
    SUPABASE_SERVICE_KEY as AUTH_SUPABASE_SERVICE_KEY,
    get_password,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

XURL_PATH = os.path.expanduser('~/.local/bin/xurl')

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

PORT = int(os.environ.get('PORT', 7777))

# Determine auth/database mode
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

# Default settings (fallback when DB is empty)
DEFAULT_SETTINGS = {
    "app": {
        "theme": "dark",
        "password": "",
        "remember_login": True,
        "auto_refresh_interval": 5,
        "max_tweets_per_page": 50,
        "date_format": "YYYY-MM-DD",
    },
    "research": {
        "sources": {
            "twitter": True,
            "arxiv": False,
            "github_trending": False,
            "reddit": False,
            "huggingface": False,
            "youtube": False,
            "tech_blogs": False,
        },
        "keywords": [],
        "language": "en",
        "date_range": "24h",
        "manual_url_check": False,
        "manual_urls": [],
        "reddit_subreddits": ["LocalLLaMA", "LocalLLM", "opensourceAI", "MachineLearning"],
        "max_stories": 15,
        "max_proposals": 10,
        "source_quotas": {
            "twitter": 0, "arxiv": 0, "github_trending": 0,
            "reddit": 0, "huggingface": 0, "youtube": 0, "tech_blogs": 0,
        },
    },
    "copywriter": {
        "instructions": "Write concise, engaging tweets about local AI, LLMs, and AI agents. Focus on practical insights, tutorials, and news.",
        "tone": "technical",
        "max_hashtags": 3,
        "include_why_it_works": True,
        "max_characters": 280,
    },
    "export": {
        "default_format": "pipeline",
        "filename_pattern": "tweets-{date}",
        "csv_fields": ["id", "label", "text", "hashtags", "status", "schedule_time", "source", "date"],
    },
    "pipeline": {
        "cron_schedule": "0 5 * * *",
        "max_tweets_per_cycle": 20,
        "deduplication_threshold": 0.8,
        "source_priority": ["twitter", "arxiv", "github_trending", "reddit", "huggingface", "youtube", "tech_blogs"],
        "language_filter": "en",
    },
}

# ---------------------------------------------------------------------------
# Startup: migrate existing JSON data to database
# ---------------------------------------------------------------------------

@app.before_request
def _migrate_on_startup():
    """Migrate JSON files to database on first startup."""
    if not USE_SUPABASE:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        tweets_json = os.path.join(data_dir, 'tweets.json')
        settings_json = os.path.join(data_dir, 'settings.json')
        
        migrated_tweets = migrate_tweets_from_json(tweets_json)
        migrated_settings = migrate_settings_from_json(settings_json)
        
        if migrated_tweets or migrated_settings:
            print(f"[TweetLoop] Migrated {migrated_tweets} tweets, {migrated_settings} settings to database")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/settings')
@require_auth
def settings_page():
    return render_template('settings.html')


# --- Auth ---

@app.route('/api/login', methods=['POST'])
def login():
    return login_endpoint()


@app.route('/api/logout', methods=['POST'])
def logout():
    return logout_endpoint()


@app.route('/api/status')
def status():
    return status_endpoint()


# --- Tweets ---

@app.route('/api/tweets', methods=['GET'])
@require_auth
def get_tweets():
    user_id = request.user_id
    tweets = db_get_tweets(user_id, limit=500)
    
    # Group by date for frontend
    grouped = {}
    for tweet in tweets:
        date = tweet.get('date') or tweet.get('created_at', 'unknown')[:10]  # YYYY-MM-DD
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(tweet)
    
    # Sort dates descending
    sorted_tweets = {}
    for date in sorted(grouped.keys(), reverse=True):
        sorted_tweets[date] = sorted(
            grouped[date],
            key=lambda x: (x.get('section_number') or 0, x.get('id', ''))
        )
    
    return jsonify(sorted_tweets)


@app.route('/api/tweets', methods=['POST'])
@require_auth
def add_tweet():
    user_id = request.user_id
    data = request.json
    
    new_tweet = {
        'id': str(uuid.uuid4()),
        'text': data.get('text', ''),
        'label': data.get('label'),
        'hashtags': data.get('hashtags'),
        'why_it_works': data.get('why_it_works'),
        'section_number': data.get('section_number'),
        'status': 'draft',
        'schedule_time': data.get('schedule_time'),
        'source': data.get('source', 'manual'),
        'source_url': None,
    }
    
    result = db_create_tweet(user_id, new_tweet)
    # The DB returns the inserted row; merge with our data for the response
    response_tweet = {**new_tweet, **result[0]} if isinstance(result, list) and result else new_tweet
    
    return jsonify(response_tweet), 201


@app.route('/api/tweets/<tweet_id>', methods=['PUT'])
@require_auth
def update_tweet(tweet_id):
    user_id = request.user_id
    updates = request.json
    
    result = db_update_tweet(user_id, tweet_id, updates)
    if not result:
        return jsonify({'error': 'Tweet not found'}), 404
    
    return jsonify(result)


@app.route('/api/tweets/<tweet_id>', methods=['DELETE'])
@require_auth
def delete_tweet(tweet_id):
    user_id = request.user_id
    success = db_delete_tweet(user_id, tweet_id)
    if not success:
        return jsonify({'error': 'Tweet not found'}), 404
    
    return jsonify({'status': 'deleted'})


# --- Post to X ---

def post_tweet_via_xurl(tweet_text):
    """Post a tweet using xurl CLI. Returns (success, message)."""
    escaped_text = tweet_text.replace("'", "'\\\\''")
    cmd = [XURL_PATH, '--app', 'twitter', '--auth', 'oauth1', 'post', escaped_text]
    env = os.environ.copy()
    env['PATH'] = os.path.expanduser('~/.local/bin') + ':' + env.get('PATH', '')
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        if result.returncode == 0:
            return True, 'Posted successfully'
        else:
            stderr = result.stderr.strip()[:500]
            return False, f'xurl error: {stderr}'
    except subprocess.TimeoutExpired:
        return False, 'xurl timed out after 30s'
    except FileNotFoundError:
        return False, f'xurl not found at {XURL_PATH}'
    except Exception as e:
        return False, f'xurl error: {str(e)}'


@app.route('/api/tweets/<tweet_id>/post', methods=['POST'])
@require_auth
def post_tweet(tweet_id):
    """Post a tweet to X via xurl CLI, then mark as 'posted'."""
    user_id = request.user_id
    tweet = db_get_tweet(user_id, tweet_id)
    
    if not tweet:
        return jsonify({'error': 'Tweet not found'}), 404
    
    text = tweet.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Tweet text is empty'}), 400
    
    success, message = post_tweet_via_xurl(text)
    
    if success:
        db_update_tweet(user_id, tweet_id, {
            'status': 'posted',
            'posted_at': datetime.now().isoformat(),
            'post_message': message,
        })
        return jsonify({'status': 'posted', 'message': message})
    else:
        return jsonify({'status': 'error', 'message': message}), 500


# --- Settings ---

@app.route('/api/settings', methods=['GET'])
@require_auth
def get_settings():
    user_id = request.user_id
    settings = db_get_settings(user_id)
    
    # Merge with defaults for any missing keys
    merged = dict(DEFAULT_SETTINGS)
    for section_key, section_data in settings.items():
        if section_key in merged and isinstance(merged[section_key], dict) and isinstance(section_data, dict):
            merged[section_key].update(section_data)
        else:
            merged[section_key] = section_data
    
    return jsonify(merged)


@app.route('/api/settings', methods=['PUT'])
@require_auth
def update_settings():
    user_id = request.user_id
    data = request.json
    
    # Save each section as a separate setting
    for section_key, section_data in data.items():
        if section_key in DEFAULT_SETTINGS:
            db_save_setting(user_id, section_key, section_data)
    
    # Reload and return merged settings
    settings = db_get_settings(user_id)
    merged = dict(DEFAULT_SETTINGS)
    for section_key, section_data in settings.items():
        if section_key in merged and isinstance(merged[section_key], dict) and isinstance(section_data, dict):
            merged[section_key].update(section_data)
        else:
            merged[section_key] = section_data
    
    return jsonify(merged)


@app.route('/api/settings/reset', methods=['POST'])
@require_auth
def reset_settings():
    user_id = request.user_id
    # Delete all user settings
    from database import delete
    for key in DEFAULT_SETTINGS:
        delete("settings", filters={"user_id": user_id, "key": key})
    return jsonify(dict(DEFAULT_SETTINGS))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'mode': 'supabase' if USE_SUPABASE else 'sqlite',
        'auth_mode': 'supabase' if (SUPABASE_URL and SUPABASE_SERVICE_KEY) else ('password' if USE_PASSWORD_AUTH else 'none'),
    })


# ---------------------------------------------------------------------------
# Favicon
# ---------------------------------------------------------------------------

@app.route('/favicon.svg')
def favicon():
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.svg', mimetype='image/svg+xml')


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

@app.after_request
def add_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
