"""Unit tests for scraper.py - PRAW Reddit scrape handling."""

from unittest.mock import Mock

import pytest

import scraper
from scraper import (
    MissingRedditCredentialsError,
    ScrapeFailedError,
    get_reddit_client,
    scrape_subreddits,
)


class FakeAuthor:
    """Minimal author object with Redditor-like string behavior."""

    def __str__(self) -> str:
        return "testuser"


class FakeSubmission:
    """Minimal PRAW Submission stand-in."""

    def __init__(self, post_id: str = "abc123") -> None:
        self.id = post_id
        self.title = "Test post"
        self.author = FakeAuthor()
        self.score = 10
        self.num_comments = 2
        self.created_utc = 1_700_000_000
        self.url = f"https://reddit.com/{post_id}"
        self.selftext = "x" * 600
        self.permalink = f"/r/ClaudeCode/comments/{post_id}/test/"
        self.link_flair_text = "Discussion"


class FakeSubreddit:
    """Fake subreddit listing methods used by scraper tests."""

    def __init__(self, submissions=None, error: Exception | None = None) -> None:
        self.submissions = submissions if submissions is not None else []
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def hot(self, **kwargs):
        self.calls.append(("hot", kwargs))
        if self.error:
            raise self.error
        return self.submissions

    def new(self, **kwargs):
        self.calls.append(("new", kwargs))
        if self.error:
            raise self.error
        return self.submissions

    def top(self, **kwargs):
        self.calls.append(("top", kwargs))
        if self.error:
            raise self.error
        return self.submissions


class FakeReddit:
    """Fake PRAW Reddit client."""

    def __init__(self, subreddits: dict[str, FakeSubreddit]) -> None:
        self.subreddits = subreddits

    def subreddit(self, name: str) -> FakeSubreddit:
        return self.subreddits[name]


def _config(*subreddits: str, sort: str = "hot", **settings) -> dict:
    """Build minimal subreddit config."""
    merged = {"sort": sort, **settings}
    return {subreddit: dict(merged) for subreddit in subreddits}


