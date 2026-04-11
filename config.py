"""Single source of truth for all configuration."""

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
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

ENABLE_AI = False
AI_PROVIDER = "gemini"
AI_API_KEY = os.environ.get("AI_API_KEY", "")
