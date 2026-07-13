#!/usr/bin/env python3
"""
Pipeline to App Bridge

Reads the verified tweets from the X-proposed-tweets pipeline output
and updates the TweetLoop app's SQLite database.
"""

import json
import os
import re
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def similarity_score(text1, text2):
    """Calculate similarity between two texts (0.0 to 1.0).
    
    Uses SequenceMatcher for character-level similarity.
    Returns a score where 1.0 = identical, 0.0 = completely different.
    """
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()


def is_duplicate(new_tweet, existing_tweets, threshold=0.85):
    """Check if a new tweet is a duplicate of any existing tweet.
    
    Args:
        new_tweet: dict with 'text' key
        existing_tweets: list of existing tweet dicts
        threshold: similarity threshold (0.0-1.0), default 0.85
    
    Returns:
        (is_dup, matched_tweet, score) tuple
    """
    new_text = new_tweet.get('text', '').strip()
    if not new_text:
        return False, None, 0.0
    
    for existing in existing_tweets:
        existing_text = existing.get('text', '').strip()
        if not existing_text:
            continue
        
        score = similarity_score(new_text, existing_text)
        if score >= threshold:
            return True, existing, score
    
    return False, None, 0.0


# ---------------------------------------------------------------------------
# Bridge logic
# ---------------------------------------------------------------------------

# Paths - configurable via environment variables
WORKSPACE = Path(os.environ.get("TLP_WORKSPACE", Path.home() / "workspace"))
X_PROPOSED_DIR = WORKSPACE / "X-proposed-tweets"
X_BRIEFINGS_DIR = WORKSPACE / "X-briefings"
DB_FILE = Path(os.environ.get("TLP_DB_PATH", Path(__file__).parent / "data" / "tweetloop.db"))


def load_tweets():
    """Load all tweets from the SQLite database."""
    if not DB_FILE.exists():
        return []
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM tweets')
        tweets = [dict(row) for row in c.fetchall()]
        conn.close()
        return tweets
    except (sqlite3.Error, FileNotFoundError):
        return []


