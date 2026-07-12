# TweetLoop

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)

A research-to-post content pipeline for X/Twitter. Research, review, edit, and schedule tweets — all self-hosted.

> "Research-driven content engine, not a generic tweet generator."

## Features

- 🔍 **Source Research** — Pull from Twitter, GitHub, Reddit, Hacker News, and custom URLs
- ✏️ **Review & Edit** — Full CRUD dashboard with approval workflow
- 📅 **Scheduling** — Schedule tweets for specific times with rate limiting
- 🔐 **Dual Auth** — Password auth (offline) or Supabase JWT (cloud)
- 🗄️ **Dual DB** — SQLite (self-hosted) or PostgreSQL (Supabase)
- 🎨 **Dark Terminal Theme** — Dark terminal aesthetic with neon accents
- 🔌 **Pipeline Bridge** — Auto-import from AI research pipelines
- 📊 **Status Tracking** — Draft, Approved, Scheduled, Posted, Manual

## Architecture

```
Environment check:
  │
  ├─ SUPABASE_URL + SUPABASE_SERVICE_KEY set?
  │   ├─ YES → Supabase PostgreSQL + JWT auth (cloud)
  │   │
  │   └─ NO → SQLite + password auth (offline)
```

**One codebase, two modes.** No branching. The Supabase path is ready for when you build the paid tier later.

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/danielbitpro/tweetloop.git
cd tweetloop
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file:

```bash
# Password auth (for offline/self-hosted)
PASSWORD=your_secure_password_here

# Or Supabase (for cloud deployment)
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_SERVICE_KEY=your-service-key
```

### 3. Run

```bash
python3 app.py
```

Navigate to `http://localhost:7777`

## Integration with AI Pipeline

TweetLoop reads verified tweets from a JSON file. The `pipeline_to_app_bridge.py` script automates this:

```json
[
  {
    "id": "unique-id",
    "text": "Your tweet text",
    "hashtags": "#AI #LocalLLM",
    "status": "draft",
    "schedule_time": "2024-01-01T08:00:00",
    "source": "Twitter",
    "source_url": "https://twitter.com/..."
  }
]
```

### Bridge Script

```bash
python3 pipeline_to_app_bridge.py
```

This reads pipeline output and imports new tweets into the app, checking for duplicates.

## Hermes Agent Integration

For Hermes users, install the `tweetloop` skill to automatically connect your AI pipeline to this dashboard.

## Docker Support

Coming soon. Self-host with Docker for easy deployment.

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `PORT` | HTTP port | `7777` |
| `PASSWORD` | Auth password (`.env`) | Required for password auth |
| `SUPABASE_URL` | Supabase project URL | Optional |
| `SUPABASE_SERVICE_KEY` | Supabase service key | Optional |

## Roadmap

### Phase 1: Open-Source MVP (Current)
- ✅ Flask backend with full CRUD API
- ✅ SQLite database
- ✅ Password auth
- ✅ Supabase path ready
- ✅ Frontend UI (Dark Terminal theme)
- ✅ Pipeline bridge
- ✅ Settings management
- ✅ Emoji picker
- ⏳ Docker support
- ⏳ Source link fix (bug)
- ⏳ Research time enforcement (bug)
- ⏳ Deduplication with similarity

### Phase 2: Open-Source Enhancements
- Auto-posting settings (scheduled mode, rate limiting)
- Configurable research sources
- Manual research trigger
- Fact check button
- Rephrase button (local model)
- Templates library
- History + favorites

### Phase 3: Paid Tier
- ArXiv source
- Custom websites
- Prioritized X accounts
- Manual keyword research
- Auto-posting
- Analytics
- Multi-account support

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please open an issue or submit a PR.

## Support

Found a bug? Have a feature request? Open an [issue](https://github.com/danielbitpro/tweetloop/issues).

---

*Built with ❤️ for the Local AI community*
