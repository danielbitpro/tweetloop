# TweetLoop

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)

A research-to-post content dashboard for X/Twitter. Research, review, edit, and schedule tweets — all self-hosted.

> "Research-driven content engine, not a generic tweet generator."

## Features

- ✏️ **Review & Edit** — Full CRUD dashboard with approval workflow (draft → approved → scheduled → posted)
- 📅 **Scheduling** — Schedule tweets for specific times with rate limiting
- 🔐 **Password Auth** — Session-based authentication, credentials in `.env`
- 🗄️ **SQLite Storage** — WAL mode, foreign keys, proper indexing
- 📊 **Status Tracking** — Draft, Approved, Scheduled, Posted, Manual
- 🔍 **Search & Filter** — Text search + status + label filtering
- 📦 **Bulk Actions** — Bulk approve/delete with selection
- 📤 **Auto-Posting** — In-process scheduler with preferred times, rate limiting, daily caps
- 📥 **Pipeline Bridge** — Auto-import from research pipeline output files
- 📋 **Export** — Raw, CSV, Pipeline format for approved tweets; JSON/CSV for all
- 📦 **Archive** — Monthly CSV archive with download and purge
- ⚙️ **Settings Panel** — Configurable research sources, auto-posting, export, pipeline paths
- 🎨 **Dark Terminal Theme** — Dark terminal aesthetic with neon accents

## Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Research Pipeline│────>│  TweetLoop App  │────>│  X / Twitter │
│  (external)       │     │  (Python/Flask) │     │              │
└──────────────────┘     └─────────────────┘     └──────────────┘
                           SQLite DB + .env config
```

**The app is a review dashboard.** The actual research, briefing, and tweet generation happen externally (cron jobs, AI agents, manual work). TweetLoop imports verified tweets via the bridge script and lets you review, edit, and post them.

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/danielbitpro/tweetloop.git
cd tweetloop
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file from the example:

```bash
cp env.example .env
```

Edit `.env` and set at minimum:

```bash
PASSWORD=your_secure_password_here
```

Optional settings:

```bash
PORT=7777                    # App listening port (default: 7777)
HTTPS_ENABLED=false          # Set true if you have certs/ directory
```

### 3. Run

```bash
python3 app.py
```

Navigate to `http://localhost:7777` (or `https://localhost:7777` with HTTPS).

### 4. Authorize Twitter (Optional — for posting from the app)

To enable direct posting from the dashboard, run:

```bash
xurl auth oauth2 --app twitter
```

Follow the browser flow to authorize. Then configure OAuth1 tokens in `.env`:

```bash
XURL_APP_OAUTH1_TOKEN=your_token
XURL_APP_OAUTH1_TOKEN_SECRET=your_token_secret
XURL_APP_OAUTH1_SECRET=your_secret
```

## Integration with External Pipeline

TweetLoop reads verified tweets from pipeline output files. The `pipeline_to_app_bridge.py` script imports them into the SQLite database.

### Bridge Script

```bash
# Configure paths (optional — defaults are sensible)
export TLP_WORKSPACE=/path/to/workspace
export TLP_DB_PATH=/path/to/data/tweetloop.db

# Run the bridge
python3 pipeline_to_app_bridge.py
```

### Expected Input Format

The bridge reads files matching `*-final.md` from the pipeline output directory. Each tweet should be formatted as:

```markdown
## X. [Label] | **Tweet:**
> Tweet text here
>
> #Hashtag

**Source:** [Name](url)
**Why it works:** Brief explanation
```

## Settings

The app includes a settings panel (⚙ Settings button) with tabs for:

- **App** — Password, port, auto-refresh interval
- **Research** — Source quotas, custom accounts, keywords, research time window
- **Copywriter** — Copywriting prompt configuration
- **Export** — Export format preferences
- **Pipeline** — Workspace paths, bridge settings
- **Auto-Post** — Preferred times, rate limits, daily caps, mode (approved/all)

## Database

Tweets are stored in `data/tweetloop.db` (SQLite). The schema supports:

- Tweet CRUD with status workflow
- Deduplication via text similarity (SequenceMatcher)
- Archive with monthly purge
- Source URL extraction

## Docker Support

Coming soon.

## License

MIT — see [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
