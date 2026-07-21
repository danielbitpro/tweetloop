#!/usr/bin/env bash
# TweetLoop — One-command install & launch
#
# Usage: ./start.sh
#
# What it does:
#   1. Installs system dependencies (Python, pip, venv)
#   2. Creates a virtual environment
#   3. Generates .env with default password if missing
#   4. Installs Python dependencies
#   5. Starts the Flask app
#
# Prerequisites: None. Run this on a fresh Ubuntu/Debian machine.

set -euo pipefail

cd "$(dirname "$0")"
PORT="${PORT:-7777}"

echo "🔧 TweetLoop — setting you up..."
echo ""

# ── Step 1: System dependencies ──────────────────────────────

# Check if ensurepip is available (this is what venv needs to create environments)
if ! python3 -c "import ensurepip" 2>/dev/null; then
    echo "📦 Installing Python 3, pip, and venv support..."
    sudo apt-get update -qq
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    VENV_PKG="python${PY_VERSION}-venv"
    sudo apt-get install -y -qq python3 python3-pip "${VENV_PKG}" > /dev/null 2>&1
fi

# Detect actual Python version (could be 3.11, 3.12, 3.13, etc.)
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# ── Step 2: Virtual environment ──────────────────────────────

if [ ! -f .venv/bin/python3 ]; then
    echo "📦 Creating virtual environment (Python ${PY_VERSION})..."
    python3 -m venv .venv
fi

# ── Step 3: Generate .env if missing ─────────────────────────

if [ ! -f .env ]; then
    echo "📝 Generating .env with default password..."
    cat > .env << 'EOF'
# TweetLoop Configuration
# Generated automatically by start.sh
# ⚠️  Change PASSWORD before using in production!

PASSWORD=tweetloop
PORT=7777
HTTPS_ENABLED=false
EOF
    echo "   → .env created with default password (change it in Settings!)"
fi

# ── Step 4: Python dependencies ──────────────────────────────

if ! .venv/bin/python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    .venv/bin/python3 -m pip install -q -r requirements.txt
fi

# ── Step 5: Start the app ───────────────────────────────────

echo ""
echo "🚀 TweetLoop is running!"
echo "   → http://localhost:${PORT}"
echo "   → Password: tweetloop (change it in Settings!)"
echo ""
.venv/bin/python3 app.py
