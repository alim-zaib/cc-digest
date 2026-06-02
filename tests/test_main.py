"""Unit tests for main.py orchestration failure paths."""

from unittest.mock import patch

import main
import scraper


def test_scrape_failure_exits_before_discord(monkeypatch):
    failures = [
        {
            "subreddit": "ClaudeCode",
            "sort": "hot",
            "status_code": 403,
            "message": "Forbidden",
        }
    ]
    error = scraper.ScrapeFailedError(
        "Reddit scraping failed for all subreddits. Refusing to post empty digest. "
        "Failures: r/ClaudeCode (hot) HTTP 403",
        failures,
    )
    monkeypatch.setattr(main.config, "DISCORD_WEBHOOK_URL", "https://discord.test/webhook")

    with patch("main.scraper.get_reddit_client", return_value="reddit"), patch(
        "main.scraper.scrape_subreddits", side_effect=error
    ), patch(
        "main.poster.send_to_discord"
    ) as mock_post:
        assert main.main() == 1

    mock_post.assert_not_called()


def test_missing_reddit_credentials_exits_before_discord(monkeypatch):
    error = scraper.MissingRedditCredentialsError(["REDDIT_CLIENT_ID"])
    monkeypatch.setattr(main.config, "DISCORD_WEBHOOK_URL", "https://discord.test/webhook")

    with patch("main.scraper.get_reddit_client", side_effect=error), patch(
        "main.scraper.scrape_subreddits"
    ) as mock_scrape, patch("main.poster.send_to_discord") as mock_post:
        assert main.main() == 1

    mock_scrape.assert_not_called()
    mock_post.assert_not_called()
