# TweetLoop App - Master Plan

## Current State (as of 2026-06-30)

### Completed Features
- [x] Flask backend with full CRUD API for tweets
- [x] Password authentication (.env based)
- [x] Frontend UI with cyberpunk "Dark Terminal" theme
- [x] Pipeline bridge (`pipeline_to_app_bridge.py`) — reads `X-proposed-tweets/{date}-final.md` → `data/tweets.json`
- [x] systemd service (`tweeter-reviewer.service`) on port 7777
- [x] Git history with 6 commits
- [x] Data: tweets from 2026-06-29 pipeline run (6 tweets)

### Known Issues
- [ ] Dashboard (hermes-dashboard) can hang when conversation context gets bloated (6+ compressions)

### Planned Features (TODO)
- [ ] **Auto-bridge cron** — run pipeline_to_app_bridge.py after daily pipeline finishes
- [ ] **"Post to X" button** — tweet approved tweets via `xurl` CLI
- [ ] **Bulk import** — scrape all `X-proposed-tweets/` files, not just today's
- [ ] **Edit workflow** — frontend edits sync back to pipeline output
- [ ] **Status dashboard** — show pipeline status, last bridge run, tweet counts
- [ ] **Schedule queue view** — separate timeline for scheduled vs draft tweets

---

## Decision Log
- **2026-06-30:** App uses cyberpunk Dark Terminal theme (#34d399 green accent)
- **2026-06-30:** User wants features built one at a time with confirmation — NOT all at once
- **2026-06-30:** Pipeline format: `## X. [Label]` with pipe separators, blockquote tweets, hashtags, "Why it works:" explanation

---

*Last updated: 2026-06-30*