def save_tweets(tweets):
    """Save all tweets to the SQLite database."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Clear existing tweets and re-insert (simple approach)
    c.execute('DELETE FROM tweets')
    for tweet in tweets:
        c.execute('''
            INSERT INTO tweets (id, text, label, hashtags, why_it_works, section_number, source_url, status, date, schedule_time, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tweet.get('id'),
            tweet.get('text'),
            tweet.get('label'),
            tweet.get('hashtags', ''),
            tweet.get('why_it_works'),
            tweet.get('section_number'),
            tweet.get('source_url'),
            tweet.get('status', 'draft'),
            tweet.get('date'),
            tweet.get('schedule_time'),
            tweet.get('source', 'pipeline'),
        ))
    conn.commit()
    conn.close()


def extract_source_url_from_block(block):
    """Extract the source URL directly from a tweet block's **Source:** line.
    Format: **Source:** [Name](url)
    Returns the URL string or None."""
    match = re.search(r'\*\*Source:\*\*\s+\[.*?\]\((https?://[^\)]+)\)', block)
    if match:
        return match.group(1)
    return None


def parse_tweets_from_md(file_path):
    """
    Parse tweets from the final.md file produced by the pipeline.
    
    Expected format:
    ## X. [Label] | **Tweet:**
    > Tweet text line 1
    >
    > #Hashtag
    |
    **Source:** [Name](url)
    **Why it works:** ...

    ## Y. [Label]
    ...
    """
    file_path = Path(file_path)
    with open(file_path, 'r') as f:
        content = f.read()

    # Extract the date from the filename (e.g., "2026-06-28-final.md")
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path.name)
    date_str = date_match.group(1) if date_match else 'unknown'

    # Split into individual tweet blocks by "## N." headers
    tweet_blocks = re.split(r'(?=\n## \d+\. )', content.strip())

    tweets = []
    for block in tweet_blocks:
        block = block.strip()
        if not block:
            continue

        # Extract section number: "## X."
        section_match = re.match(r'## (\d+)\.', block)
        section_number = int(section_match.group(1)) if section_match else None

        # Extract label: "[Label]"
        label_match = re.search(r'\[([^\]]+)\]', block)
        label = label_match.group(1) if label_match else None

        # Extract tweet text from blockquote lines
        tweet_text_lines = []
        hashtags = []
        in_tweet_block = False
        after_closing_pipe = False
        tweet_header_seen = False

        for line in block.split('\n'):
            line_stripped = line.strip()

            # Handle both formats:
            # 1) "## X. [Label] | **Tweet:**" (inline)
            # 2) "| **Tweet:**" on its own line
            if not tweet_header_seen and ('| **Tweet:**' in line_stripped or line_stripped == '| **Tweet:**'):
                in_tweet_block = True
                after_closing_pipe = False
                tweet_header_seen = True
                continue

            # Closing pipe ends the tweet block — stop processing this block
            if line_stripped == '|' and in_tweet_block:
                in_tweet_block = False
                after_closing_pipe = True
                continue

            # Skip everything after closing pipe
            if after_closing_pipe:
                break

            if in_tweet_block:
                if line_stripped.startswith('> '):
                    text = line_stripped[2:].strip()
                    if not text:
                        # Empty blockquote line = line break in tweet
                        tweet_text_lines.append('')
                    elif text.startswith('#'):
                        hashtags.append(text)
                    else:
                        tweet_text_lines.append(text)

        # Clean up empty lines at start/end
        while tweet_text_lines and not tweet_text_lines[0]:
            tweet_text_lines.pop(0)
        while tweet_text_lines and not tweet_text_lines[-1]:
            tweet_text_lines.pop()

        text = '\n'.join(tweet_text_lines)
        hashtags_str = ' '.join(hashtags) if hashtags else ''

        # Extract "Why it works" explanation
        why_match = re.search(r'\*\*Why it works:\*\*\s*(.+)', block)
        why_it_works = why_match.group(1).strip() if why_match else None

        # Extract source URL directly from the block
        source_url = extract_source_url_from_block(block)

        if text:
            tweets.append({
                'section_number': section_number,
                'label': label,
                'text': text,
                'hashtags': hashtags_str,
                'why_it_works': why_it_works,
                'source_url': source_url,
                'date': date_str
            })

    return tweets


def generate_id(text, date):
    """Generate a consistent ID based on the tweet text and date."""
    return hashlib.md5((text + date).encode()).hexdigest()[:8]


def bridge():
    today = datetime.now().strftime("%Y-%m-%d")
    final_file = X_PROPOSED_DIR / f"{today}-final.md"

    if not final_file.exists():
        print(f"No final file found for {today} at {final_file}")
        return

    print(f"Reading pipeline output from: {final_file}")
    pipeline_tweets = parse_tweets_from_md(final_file)

    if not pipeline_tweets:
        print("No tweets found in the pipeline output.")
        return

    print(f"Found {len(pipeline_tweets)} tweets in pipeline output.")

    app_tweets = load_tweets()
    existing_keys = {t['text'] for t in app_tweets}

    new_count = 0
    duplicate_count = 0
    skipped_exact = 0

    for tweet_data in pipeline_tweets:
        text = tweet_data['text']
        
        # Check 1: Exact text match
        if text in existing_keys:
            skipped_exact += 1
            continue
        
        # Check 2: Similarity-based deduplication
        tweet_dict = {
            'id': generate_id(text, today),
            'user_id': '00000000-0000-0000-0000-000000000001',
            'text': text,
            'label': tweet_data.get('label'),
            'hashtags': tweet_data.get('hashtags', ''),
            'why_it_works': tweet_data.get('why_it_works'),
            'section_number': tweet_data.get('section_number'),
            'source_url': tweet_data.get('source_url'),
            'status': 'draft',
            'date': today,
            'schedule_time': None,
            'source': 'pipeline',
        }
        
        is_dup, matched_tweet, score = is_duplicate(tweet_dict, app_tweets, threshold=0.85)
        if is_dup:
            duplicate_count += 1
            matched_date = matched_tweet.get('date', 'unknown')
            matched_id = matched_tweet.get('id', 'unknown')[:8]
            print(f"  ⚠ DUPLICATE (score: {score:.2f}): '{text[:60]}...' matches existing tweet #{matched_id} ({matched_date})")
            continue
        
        app_tweets.append(tweet_dict)
        existing_keys.add(text)
        new_count += 1

    if new_count > 0:
        save_tweets(app_tweets)
        print(f"✓ Added {new_count} new tweets to the app.")
        print(f"  - Exact duplicates skipped: {skipped_exact}")
        print(f"  - Similar duplicates skipped: {duplicate_count}")
        print(f"  Total tweets in app: {len(app_tweets)}")
    else:
        print("All pipeline tweets already exist in the app.")
        print(f"  - Exact duplicates: {skipped_exact}")
        print(f"  - Similar duplicates: {duplicate_count}")


if __name__ == '__main__':
    bridge()
