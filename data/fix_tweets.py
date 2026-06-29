#!/usr/bin/env python3
"""Fix existing tweets: clean text field, update dates to execution date."""
import json
import re
from datetime import datetime

DATA_FILE = "/home/danny/workspace/twitter-reviewer/data/tweets.json"

today = datetime.now().strftime("%Y-%m-%d")

with open(DATA_FILE, 'r') as f:
    tweets = json.load(f)

cleaned = 0
dates_fixed = 0

for tweet in tweets:
    text = tweet.get('text', '')
    why = tweet.get('why_it_works')
    label = tweet.get('label')
    orig_text = text
    
    # Remove "**Why it works:** explanation" from end of text
    if why and f"\n\n**Why it works:** {why}" in text:
        text = text.replace(f"\n\n**Why it works:** {why}", "")
        cleaned += 1
    
    # Remove "[Label]" prefix from text (it was added by old build_formatted_text)
    # Pattern: text starts with "[Label]\n\n" or "[Label]\n"
    if label and text.startswith(f"[{label}]"):
        text = re.sub(r'^\[' + re.escape(label) + r'\]\s*\n+', '', text)
        if orig_text == text:
            cleaned += 1  # only count if we actually changed something
        else:
            cleaned += 1  # count again since we modified it
    
    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    
    if text != orig_text:
        tweet['text'] = text
    
    # Update date to execution date
    if tweet.get('date') != today:
        tweet['date'] = today
        dates_fixed += 1

with open(DATA_FILE, 'w') as f:
    json.dump(tweets, f, indent=2)

print(f"Cleaned text fields: {cleaned} tweets")
print(f"Updated dates to {today}: {dates_fixed} tweets")
print(f"\nSample tweet text (first 300 chars):")
if tweets:
    print(repr(tweets[0]['text'][:300]))
    print(f"\nSample why_it_works: {tweets[0].get('why_it_works', 'N/A')}")
