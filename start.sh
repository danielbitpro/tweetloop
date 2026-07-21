#!/usr/bin/env bash
# TweetLoop — One-command launcher
#
# Usage: ./start.sh          # runs on PORT (default 7777)
#
# Prerequisites (run once):
#   sudo apt update && sudo apt install -y python3 python3-pip python3.12-venv
#
# This script:
#   1. Creates a venv if it doesn't exist
#   2. Installs dependencies if requirements aren't met
#   3. Starts the Flask app

set -euo pipefail

cd "$(dirname "$0")"
PORT="${PORT:-7777}"

# Create venv if missing
if [ ! -f .venv/bin/python3 ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Install deps if flask is not in venv
if ! .venv/bin/python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    .venv/bin/python3 -m pip install -q -r requirements.txt
fi

# Start the app
echo "🚀 Starting TweetLoop on port $PORT"
.venv/bin/python3 app.py
