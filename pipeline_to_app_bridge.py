#!/usr/bin/env python3
"""
Pipeline to App Bridge

Reads the verified tweets from the X-proposed-tweets pipeline output
and updates the TweetLoop app's database (tweets.json).
"""

import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

# Paths
WORKSPACE = Path("/home/danny/workspace")
X_PROPOSED_DIR = WORKSPACE / "X-proposed-tweets"
X_BRIEFINGS_DIR = WORKSPACE / "X-briefings"
DATA_FILE = Path("/home/danny/workspace/tweetloop/data/tweets.json")


def load_tweets():
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_tweets(tweets):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(tweets, f, indent=2)


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
    for tweet_data in pipeline_tweets:
        text = tweet_data['text']
        if text not in existing_keys:
            app_tweets.append({
                'id': generate_id(text, today),
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
            })
            new_count += 1

    if new_count > 0:
        save_tweets(app_tweets)
        print(f"Added {new_count} new tweets to the app.")
        print(f"Total tweets in app: {len(app_tweets)}")
    else:
        print("All pipeline tweets already exist in the app.")


if __name__ == '__main__':
    bridge()
