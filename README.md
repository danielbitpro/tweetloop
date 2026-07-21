# TweetLoop

<p align="center">
  <img src="https://raw.githubusercontent.com/danielbitpro/tweetloop/master/static/tweetloop-logo.png" alt="TweetLoop Logo" width="120" style="border-radius: 24px;">
</p>

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
- 🎨 **Dark Terminal Theme** — Cyberpunk-inspired terminal aesthetic with neon accents

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

One script. Zero dependencies. Here's all you need:

```bash
git clone https://github.com/danielbitpro/tweetloop.git
cd tweetloop
cp env.example .env
# Edit .env → set PASSWORD=your_secure_password_here
chmod +x start.sh
./start.sh
```

That's it. Navigate to `http://localhost:7777`.

> **What `start.sh` does:** installs system dependencies (Python, pip, venv), creates a virtual environment, installs Python packages, and starts the app. No manual setup required.

Optional: set `PORT=8080 ./start.sh` to change the port.

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

TweetLoop reads verified tweets from pipeline output files. Users can get tweets into the app in two ways:

### Option 1: IMPORT Button (Manual)

Click the **📥 IMPORT** button in the header, select any `*-final.md` file, and the app will parse and import all tweets. This is a one-time operation — good for testing or ad-hoc imports.

### Option 2: FETCH Button (Automated)

Set your pipeline output directory in **Settings → Pipeline → Output Directory**, then click **🔄 FETCH**. The app will automatically find today's `*-final.md` file in that directory and import it. This is the primary workflow for users with an AI pipeline that generates daily output.

> **Note:** The FETCH feature requires the Flask app to have filesystem access to the configured directory.

### Bridge Script (Optional — for Cron Users)

For users who prefer server-side automation, the `pipeline_to_app_bridge.py` script imports tweets into the SQLite database.

```bash
# Configure paths (optional — defaults are sensible)
export TLP_WORKSPACE=/path/to/workspace
export TLP_DB_PATH=/path/to/data/tweetloop.db

# Run the bridge
python3 pipeline_to_app_bridge.py
```

### Expected Input Format

The pipeline should output files matching `*-final.md` in the configured directory. Each tweet should be formatted as:

```markdown
## X. [Label] | **Tweet:**
> Tweet text here
>
> #Hashtag

**Source:** [Name](url)
**Why it works:** Brief explanation
```

### Sample Output File

A complete example of a `*-final.md` file:

```markdown
## 1. [Local LLM] | **Tweet:**
> Fresh on HF: Qwen3.6-35B-A3B-UD-Q8_K_XL.gguf — 35B parameters, 3B active, quantized to Q8. Runs on a single RTX 3090. Drop it straight into your local setup.

**Source:** [Hugging Face](https://huggingface.co)
**Why it works:** Concrete numbers + specific hardware requirement = high engagement in LocalLLaMA.

## 2. [AI Agents] | **Tweet:**
> vix: a new coding agent built specifically for local LLMs via Ollama + llama.cpp. Full agentic workflow, no cloud dependency. Self-hosted from day one.

**Source:** [GitHub](https://github.com)
**Why it works:** Names the agent, lists the stack, emphasizes self-hosting — hits all the right notes for the audience.
```

### How It Works

1. Your AI pipeline (Hermes, LangChain, custom scripts, etc.) generates a `*-final.md` file with today's date (e.g., `2026-07-21-final.md`)
2. The file is saved to the configured output directory
3. In TweetLoop, click **🔄 FETCH** to automatically import today's tweets
4. Review, edit, schedule, and post from the dashboard

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
