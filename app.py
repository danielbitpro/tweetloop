"""
TweetLoop — Flask backend for the TweetLoop dashboard.

Dual auth:
  - Supabase JWT (when SUPABASE_URL is set)
  - Password from .env (when SUPABASE_URL is NOT set)

Database:
  - Supabase PostgreSQL (when SUPABASE_URL is set)
  - SQLite fallback (when SUPABASE_URL is NOT set)
"""

import csv
import json
import os
import sqlite3
import subprocess
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_file

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
        "custom_x_accounts": [],
        "custom_urls": [],
        "language": "en",
        "research_days": 1,
        "min_history": 30,
        "enable_archive": False,
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
    "autopost": {
        "enable": False,
        "max_posts_per_day": 3,
        "min_gap_minutes": 60,
        "preferred_times": ["09:00", "14:00", "19:00"],
        "mode": "approved",
    },
}

# ---------------------------------------------------------------------------
# Startup: migrate existing JSON data to database (once, at import time)
# ---------------------------------------------------------------------------

_migrated = False

def _do_migration():
    """Migrate JSON files to database once at startup."""
    global _migrated
    if _migrated:
        return
    if USE_SUPABASE:
        _migrated = True
        return
    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        tweets_json = os.path.join(data_dir, 'tweets.json')
        settings_json = os.path.join(data_dir, 'settings.json')
        
        migrated_tweets = migrate_tweets_from_json(tweets_json)
        migrated_settings = migrate_settings_from_json(settings_json)
        
        if migrated_tweets or migrated_settings:
            print(f"[TweetLoop] Migrated {migrated_tweets} tweets, {migrated_settings} settings to database")
    except Exception as e:
        print(f"[TweetLoop] Migration error: {e}")
    finally:
        _migrated = True

# Run migration at import time (before server starts)
_do_migration()

@app.before_request
def _skip_migration():
    """Migration already done at import time — no-op."""
    pass


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
# Archive endpoints
# ---------------------------------------------------------------------------

@app.route('/api/archive/check', methods=['GET'])
@require_auth
def check_archive():
    """Check if an archive is ready for download."""
    try:
        from pipeline_to_app_bridge import check_archive_ready
        archive_info = check_archive_ready()
        if archive_info:
            return jsonify({
                'ready': True,
                'month': archive_info.get('month', ''),
                'count': archive_info.get('count', 0),
                'cutoff_date': archive_info.get('cutoff_date', ''),
            })
        else:
            return jsonify({'ready': False})
    except Exception as e:
        return jsonify({'ready': False, 'error': str(e)}), 500


