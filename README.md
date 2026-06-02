# Claude Code Daily Digest

A lightweight Python tool that fetches Reddit posts about Claude Code, filters them, formats a daily digest, and posts it to Discord via webhook.

It runs on GitHub Actions at 7am UK time and can also be triggered manually. Reddit access uses authenticated PRAW, so you need Reddit API credentials.

## How It Works

1. GitHub Actions triggers `python main.py`.
2. The scraper uses PRAW with `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `REDDIT_USER_AGENT`.
3. Configured subreddits are fetched using their configured sort mode and post limit.
4. Posts are filtered by recency, keywords, score, and duplicate URL.
5. The digest is formatted into Discord embeds and sent to the configured webhook.

## Prerequisites

- Python 3.10+
- A Discord server where you can create a webhook
- A Reddit account
- A Reddit API app
- A GitHub account for scheduled Actions runs

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Reddit API Credentials

1. Go to <https://www.reddit.com/prefs/apps>.
2. Click "create another app" or "create app".
3. Choose `script` as the app type.
4. Give it a name such as `cc-digest`.
5. Use any valid redirect URI, for example `http://localhost:8080`.
6. Save the app.
7. Copy the client ID from under the app name and the client secret from the app details.

Use a descriptive user agent, for example:

```text
python:cc-digest:v1.0.0 (by /u/CarelessGarden2799)
```

Never commit Reddit credentials, Discord webhooks, or AI API keys.

### 3. Create a Discord Webhook

1. Open Discord and go to the channel where you want the digest.
2. Open channel settings, then Integrations, then Webhooks.
3. Create a new webhook.
4. Copy the webhook URL.

### 4. Configure GitHub Secrets

Add these repository secrets in GitHub under Settings, Secrets and variables, Actions:

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
DISCORD_WEBHOOK_URL
AI_API_KEY
```

`AI_API_KEY` is only needed if AI summarisation is enabled.

### 5. Configure Subreddits

Edit `config.py` to adjust subreddit behavior:

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

Supported Reddit sort modes are `hot`, `new`, and `top`. For `top`, add `time_filter` if you want something other than the default `day`.

## Local Run With `.env`

Copy `.env.example` to `.env` and fill in the values. `.env` is ignored by Git.

On macOS/Linux:

```bash
while IFS='=' read -r name value; do
    [ -z "$name" ] && continue
    case "$name" in \#*) continue ;; esac
    export "$name=$value"
done < .env
python main.py
```

On PowerShell:

```powershell
Get-Content .env | Where-Object { $_ -and $_ -notmatch '^#' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    Set-Item -Path "Env:$name" -Value $value
}
python main.py
```

## GitHub Actions

The workflow lives at `.github/workflows/digest.yml`. It runs daily and supports manual `workflow_dispatch` runs.

To test it, go to Actions, choose "Claude Code Digest", and run the workflow manually.

## Project Structure

```text
main.py                  # Orchestrates scrape -> filter -> format -> post
scraper.py               # Reddit access via PRAW
filter.py                # Score, recency, keyword filtering, deduplication
formatter.py             # Discord embed formatting
poster.py                # Discord webhook posting
ai_summary.py            # Optional AI summarisation
config.py                # Configuration and environment variables
requirements.txt         # Python dependencies
.github/workflows/       # GitHub Actions workflow
```

## Failure Behavior

- Missing Reddit credentials fail loudly and exit with code 1.
- If all configured subreddit fetches fail, no Discord message is posted.
- If some subreddit fetches fail but others return posts, failures are logged and the digest continues with the successful results.
- If Discord posting fails, the run exits with code 1.