class TestCredentials:
    def test_missing_reddit_credentials_raise_clear_error(self, monkeypatch):
        monkeypatch.setattr(scraper.config, "REDDIT_CLIENT_ID", "")
        monkeypatch.setattr(scraper.config, "REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setattr(scraper.config, "REDDIT_USER_AGENT", "")

        with pytest.raises(MissingRedditCredentialsError) as exc:
            get_reddit_client()

        assert "Missing Reddit credentials" in str(exc.value)
        assert "REDDIT_CLIENT_ID" in str(exc.value)
        assert "REDDIT_USER_AGENT" in str(exc.value)
        assert exc.value.failures == []

    def test_get_reddit_client_uses_env_backed_config(self, monkeypatch):
        monkeypatch.setattr(scraper.config, "REDDIT_CLIENT_ID", "client-id")
        monkeypatch.setattr(scraper.config, "REDDIT_CLIENT_SECRET", "client-secret")
        monkeypatch.setattr(scraper.config, "REDDIT_USER_AGENT", "test-agent")
        mock_reddit = Mock(return_value="reddit")
        monkeypatch.setattr(scraper.praw, "Reddit", mock_reddit)

        assert get_reddit_client() == "reddit"
        mock_reddit.assert_called_once_with(
            client_id="client-id",
            client_secret="client-secret",
            user_agent="test-agent",
        )


class TestSubmissionExtraction:
    def test_praw_submission_converts_to_expected_post_shape(self):
        reddit = FakeReddit({"ClaudeCode": FakeSubreddit([FakeSubmission()])})

        posts = scrape_subreddits(_config("ClaudeCode"), reddit=reddit)

        assert posts == [
            {
                "id": "abc123",
                "title": "Test post",
                "author": "testuser",
                "score": 10,
                "num_comments": 2,
                "created_utc": 1_700_000_000,
                "url": "https://reddit.com/abc123",
                "selftext": "x" * 500,
                "permalink": "https://www.reddit.com/r/ClaudeCode/comments/abc123/test/",
                "link_flair_text": "Discussion",
                "subreddit": "ClaudeCode",
            }
        ]


class TestSortModes:
    def test_hot_sort_uses_hot_listing(self):
        subreddit = FakeSubreddit([FakeSubmission()])
        reddit = FakeReddit({"ClaudeCode": subreddit})

        scrape_subreddits(_config("ClaudeCode", sort="hot"), reddit=reddit)

        assert subreddit.calls == [("hot", {"limit": scraper.config.POST_LIMIT_PER_SUBREDDIT})]

    def test_new_sort_uses_new_listing(self):
        subreddit = FakeSubreddit([FakeSubmission()])
        reddit = FakeReddit({"ClaudeCode": subreddit})

        scrape_subreddits(_config("ClaudeCode", sort="new"), reddit=reddit)

        assert subreddit.calls == [("new", {"limit": scraper.config.POST_LIMIT_PER_SUBREDDIT})]

    def test_top_sort_defaults_to_day_time_filter(self):
        subreddit = FakeSubreddit([FakeSubmission()])
        reddit = FakeReddit({"ClaudeCode": subreddit})

        scrape_subreddits(_config("ClaudeCode", sort="top"), reddit=reddit)

        assert subreddit.calls == [
            ("top", {"time_filter": "day", "limit": scraper.config.POST_LIMIT_PER_SUBREDDIT})
        ]

    def test_top_sort_uses_configured_time_filter(self):
        subreddit = FakeSubreddit([FakeSubmission()])
        reddit = FakeReddit({"ClaudeCode": subreddit})

        scrape_subreddits(_config("ClaudeCode", sort="top", time_filter="week"), reddit=reddit)

        assert subreddit.calls == [
            ("top", {"time_filter": "week", "limit": scraper.config.POST_LIMIT_PER_SUBREDDIT})
        ]


class TestScrapeFailures:
    def test_all_subreddit_fetches_fail_raise_clear_error(self):
        reddit = FakeReddit(
            {
                "ClaudeCode": FakeSubreddit(error=ValueError("api denied")),
                "ClaudeAI": FakeSubreddit(error=ValueError("api denied")),
            }
        )

        with pytest.raises(ScrapeFailedError) as exc:
            scrape_subreddits(_config("ClaudeCode", "ClaudeAI"), reddit=reddit)

        assert "Reddit scraping failed for all subreddits" in str(exc.value)
        assert "Refusing to post empty digest" in str(exc.value)
        assert "r/ClaudeCode (hot) api denied" in str(exc.value)
        assert "r/ClaudeAI (hot) api denied" in str(exc.value)
        assert exc.value.failures == [
            {
                "subreddit": "ClaudeCode",
                "sort": "hot",
                "status_code": None,
                "message": "api denied",
            },
            {
                "subreddit": "ClaudeAI",
                "sort": "hot",
                "status_code": None,
                "message": "api denied",
            },
        ]

    def test_partial_failure_with_posts_returns_scraped_posts(self):
        reddit = FakeReddit(
            {
                "ClaudeCode": FakeSubreddit(error=ValueError("api denied")),
                "ClaudeAI": FakeSubreddit([FakeSubmission("def456")]),
            }
        )

        posts = scrape_subreddits(_config("ClaudeCode", "ClaudeAI"), reddit=reddit)

        assert len(posts) == 1
        assert posts[0]["id"] == "def456"
        assert posts[0]["subreddit"] == "ClaudeAI"

    def test_zero_posts_after_failure_raises(self):
        reddit = FakeReddit(
            {
                "ClaudeCode": FakeSubreddit(error=ValueError("api denied")),
                "ClaudeAI": FakeSubreddit([]),
            }
        )

        with pytest.raises(ScrapeFailedError) as exc:
            scrape_subreddits(_config("ClaudeCode", "ClaudeAI"), reddit=reddit)

        assert "returned 0 posts after Reddit failures" in str(exc.value)
        assert "r/ClaudeCode (hot) api denied" in str(exc.value)

    def test_zero_posts_without_failures_is_valid_empty_scrape(self):
        reddit = FakeReddit(
            {
                "ClaudeCode": FakeSubreddit([]),
                "ClaudeAI": FakeSubreddit([]),
            }
        )

        posts = scrape_subreddits(_config("ClaudeCode", "ClaudeAI"), reddit=reddit)

        assert posts == []

    def test_unsupported_sort_is_recorded_as_subreddit_failure(self):
        reddit = FakeReddit({"ClaudeCode": FakeSubreddit([FakeSubmission()])})

        with pytest.raises(ScrapeFailedError) as exc:
            scrape_subreddits(_config("ClaudeCode", sort="rising"), reddit=reddit)

        assert "Unsupported Reddit sort 'rising'" in str(exc.value)
