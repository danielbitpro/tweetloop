#!/bin/bash

# Start TweetLoop App
# Usage: ./start.sh [port]
# Or:   PORT=8080 ./start.sh

cd "$(dirname "$0")"

# Start the app
python3 app.py
