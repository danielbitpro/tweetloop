# Auto-Posting System

## Overview

In-process APScheduler running inside Flask. No external cron, no Railway. User clicks "Enable auto-posting" in settings and it just works — same experience for OSS and self-hosted tiers.

## Architecture

- **Scheduler:** APScheduler BackgroundScheduler inside Flask process
- **Trigger:** User enables toggle in settings → scheduler starts automatically
- **Survives restarts:** Checks `data/settings.json` on startup
- **Settings re-read:** Every job run re-reads settings from disk
- **Both tiers:** Identical experience — click enable, it works

## Settings (Auto-Post Tab)

| Setting | Default | Range | Description |
|---|---|---|---|
| `preferred_times` | 09:00, 14:00, 19:00 | HH:MM | General posting windows |
| `time_jitter` | 15 | 0-60 | Random ±X min offset on preferred times |
| `posts_per_run` | 1 | 1-5 | Tweets posted per scheduler check |
| `max_posts_per_day` | 3 | 1-10 | Total daily cap |
| `min_gap_minutes` | 60 | 15-240 | Min time between consecutive posts |
| `fallback_interval` | 60 | 15-240 | Between windows, check every X min |
| `fallback_jitter` | 10 | 0-30 | Random ±X min offset on fallback interval |
| `mode` | approved | approved/all | Which tweets to auto-post |

## Scheduler Behavior

### Preferred Times
At startup, each preferred time gets a random jitter applied:
- 09:00 with 15min jitter → actually fires at 08:47 or 09:17
- 14:00 with 15min jitter → actually fires at 13:47 or 14:11
- 19:00 with 15min jitter → actually fires at 18:52 or 19:08

### Fallback Checks
Between preferred times, scheduler checks at jittered intervals:
- 60 min interval with 10 min jitter → fires every 50-70 min
- Ensures tweets don't sit too long if approved outside windows

### Rate Limiting
- `max_posts_per_day`: Hard daily cap
- `min_gap_minutes`: Enforced between consecutive posts
- `posts_per_run`: Limits batch size (1 by default for natural spacing)

### Randomness
- Preferred times: jittered once at startup, consistent for that day
- Fallback interval: jittered at startup, consistent for that day
- No two days run the same schedule
- Prevents bot detection patterns

## API Endpoints

### `GET /api/autopost/status`
Returns today's posting stats.
```json
{
  "enabled": true,
  "posted_today": 1,
  "max_posts": 3,
  "remaining": 2,
  "next_available": "14:11"
}
```

### `POST /api/autopost/post-eligible`
Manually trigger posting. Same logic as scheduler.
```json
{ "posted": 1, "message": "Posted 1 tweet(s)" }
```

### `GET /api/autopost/scheduler/status`
Returns scheduler state.
```json
{ "enabled": true, "running": true, "message": "Auto-posting is active" }
```

## Frontend

### Autopost Banner
- Cyan themed, fixed at top
- Shows: `X/Y posted today · Next: HH:MM · Z remaining`
- "POST NOW" button to manually trigger

### QUICK RESEARCH
- 🔍 Button in header
- Opens modal with topic input, max stories, max proposals
- Triggers `POST /api/research/run`

## Files

- `app.py` — Scheduler logic, API endpoints
- `templates/settings.html` — Auto-Post tab UI
- `templates/index.html` — Autopost banner, QUICK RESEARCH modal
- `static/css/style.css` — Banner styles (cyan autopost, orange archive)
- `data/settings.json` — Settings storage, re-read on each job run

## Testing

Tested: July 15, 2026

## Future Improvements

- Per-user scheduler (multi-tenant)
- Visual schedule calendar in UI
- Post success/failure history log
- Retry failed posts automatically
