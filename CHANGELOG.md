# Changelog

All notable changes to the TweetLoop App and X content pipeline.

---

## [Unreleased]

### Pipeline — Topic-Level Dedup System (2026-07-06)
- **What:** Built a deduplication system that tracks CVEs, model names, and orgs/projects across all briefing and tweet files. Prevents the same stories from being researched, proposed, and posted repeatedly.
- **Why:** The DirtyClone CVE-2026-43503 exploit was proposed on June 30, re-added on July 3, and again on July 5 — each time the agent treated it as "new" news. The text similarity check couldn't catch it because the wording changed.
- **How:** 
  - `X-briefings/briefing_history.json` tracks 121 topics (33 CVEs, 58 models, 30 orgs) across 10 briefings
  - `X-proposed-tweets/tweet_history.json` tracks 148 topics and 254 tweet text snippets across 10 final tweet files
  - `pipelines/dedup_check.py` — manual dedup verification tool
- **Components:**
  - Topic extraction via regex patterns (CVE IDs, model names, org/project names)
  - Recency filter (14-day lookback for briefings, 7-day for tweets)
  - Text similarity check (word overlap detection)
  - Dedup instructions injected into Researcher and Verifier cron prompts

### Pipeline — Cron Prompt Updates (2026-07-06)
- **What:** Updated `daily-tech-pipeline` (Researcher) and `verify-tweets` (Verifier) cron jobs with mandatory dedup steps.
- **Researcher (daily-tech-pipeline):** Now loads `briefing_history.json` before researching, skips topics already covered, and reports excluded topics in a DEDUP SUMMARY section. Also loads `tweet_history.json` to avoid text similarity with previously generated tweets. Updates both dedup files after generating content.
- **Verifier (verify-tweets):** Now checks `tweet_history.json` for topic overlap with the last 7 days and semantic similarity with the last 254 generated tweets. Removes duplicates from the final selection.

### X Integration — Post via xurl (2026-07-06)
- **What:** Added ability to post tweets directly from the app via the `xurl` CLI tool.
- **How:** 
  - `app.py`: Added `post_tweet_via_xurl()` helper and `POST /api/tweets/<id>/post` endpoint
  - `templates/index.html`: Updated "Post to X" button to call the new endpoint with success/error toasts
- **Status:** Ready to use, blocked by missing X API credentials (`client_id`/`client_secret`).

---

## [1.0.0] — Initial Release

### UI — Cyberpunk "Dark Terminal" Theme
- Dark theme with `#34d399` green accents
- Glassmorphism cards, neon glow effects, monospace typography
- Responsive layout

### Backend — Tweet Management
- REST API for managing tweet drafts and finals
- `GET /api/tweets` — list all tweets
- `GET /api/tweets/<id>` — single tweet detail
- `POST /api/tweets` — create draft tweet
- `PUT /api/tweets/<id>` — update tweet
- `DELETE /api/tweets/<id>` — delete tweet
- `PATCH /api/tweets/<id>/toggle-final` — toggle final status

### UI — Tweet Cards
- Inline editing of tweet text (double-click)
- Toggle final status with animated switch
- Delete with confirmation
- Color-coded status (draft vs final)

### UI — Settings Panel
- Date picker for filtering by date
- Password-protected access
- Tweet count statistics per date

### Password Protection
- Basic password authentication for app access
- Credentials stored in `settings.json`

---

*This changelog is maintained for internal tracking. The app is not yet open source.*
