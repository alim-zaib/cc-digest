# CLAUDE.md - Claude Code Daily Digest

## Project Overview

Python CLI tool that fetches Reddit content for Claude Code topics and posts a digest to Discord. Runs on GitHub Actions.

## Code Standards

- Python 3.12, type hints on function signatures.
- No hardcoded secrets or credentials.
- Use `logging` for status and errors.
- Keep dependencies minimal: `praw` for Reddit and `requests` for Discord posting.
- Use raw HTTP for AI providers rather than SDKs.
- Keep functions simple and readable.

## Architecture Rules

- `main.py` orchestrates scrape -> filter -> format -> post.
- `scraper.py` owns Reddit/PRAW access and raises scrape-specific exceptions.
- `filter.py`, `formatter.py`, `ai_summary.py`, and `poster.py` stay independent of Reddit client details.
- `config.py` reads environment-backed configuration.
- Modules communicate with plain dicts and lists.

## Error Handling

- Missing Reddit credentials fail loudly.
- Never post an empty Discord digest when Reddit scraping failed.
- If one subreddit fails but others return posts, log the failure and continue.
- If all configured subreddits fail, raise `ScrapeFailedError` and exit code 1.
- Exit code 0 on success, 1 for scrape failure or Discord posting failure.

## File Structure

```text
main.py           # entry point
config.py         # configuration and env vars
scraper.py        # Reddit scraping via PRAW
filter.py         # post filtering and ranking
ai_summary.py     # optional AI enrichment
formatter.py      # Discord embed building
poster.py         # Discord webhook posting
requirements.txt  # dependencies
```

## Don'ts

- Don't use unauthenticated Reddit `.json` scraping.
- Don't hardcode subreddit names, keywords, thresholds, or credentials outside `config.py`.
- Don't create unnecessary abstractions or base classes.
- Don't add dependencies beyond `praw` and `requests` for core functionality.
- Don't store state between runs.
