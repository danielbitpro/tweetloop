# Changelog

All notable user-facing changes to TweetLoop.

## [Unreleased]

### Added
- **FETCH button** — Auto-import today's pipeline file from a configured directory
- **Pipeline Output Directory** setting — Configure where your pipeline saves `*-final.md` files
- Integration section with sample output file in README

### Fixed
- Missing `catch` block in import handler (caused silent failures)
- Browser cache serving stale HTML after updates

## [1.1.0] — 2026-07-21

### Added
- 🔄 **FETCH button** in header for automated pipeline file import
- 📥 **IMPORT button** — Drag-and-drop `*-final.md` files for one-time imports
- 🔄 **Pipeline Output Directory** setting in Settings → Pipeline
- Full pipeline integration documentation in README with sample output file
- `GET /api/fetch/status` — Check if today's pipeline file exists
- `POST /api/fetch` — Read, parse, and import today's pipeline file

### Fixed
- Import parser now handles both blockquote and table formats
- Import parser matches `**Tweet:**` anywhere in line (inline format support)
- Schedule time picker: 15:00 no longer shows as 3 AM (removed AM/PM dropdown)
- Schedule display formatting — shows `Jul 22 at 3:00 PM` instead of raw timestamp
- Past date validation — prevents scheduling tweets for dates in the past
- Delete tweet — now properly sends session cookie
- Password authentication — rejects wrong passwords
- Quick Research — opens Google Search with AI Overview in OSS mode
- Emoji picker — fixed z-index (now appears above modals)
- Header layout — branding and buttons now centered
- Login overlay — solid black background (no transparency)

## [1.0.0] — 2026-07-18

### Features
- Tweet CRUD with status workflow (draft → approved → scheduled → posted → manual)
- Inline editing of tweet text
- X-style scheduling GUI with date/time picker
- Image paste support (uploads to server)
- Scheduled tweet priority in auto-posting
- Auto-posting system with preferred times, rate limiting, daily caps
- Configurable research sources (custom accounts, keywords, time windows)
- Manual research trigger from dashboard
- Monthly archive with download and purge
- Search, filter, and bulk actions
- Export (raw, CSV, pipeline format)
- Emoji picker in tweet composition
- Pipeline bridge for auto-importing tweets
- Password authentication with session management
- SQLite storage with WAL mode and indexing
- Dark Terminal dark terminal theme
- HTTPS support with auto-detecting certs
- Full favicon pack

### Infrastructure
- Dual auth mode (password / Supabase JWT)
- Dual DB mode (SQLite / PostgreSQL)
- Pipeline bridge with deduplication and retry logic
- One-command launcher (start.sh)
- Systemd service template

---

*Last updated: July 21, 2026*
