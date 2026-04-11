# SPEC.md — Claude Code Daily Digest

## Overview

A Python CLI tool that scrapes Reddit for Claude Code content daily and posts a formatted digest to Discord. Runs as a scheduled GitHub Actions workflow with manual trigger support. Zero cost, no API keys needed for core functionality.

## Architecture

```
GitHub Actions (cron 7am UK / manual)
         │
         ▼
      main.py  ─── orchestrates pipeline
         │
         ├── scraper.py    → hits Reddit .json endpoints
         ├── filter.py     → score, recency, keyword filtering
         ├── ai_summary.py → optional AI enrichment (passthrough when off)
         ├── formatter.py  → builds Discord embed payloads
         └── poster.py     → POSTs to Discord webhook
```

## Data Flow

```
Reddit .json → raw posts → filtered posts → [AI enrichment] → Discord embeds → webhook POST
```

The AI enrichment step is a passthrough by default. When enabled, it sits between filtering and formatting, enriching post data with summaries and categories before the formatter builds the embeds.

## Module Specifications

### config.py

Single source of truth for all configuration. No hardcoded values anywhere else.

```python
import os

SUBREDDITS = {
    "ClaudeCode": {
        "filter_mode": "all",
        "sort": "hot",
        "min_score": 5,
    },
    "ClaudeAI": {
        "filter_mode": "keyword",
        "sort": "hot",
        "min_score": 15,
    },
    "anthropic": {
        "filter_mode": "keyword",
        "sort": "hot",
        "min_score": 15,
    },
}

KEYWORDS = [
    "claude code", "claude-code", "claudecode",
    "CLAUDE.md", "slash command", "hooks", "statusline",
    "status line", "subagent", "sub-agent", "agent teams",
    "/compact", "MCP", "model context protocol",
    "skills", "claude code tips", ".claude/commands",
    "opusplan", "claude code skill",
]

TIME_WINDOW_HOURS = 24
POST_LIMIT_PER_SUBREDDIT = 25
REQUEST_DELAY_SECONDS = 2
USER_AGENT = "ClaudeCodeDigest/1.0"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

ENABLE_AI = False
AI_PROVIDER = "gemini"
AI_API_KEY = os.environ.get("AI_API_KEY", "")
```

### scraper.py

Handles all Reddit interaction via the public `.json` endpoint.

**`scrape_subreddits(subreddit_config: dict) -> list[dict]`**

For each subreddit:
- Build URL: `https://www.reddit.com/r/{subreddit}/{sort}.json`
- Set params: `limit={POST_LIMIT_PER_SUBREDDIT}`, `raw_json=1`, `t=day`
- Set headers: `User-Agent: {USER_AGENT}`
- GET request with `REQUEST_DELAY_SECONDS` pause between subreddits
- Parse `response.json()["data"]["children"]`
- Extract and return a list of post dicts

**Post dict schema:**
```python
{
    "id": str,
    "title": str,
    "author": str,
    "score": int,
    "num_comments": int,
    "created_utc": float,
    "url": str,
    "selftext": str,          # first 500 chars only
    "permalink": str,          # full reddit permalink
    "link_flair_text": str,    # nullable
    "subreddit": str,          # source subreddit name
}
```

**Error handling — never crash the pipeline for one failed subreddit:**
- HTTP 429: log warning, skip subreddit
- HTTP 403/404: log warning, skip subreddit
- Connection error: log error, skip subreddit
- JSON decode error: log error, skip subreddit

### filter.py

**`filter_posts(posts: list[dict], config: dict) -> list[dict]`**

Applies filters in order:

1. **Recency**: drop posts where `created_utc` is older than `TIME_WINDOW_HOURS` ago
2. **Keyword match**: for subreddits with `filter_mode: "keyword"`, check title and selftext against `KEYWORDS` list (case-insensitive substring match). Subreddits with `filter_mode: "all"` skip this.
3. **Score threshold**: drop posts below the subreddit's `min_score`
4. **Deduplication**: remove posts with identical URLs (catches cross-posts)
5. **Sort**: order by score descending within each subreddit group

### ai_summary.py

**`summarise(posts: list[dict]) -> dict | None`**

When `ENABLE_AI` is `False`: returns `None`. The formatter skips AI sections.

When `ENABLE_AI` is `True`: sends post data to configured provider and returns:

```python
{
    "tldr": str,                    # one paragraph daily summary
    "categories": {                 # post ID to category
        "abc123": "new_feature",    # options: new_feature, tip, bug, workflow, tool, discussion
    },
    "top_picks": [                  # top 3 most actionable posts
        {"id": "abc123", "reason": "..."},
    ],
    "summaries": {                  # post ID to one-line summary
        "abc123": "...",
    },
}
```

**Provider routing:**
- Factory function selects provider based on `AI_PROVIDER` config
- Each provider (gemini, groq, anthropic) has its own function
- All return the same schema
- API keys from environment variables

### formatter.py

**`build_embeds(posts: list[dict], ai_data: dict | None) -> list[dict]`**

Builds Discord webhook payload(s).

**Without AI:**
- Title embed: "🔥 Claude Code Digest — {date}"
- Posts grouped by subreddit
- Each post: `⬆️ {score} | 💬 {comments}\n{title}\n{link}`
- Footer: "Next digest at 7am UK time"

**With AI:**
- Same as above plus TL;DR in description, category emoji per post, one-line summary under each title, "⭐ Top Picks" section

**Discord limits to respect:**
- Max 10 embeds per message
- Max 6000 chars total across all embeds
- Max 25 fields per embed
- Max 1024 chars per field value
- If over limits: truncate lowest-scored posts first, then split into multiple payloads

### poster.py

**`send_to_discord(payloads: list[dict], webhook_url: str) -> bool`**

- POST each payload to webhook_url with `Content-Type: application/json`
- Return `True` on all 2xx responses
- Handle 429 with `Retry-After` header
- Log and return `False` on failure

## GitHub Actions Workflow

`.github/workflows/digest.yml`:

- Trigger: cron `0 6 * * *` UTC (7am BST) + `workflow_dispatch` for manual
- Runner: `ubuntu-latest`
- Steps: checkout, setup Python 3.12, pip install, run `main.py`
- Env vars from secrets: `DISCORD_WEBHOOK_URL`, `AI_API_KEY`

## Dependencies

`requirements.txt`:
```
requests>=2.31.0
```

No other dependencies for core. AI providers use raw HTTP requests to avoid heavy SDKs.

## Error Handling Philosophy

- Never crash the pipeline for a single failure
- Log everything to stdout (GitHub Actions captures it)
- All subreddits fail → send "no data" message to Discord so you know it ran
- Discord webhook fails → exit code 1 so Actions marks it failed
- AI fails → log warning, fall back to non-AI formatting

## Testing

- `scraper.py`: mock HTTP responses, verify parsing handles missing/null fields
- `filter.py`: unit test each filter stage with fixture data
- `formatter.py`: verify Discord embed limits respected
- `poster.py`: mock webhook, verify retry logic
- `main.py`: integration test with all mocks

## Future AI Expansion

To add a new AI provider:
1. Add function in `ai_summary.py` matching existing signature
2. Add to factory function routing
3. Add API key env var to GitHub Actions workflow
4. Document free tier limits in README

No other modules change — the filter → AI → formatter interface is stable.
