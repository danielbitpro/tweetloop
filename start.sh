#!/bin/bash

# Start TweetLoop App
# Usage: ./start.sh [port]
# Or:   PORT=8080 ./start.sh

cd "$(dirname "$0")"

# Install dependencies if needed
pip install -q flask > /dev/null 2>&1

# Start the app
python3 app.py
