# Changelog

All notable user-facing changes to TweetLoop.

## [Unreleased]

### Added
- Logout button for session invalidation
- Login session persistence (30-day cookies)
- Centered header layout with terminal bar
- Solid black login overlay (no transparency)

### Fixed
- Bridge script no longer overwrites manually edited tweets
- Bridge deduplication preserves manual edits and status changes
- CSS cache busting for live theme updates
- Header alignment — branding and buttons now centered

## [1.0.0] — Initial Release

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

*Last updated: July 18, 2026*
