# Claude Code Daily Digest

A lightweight Python tool that scrapes Reddit daily for Claude Code updates, tips, and new features — then delivers a formatted digest straight to your Discord channel via webhook.

Runs on GitHub Actions at 7am UK time. No API keys needed for Reddit. No AI required (optional AI summarisation can be enabled later). Your PC doesn't need to be on.

## How It Works

1. GitHub Actions triggers the script daily at 7am UK time (or manually via the "Run workflow" button)
2. The script hits Reddit's public `.json` endpoints — no API key needed
3. It scrapes **all** posts from `r/ClaudeCode`, and **keyword-filtered** Claude Code posts from `r/ClaudeAI` and `r/anthropic`
4. Posts are filtered by minimum score and recency (last 24 hours)
5. Results are ranked by engagement, formatted into a clean Discord embed, and POSTed to your webhook

## What You'll See in Discord

```
🔥 Claude Code Digest — 11 Apr 2026

📌 r/ClaudeCode (5 posts)
━━━━━━━━━━━━━━━━━━━━━━━━━━
⬆️ 847 | 💬 203
Opus 4.6 effort parameter changes tool call behaviour
https://reddit.com/r/ClaudeCode/...

⬆️ 412 | 💬 89
PSA: /statusline exists and it's a game changer
https://reddit.com/r/ClaudeCode/...

📌 r/ClaudeAI (2 Claude Code posts)
━━━━━━━━━━━━━━━━━━━━━━━━━━
⬆️ 1.2k | 💬 341
Claude Code agent teams just shipped — here's how to use them
https://reddit.com/r/ClaudeAI/...
```

## Prerequisites

- Python 3.10+
- A Discord server where you can create a webhook
- A GitHub account (for Actions scheduling)

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/claude-code-digest.git
cd claude-code-digest
```

### 2. Create a Discord webhook

1. Open Discord and go to the channel where you want the digest
2. Click the gear icon (Edit Channel) → Integrations → Webhooks
3. Click "New Webhook"
4. Name it something like "Claude Code Digest"
5. Copy the webhook URL — you'll need this in step 4

### 3. Configure the scraper

Edit `config.py` to adjust your preferences:

```python
# Subreddits to scrape
SUBREDDITS = {
    "ClaudeCode": {
        "filter_mode": "all",  # grab everything
        "sort": "hot",
        "min_score": 5,
    },
    "ClaudeAI": {
        "filter_mode": "keyword",  # only Claude Code related posts
        "sort": "hot",
        "min_score": 15,
    },
    "anthropic": {
        "filter_mode": "keyword",
        "sort": "hot",
        "min_score": 15,
    },
}

# Keywords to match in filtered subreddits (case-insensitive)
KEYWORDS = [
    "claude code", "claude-code", "claudecode",
    "CLAUDE.md", "slash command", "hooks", "statusline",
    "status line", "subagent", "sub-agent", "agent teams",
    "/compact", "MCP", "model context protocol",
    "skills", "claude code tips", ".claude/commands",
    "opusplan", "claude code skill",
]

# Post filters
TIME_WINDOW_HOURS = 24
POST_LIMIT_PER_SUBREDDIT = 25

# AI summarisation (off by default)
ENABLE_AI = False
AI_PROVIDER = "gemini"  # "gemini", "groq", or "anthropic"
```

### 4. Add your Discord webhook as a GitHub secret

1. Go to your repo on GitHub → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `DISCORD_WEBHOOK_URL`
4. Value: paste your Discord webhook URL from step 2
5. Click "Add secret"

If you plan to use AI summarisation later, also add:
- `GEMINI_API_KEY` or `GROQ_API_KEY` or `ANTHROPIC_API_KEY` (depending on your choice)

### 5. Push to GitHub and you're done

The GitHub Actions workflow is already configured in `.github/workflows/digest.yml`. It will run automatically at 7am UK time every day.

To test it immediately, go to Actions → "Claude Code Digest" → "Run workflow" → click the green button.

## Manual Run (Local)

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="your_webhook_url_here"
python main.py
```

## Project Structure

```
claude-code-digest/
├── main.py                  # Entry point — orchestrates scrape → filter → format → post
├── scraper.py               # Reddit scraping via .json endpoints
├── filter.py                # Score, recency, and keyword filtering
├── formatter.py             # Discord embed formatting
├── poster.py                # Discord webhook POST logic
├── ai_summary.py            # Optional AI summarisation (disabled by default)
├── config.py                # All configuration in one place
├── requirements.txt         # Python dependencies
├── .github/
│   └── workflows/
│       └── digest.yml       # GitHub Actions cron + manual trigger
├── .claude/
│   └── commands/            # Claude Code slash commands for building this
│       ├── step-1.md
│       ├── step-2.md
│       ├── step-3.md
│       ├── step-4.md
│       ├── step-5.md
│       └── step-6.md
├── CLAUDE.md                # Claude Code rules for this project
├── SPEC.md                  # Technical specification
└── README.md                # This file
```

## Future: AI Summarisation

The script is structured so AI is a simple toggle. When enabled:

1. The scraped posts pass through an AI processing step before formatting
2. The AI can summarise long posts, categorise them (new feature / tip / bug / workflow / tool), highlight the most actionable items, and generate a TL;DR paragraph
3. Set `ENABLE_AI = True` in `config.py` and add your API key as a GitHub secret
4. Supported providers: Google Gemini (free tier), Groq (free tier), Anthropic (paid)

## Adjusting the Schedule

The cron in `.github/workflows/digest.yml` is set to `0 6 * * *` UTC which is 7am BST (UK summer time, March–October). When clocks go back to GMT (October–March), change it to `0 7 * * *` UTC to keep it at 7am UK time.

## Rate Limits

Reddit's `.json` endpoint is unofficial and rate-limited. The script:
- Sets a custom User-Agent header
- Adds a 2-second delay between requests
- Only makes 3 requests total (one per subreddit) so you're well within limits
