# CLAUDE.md — Claude Code Daily Digest

## Project Overview

Python CLI tool that scrapes Reddit for Claude Code content and posts a digest to Discord. Runs on GitHub Actions.

## Code Standards

- Python 3.12, type hints on all function signatures
- No hardcoded values — everything lives in `config.py`
- Use `logging` module, never `print()` for status/error output
- All functions have docstrings (one-liner is fine for simple functions)
- Explicit error handling — never silently swallow exceptions
- No classes unless genuinely needed — prefer functions and simple data structures (dicts, dataclasses)
- Keep dependencies minimal — only `requests` for core. No heavy SDKs.
- Use raw HTTP for AI providers rather than their SDKs

## Architecture Rules

- `main.py` is the orchestrator — it calls modules in sequence and handles top-level errors
- Each module has a single responsibility and a clear public interface
- Modules communicate via plain dicts and lists — no custom objects passed between modules
- `config.py` is imported by other modules, never the reverse
- The AI layer (`ai_summary.py`) must be a clean passthrough when disabled — no conditional logic leaking into other modules

## Error Handling

- Never crash the full pipeline because one subreddit or one API call failed
- Log the error, skip the failed item, continue with the rest
- If everything fails, still send a "no data" message to Discord
- Exit code 0 on success, 1 only if Discord posting fails entirely

## File Structure

```
main.py           # entry point
config.py         # all configuration
scraper.py        # Reddit .json scraping
filter.py         # post filtering and ranking
ai_summary.py     # optional AI enrichment
formatter.py      # Discord embed building
poster.py         # Discord webhook posting
requirements.txt  # dependencies
```

## Don'ts

- Don't use PRAW or any Reddit API wrapper — we use the `.json` endpoint directly
- Don't use async — the script makes 3 HTTP requests total, async adds complexity for no gain
- Don't create unnecessary abstractions or base classes
- Don't add dependencies beyond `requests` for core functionality
- Don't hardcode subreddit names, keywords, or thresholds outside `config.py`
- Don't store any state between runs — each run is fully independent
