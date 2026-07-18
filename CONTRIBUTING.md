# Contributing to TweetLoop

Thank you for your interest in contributing!

## Reporting Issues

- Use GitHub Issues with clear titles
- Include steps to reproduce for bugs
- Specify your environment (Python version, OS, SQLite/Supabase mode)
- Screenshots welcome for UI issues

## Feature Requests

- Open an issue with the `enhancement` label
- Describe the problem and proposed solution
- Note if it applies to OSS mode, paid mode, or both

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly — the app runs in two modes (SQLite offline, Supabase cloud)
5. Commit with clear messages (`git commit -m 'feat: add amazing feature'`)
6. Push and open a PR

## Code Style

- Python: Follow PEP 8, use type hints where practical
- JS: No framework — vanilla JS only
- CSS: BEM-like naming, CSS custom properties for theming
- Commits: [type]: description (feat, fix, docs, style, refactor, test, chore)

## Testing

- Test in both SQLite and Supabase modes
- Verify password auth works
- Check bridge script with sample pipeline output
- Test auto-posting with preferred times and rate limits

## Questions?

Open an issue or discussion. All contributions welcome.
