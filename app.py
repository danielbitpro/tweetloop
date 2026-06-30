"""
Twitter Reviewer App
Flask backend for the Tweet Reviewer dashboard.
"""

import json
import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, make_response, session

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'tweets.json')
PORT = int(os.environ.get('PORT', 7777))

# Optional password authentication via .env
def get_password():
    """Load password from .env file if it exists."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('REVIEWER_PASSWORD='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('REVIEWER_PASSWORD', '')

PASSWORD_HASH = get_password()

def require_auth(f):
    """Decorator to require authentication if password is set."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not PASSWORD_HASH:
            return f(*args, **kwargs)
        if not session.get('authenticated'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def load_tweets():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_tweets(tweets):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(tweets, f, indent=2, default=str)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    entered_password = data.get('password', '') if data else ''
    if not PASSWORD_HASH:
        session['authenticated'] = True
        return jsonify({'status': 'authenticated'})
    if entered_password == PASSWORD_HASH:
        session['authenticated'] = True
        return jsonify({'status': 'authenticated'})
    return jsonify({'status': 'unauthorized', 'error': 'Invalid password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return jsonify({'status': 'logged_out'})

@app.route('/api/status')
def status():
    return jsonify({'authenticated': session.get('authenticated', False), 'auth_required': bool(PASSWORD_HASH)})

@app.route('/api/tweets', methods=['GET'])
@require_auth
def get_tweets():
    tweets = load_tweets()
    # Group by date for frontend
    grouped = {}
    for tweet in tweets:
        date = tweet.get('date', tweet.get('created_at', 'unknown'))[:10]  # YYYY-MM-DD
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(tweet)
    
    # Sort dates descending
    sorted_tweets = {}
    for date in sorted(grouped.keys(), reverse=True):
        sorted_tweets[date] = sorted(grouped[date], key=lambda x: (x.get('section_number') or 0, x.get('id', '')))
    
    return jsonify(sorted_tweets)

@app.route('/api/tweets', methods=['POST'])
@require_auth
def add_tweet():
    data = request.json
    new_tweet = {
        'id': str(uuid.uuid4()),
        'text': data.get('text', ''),
        'label': data.get('label', None),
        'hashtags': data.get('hashtags', ''),
        'why_it_works': data.get('why_it_works', None),
        'section_number': data.get('section_number', None),
        'status': 'draft',
        'schedule_time': data.get('schedule_time', None),
        'source': data.get('source', 'manual'),
        'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
        'created_at': datetime.now().isoformat()
    }
    tweets = load_tweets()
    tweets.append(new_tweet)
    save_tweets(tweets)
    return jsonify(new_tweet), 201

@app.route('/api/tweets/<tweet_id>', methods=['PUT'])
@require_auth
def update_tweet(tweet_id):
    tweets = load_tweets()
    for tweet in tweets:
        if tweet['id'] == tweet_id:
            tweet.update(request.json)
            save_tweets(tweets)
            return jsonify(tweet)
    return jsonify({'error': 'Tweet not found'}), 404

@app.route('/api/tweets/<tweet_id>', methods=['DELETE'])
@require_auth
def delete_tweet(tweet_id):
    tweets = load_tweets()
    new_tweets = [t for t in tweets if t['id'] != tweet_id]
    if len(new_tweets) == len(tweets):
        return jsonify({'error': 'Tweet not found'}), 404
    save_tweets(new_tweets)
    return jsonify({'status': 'deleted'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
