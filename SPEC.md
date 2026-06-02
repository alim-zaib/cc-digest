# SPEC.md - Claude Code Daily Digest

## Overview

`cc-digest` is a Python CLI tool that fetches selected Reddit subreddits through authenticated PRAW access, filters the posts, formats a Discord digest, and sends it through a Discord webhook.

## Data Flow

```text
PRAW -> raw post dicts -> filtered posts -> optional AI enrichment -> Discord embeds -> webhook POST
```

## Configuration

`config.py` is the single source of truth for runtime configuration.

Environment variables:

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
DISCORD_WEBHOOK_URL
AI_API_KEY
```

Subreddit settings:

```python
SUBREDDITS = {
    "ClaudeCode": {
        "filter_mode": "all",
        "sort": "hot",
        "min_score": 200,
    },
    "ClaudeAI": {
        "filter_mode": "keyword",
        "sort": "hot",
        "min_score": 500,
    },
}
```

Supported Reddit sort modes:

- `hot`
- `new`
- `top`

For `top`, use `time_filter` in the subreddit settings to override the default `day`.

## scraper.py

Public functions and exceptions:

- `get_reddit_client() -> praw.Reddit`
- `scrape_subreddits(subreddit_config: dict, reddit: praw.Reddit | None = None) -> list[dict]`
- `ScrapeFailedError`
- `MissingRedditCredentialsError`

`get_reddit_client()` builds a PRAW client from environment-backed config and raises `MissingRedditCredentialsError` if required values are missing.

`scrape_subreddits()` fetches each configured subreddit with the configured sort and `POST_LIMIT_PER_SUBREDDIT`.

Expected post dict shape:

```python
{
    "id": str,
    "title": str,
    "author": str,
    "score": int,
    "num_comments": int,
    "created_utc": float,
    "url": str,
    "selftext": str,
    "permalink": str,
    "link_flair_text": str | None,
    "subreddit": str,
}
```

Scrape failures are tracked per subreddit with:

- subreddit name
- sort type
- HTTP status code when available
- error message

Failure behavior:

- Missing Reddit credentials fail before scraping.
- One failed subreddit is logged and skipped if other subreddits return posts.
- All configured subreddit fetches failing raises `ScrapeFailedError`.
- Zero posts after one or more scrape failures raises `ScrapeFailedError` to avoid posting an empty digest caused by Reddit access problems.

## Downstream Modules

- `filter.py`: applies recency, keyword, score, deduplication, and ordering filters.
- `ai_summary.py`: optional passthrough enrichment layer.
- `formatter.py`: builds Discord webhook payloads.
- `poster.py`: posts payloads to Discord with retry handling for Discord rate limits.

## GitHub Actions

`.github/workflows/digest.yml` runs on a daily schedule and `workflow_dispatch`.

Required secrets:

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
DISCORD_WEBHOOK_URL
```

Optional secret:

```text
AI_API_KEY
```

## Dependencies

```text
praw>=7.7.1
requests>=2.31.0
```