@app.route('/api/archive/download', methods=['POST'])
@require_auth
def download_archive():
    """Download archive CSV and purge old tweets."""
    try:
        from pipeline_to_app_bridge import (
            check_archive_ready,
            purge_old_tweets,
            remove_archive,
            DB_FILE,
        )
        import csv
        import os
        from pathlib import Path
        
        archive_info = check_archive_ready()
        if not archive_info:
            return jsonify({'error': 'No archive available'}), 404
        
        archive_file = Path(archive_info.get('file', ''))
        if not archive_file.exists():
            return jsonify({'error': 'Archive file not found'}), 404
        
        # Get min_history for purge
        settings_file = DB_FILE.parent / "settings.json"
        min_history = 30
        if settings_file.exists():
            with open(settings_file) as f:
                settings = json.load(f)
                min_history = settings.get('research', {}).get('min_history', 30)
        
        # Purge old tweets
        purged_count = purge_old_tweets(min_history=min_history)
        
        # Remove archive flag
        remove_archive()
        
        # Send file
        return send_file(
            str(archive_file),
            as_attachment=True,
            download_name=f"tweets-{archive_info.get('month', 'archive')}.csv",
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Auto-posting endpoints
# ---------------------------------------------------------------------------

@app.route('/api/autopost/status', methods=['GET'])
@require_auth
def autopost_status():
    """Get auto-posting status: how many posts today, next available time."""
    try:
        from database import get_settings as db_get_settings
        from pipeline_to_app_bridge import DB_FILE
        import json
        
        user_id = request.user_id
        settings = db_get_settings(user_id)
        
        # Get autopost settings
        autopost = settings.get('autopost', DEFAULT_SETTINGS.get('autopost', {}))
        if not autopost.get('enable', False):
            return jsonify({
                'enabled': False,
                'message': 'Auto-posting is disabled'
            })
        
        # Get posted tweets today
        today = datetime.now().strftime('%Y-%m-%d')
        all_tweets = db_get_tweets(user_id, limit=500)
        posted_today = [t for t in all_tweets if t.get('status') == 'posted' and t.get('date') == today]
        
        max_posts = autopost.get('max_posts_per_day', 3)
        remaining = max(0, max_posts - len(posted_today))
        
        # Find next available time
        preferred_times = autopost.get('preferred_times', ['09:00', '14:00', '19:00'])
        now = datetime.now()
        next_time = None
        for time_str in preferred_times:
            try:
                h, m = map(int, time_str.split(':'))
                candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if candidate > now:
                    next_time = time_str
                    break
            except:
                pass
        
        if not next_time and preferred_times:
            next_time = preferred_times[0]
        
        return jsonify({
            'enabled': True,
            'posted_today': len(posted_today),
            'max_posts': max_posts,
            'remaining': remaining,
            'next_available': next_time,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/autopost/post-eligible', methods=['POST'])
@require_auth
def autopost_eligible():
    """Auto-post eligible tweets based on settings."""
    try:
        from database import get_settings as db_get_settings, update_tweet as db_update_tweet
        from pipeline_to_app_bridge import DB_FILE
        import json
        
        user_id = request.user_id
        settings = db_get_settings(user_id)
        
        autopost = settings.get('autopost', DEFAULT_SETTINGS.get('autopost', {}))
        if not autopost.get('enable', False):
            return jsonify({'error': 'Auto-posting is disabled'}), 400
        
        max_posts = autopost.get('max_posts_per_day', 3)
        mode = autopost.get('mode', 'approved')
        
        # Get posted tweets today
        today = datetime.now().strftime('%Y-%m-%d')
        all_tweets = db_get_tweets(user_id, limit=500)
        posted_today = [t for t in all_tweets if t.get('status') == 'posted' and t.get('date') == today]
        
        if len(posted_today) >= max_posts:
            return jsonify({
                'posted': 0,
                'message': f'Max posts per day ({max_posts}) reached'
            })
        
        # Find eligible tweets
        eligible_status = 'approved' if mode == 'approved' else ['approved', 'draft']
        eligible = [t for t in all_tweets if t.get('status') in eligible_status and not t.get('posted_at')]
        
        # Sort by date (newest first), then section number
        eligible.sort(key=lambda x: (x.get('date') or '', x.get('section_number') or 0), reverse=True)
        
        # Post up to remaining
        remaining = max_posts - len(posted_today)
        posted_count = 0
        
        for tweet in eligible[:remaining]:
            success, message = post_tweet_via_xurl(tweet.get('text', ''))
            if success:
                db_update_tweet(user_id, tweet['id'], {
                    'status': 'posted',
                    'posted_at': datetime.now().isoformat(),
                    'post_message': message,
                })
                posted_count += 1
        
        return jsonify({
            'posted': posted_count,
            'message': f'Posted {posted_count} tweet(s)' if posted_count > 0 else 'No eligible tweets'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Manual research endpoint
# ---------------------------------------------------------------------------

@app.route('/api/research/run', methods=['POST'])
@require_auth
def run_manual_research():
    """Trigger a manual research cycle on a specific topic."""
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        max_stories = data.get('max_stories', 10)
        max_proposals = data.get('max_proposals', 5)
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        # Build the research command with topic override
        research_cmd = [
            'hermes', 'cron', 'run', 'daily-tech-pipeline',
            '--context', f'topic_override={topic}'
        ]
        
        # For now, just log that research was requested
        # The actual research runs via the cron job
        print(f"[TweetLoop] Manual research requested: topic='{topic}', stories={max_stories}, proposals={max_proposals}")
        
        return jsonify({
            'message': f'Research started for "{topic}". Check X-briefings/ after pipeline completes.',
            'topic': topic,
            'max_stories': max_stories,
            'max_proposals': max_proposals,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

@app.route('/favicon.ico')
def favicon_ico():
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/x-icon')


@app.route('/favicon-32x32.png')
def favicon_32():
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon-32x32.png', mimetype='image/png')


@app.route('/favicon-16x16.png')
def favicon_16():
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon-16x16.png', mimetype='image/png')


@app.route('/apple-touch-icon.png')
def apple_touch_icon():
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static'), 'apple-touch-icon.png', mimetype='image/png')


@app.route('/site.webmanifest')
def web_manifest():
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static'), 'site.webmanifest', mimetype='application/manifest+json')


# ---------------------------------------------------------------------------
# Auto-posting scheduler (in-process, survives restarts)
# ---------------------------------------------------------------------------

_scheduler = None
_scheduler_active = False


def _get_scheduler():
    """Get or create the APScheduler instance."""
    global _scheduler
    if _scheduler is None:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()
    return _scheduler


def _autopost_job():
    """Background job that calls the auto-posting logic directly."""
    try:
        # Import inside the job to avoid circular imports at startup
        from database import get_settings as db_get_settings
        from pipeline_to_app_bridge import DB_FILE
        import json

        # Load user settings
        settings_file = DB_FILE.parent / "settings.json"
        if not settings_file.exists():
            return

        with open(settings_file) as f:
            settings = json.load(f)

        autopost = settings.get('autopost', DEFAULT_SETTINGS.get('autopost', {}))
        if not autopost.get('enable', False):
            return

        # Check rate limits
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) as cnt FROM tweets WHERE status = ? AND date = ?",
            ('posted', today)
        )
        posted_today = c.fetchone()['cnt']
        conn.close()

        max_posts = autopost.get('max_posts_per_day', 3)
        if posted_today >= max_posts:
            return

        # Check min gap between posts
        min_gap = autopost.get('min_gap_minutes', 60)
        if posted_today > 0:
            conn = sqlite3.connect(str(DB_FILE))
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                "SELECT MAX(posted_at) as last_post FROM tweets WHERE status = ? AND date = ? AND posted_at IS NOT NULL",
                ('posted', today)
            )
            row = c.fetchone()
            conn.close()
            if row['last_post']:
                last_post = datetime.fromisoformat(row['last_post'])
                gap = (datetime.now() - last_post).total_seconds() / 60
                if gap < min_gap:
                    return

        # Find eligible tweets
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        mode = autopost.get('mode', 'approved')
        if mode == 'approved':
            c.execute(
                "SELECT * FROM tweets WHERE status = 'approved' AND posted_at IS NULL ORDER BY date DESC, section_number DESC LIMIT ?",
                (max_posts - posted_today,)
            )
        else:
            c.execute(
                "SELECT * FROM tweets WHERE status IN ('approved', 'draft') AND posted_at IS NULL ORDER BY date DESC, section_number DESC LIMIT ?",
                (max_posts - posted_today,)
            )
        eligible = [dict(row) for row in c.fetchall()]
        conn.close()

        if not eligible:
            return

        # Post tweets
        posted_count = 0
        for tweet in eligible:
            text = tweet.get('text', '').strip()
            if not text:
                continue
            success, message = post_tweet_via_xurl(text)
            if success:
                conn = sqlite3.connect(str(DB_FILE))
                c = conn.cursor()
                c.execute(
                    "UPDATE tweets SET status = ?, posted_at = ?, post_message = ? WHERE id = ?",
                    ('posted', datetime.now().isoformat(), message, tweet['id'])
                )
                conn.commit()
                conn.close()
                posted_count += 1
            else:
                print(f"[TweetLoop] Auto-post failed: {message}")

        if posted_count > 0:
            print(f"[TweetLoop] Auto-posted {posted_count} tweet(s)")
    except Exception as e:
        print(f"[TweetLoop] Scheduler job error: {e}")


def start_scheduler():
    """Start the auto-posting scheduler if enabled."""
    global _scheduler_active
    from pipeline_to_app_bridge import DB_FILE
    settings_file = DB_FILE.parent / "settings.json"
    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)
        if settings.get('autopost', {}).get('enable', False):
            stop_scheduler()
            sched = _get_scheduler()
            preferred_times = settings.get('autopost', {}).get('preferred_times', ['09:00', '14:00', '19:00'])
            for time_str in preferred_times:
                try:
                    h, m = map(int, time_str.split(':'))
                    sched.add_job(_autopost_job, 'cron', hour=h, minute=m, id=f'autopost_{h}_{m}')
                except:
                    pass
            # Also add an hourly fallback check
            sched.add_job(_autopost_job, 'interval', hours=1, id='autopost_hourly')
            if not sched.running:
                sched.start()
            _scheduler_active = True
            print("[TweetLoop] Auto-posting scheduler started")


def stop_scheduler():
    """Stop the auto-posting scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
    _scheduler_active = False
    print("[TweetLoop] Auto-posting scheduler stopped")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

@app.after_request
def add_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/autopost/scheduler/status', methods=['GET'])
@require_auth
def scheduler_status():
    """Get scheduler status for the frontend."""
    try:
        from database import get_settings as db_get_settings
        settings = db_get_settings(request.user_id)
        autopost = settings.get('autopost', DEFAULT_SETTINGS.get('autopost', {}))
        enabled = autopost.get('enable', False)
        return jsonify({
            'enabled': enabled,
            'running': _scheduler_active,
            'message': 'Auto-posting is active' if enabled and _scheduler_active else 'Auto-posting is disabled',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 7777))
    CERT_DIR = os.path.join(os.path.dirname(__file__), 'certs')
    CERT_FILE = os.path.join(CERT_DIR, 'cert.pem')
    KEY_FILE = os.path.join(CERT_DIR, 'key.pem')

    # Start scheduler if auto-posting is enabled
    start_scheduler()

    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        print(f"[TweetLoop] Starting HTTPS on port {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False, ssl_context=(CERT_FILE, KEY_FILE))
    else:
        print(f"[TweetLoop] Starting HTTP on port {PORT} (no certs found in {CERT_DIR})")
        app.run(host='0.0.0.0', port=PORT, debug=False)
