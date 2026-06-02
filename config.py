"""Single source of truth for all configuration."""

import os

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

REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

ENABLE_AI = False
AI_PROVIDER = "gemini"
AI_API_KEY = os.environ.get("AI_API_KEY", "")
