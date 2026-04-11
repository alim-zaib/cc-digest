"""Unit tests for filter.py — each filter stage tested independently."""

import time

import pytest

import filter as filter_mod
from filter import filter_posts, _is_recent, _matches_keywords


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_post(
    subreddit: str = "ClaudeCode",
    score: int = 50,
    title: str = "Test post",
    selftext: str = "",
    url: str = "",
    created_utc: float | None = None,
) -> dict:
    """Build a minimal post dict for testing."""
    return {
        "id": url or f"post_{score}",
        "title": title,
        "author": "testuser",
        "score": score,
        "num_comments": 10,
        "created_utc": created_utc if created_utc is not None else time.time(),
        "url": url or f"https://reddit.com/{subreddit}/{score}",
        "selftext": selftext,
        "permalink": f"https://www.reddit.com/r/{subreddit}/comments/abc/test/",
        "link_flair_text": None,
        "subreddit": subreddit,
    }


SUBREDDIT_CONFIG = {
    "ClaudeCode": {"filter_mode": "all", "sort": "hot", "min_score": 5},
    "ClaudeAI": {"filter_mode": "keyword", "sort": "hot", "min_score": 15},
}


# ---------------------------------------------------------------------------
# 1. Recency filter
# ---------------------------------------------------------------------------

class TestRecency:
    def test_recent_post_kept(self):
        post = _make_post(created_utc=time.time() - 3600)  # 1 hour ago
        assert _is_recent(post, 24)

    def test_old_post_dropped(self):
        post = _make_post(created_utc=time.time() - 90000)  # 25 hours ago
        assert not _is_recent(post, 24)

    def test_boundary_just_inside_window(self):
        """Post 1 second inside the window is kept."""
        post = _make_post(created_utc=time.time() - (24 * 3600) + 2)
        assert _is_recent(post, 24)

    def test_boundary_just_outside_window(self):
        """Post 1 second outside the window is dropped."""
        post = _make_post(created_utc=time.time() - (24 * 3600) - 2)
        assert not _is_recent(post, 24)

    def test_recency_in_full_pipeline(self):
        old = _make_post(created_utc=time.time() - 90000, url="https://old")
        new = _make_post(created_utc=time.time(), url="https://new")
        result = filter_posts([old, new], SUBREDDIT_CONFIG)
        assert len(result) == 1
        assert result[0]["url"] == "https://new"


# ---------------------------------------------------------------------------
# 2. Keyword filter
# ---------------------------------------------------------------------------

class TestKeywordMatch:
    def test_keyword_in_title(self):
        post = _make_post(title="Check out Claude Code tips")
        assert _matches_keywords(post, ["claude code"])

    def test_keyword_in_selftext(self):
        post = _make_post(selftext="Using MCP servers for development")
        assert _matches_keywords(post, ["MCP"])

    def test_case_insensitive(self):
        post = _make_post(title="CLAUDE.MD is great")
        assert _matches_keywords(post, ["claude.md"])

    def test_no_match(self):
        post = _make_post(title="Unrelated post about python")
        assert not _matches_keywords(post, ["claude code", "MCP"])

    def test_missing_selftext(self):
        """Post with empty selftext should still check title."""
        post = _make_post(title="New MCP feature", selftext="")
        assert _matches_keywords(post, ["MCP"])

    def test_keyword_subreddit_filtered(self):
        """Keyword-mode subreddit drops non-matching posts."""
        match = _make_post(subreddit="ClaudeAI", score=20, title="Claude Code update", url="https://a")
        no_match = _make_post(subreddit="ClaudeAI", score=20, title="General AI news", url="https://b")
        result = filter_posts([match, no_match], SUBREDDIT_CONFIG)
        assert len(result) == 1
        assert result[0]["url"] == "https://a"

    def test_all_mode_skips_keyword_filter(self):
        """filter_mode: 'all' keeps posts regardless of keywords."""
        post = _make_post(subreddit="ClaudeCode", score=10, title="No keywords here")
        result = filter_posts([post], SUBREDDIT_CONFIG)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# 3. Score threshold
# ---------------------------------------------------------------------------

class TestScoreThreshold:
    def test_above_threshold_kept(self):
        post = _make_post(subreddit="ClaudeCode", score=10)
        result = filter_posts([post], SUBREDDIT_CONFIG)
        assert len(result) == 1

    def test_below_threshold_dropped(self):
        post = _make_post(subreddit="ClaudeCode", score=2)
        result = filter_posts([post], SUBREDDIT_CONFIG)
        assert len(result) == 0

    def test_exactly_at_threshold(self):
        """Score exactly at min_score should be kept (>=)."""
        post = _make_post(subreddit="ClaudeCode", score=5)
        result = filter_posts([post], SUBREDDIT_CONFIG)
        assert len(result) == 1

    def test_different_thresholds_per_subreddit(self):
        cc_post = _make_post(subreddit="ClaudeCode", score=6, title="Claude Code thing", url="https://cc")
        ai_post = _make_post(subreddit="ClaudeAI", score=10, title="Claude Code thing", url="https://ai")
        result = filter_posts([cc_post, ai_post], SUBREDDIT_CONFIG)
        # ClaudeCode min_score=5 (6 passes), ClaudeAI min_score=15 (10 fails)
        assert len(result) == 1
        assert result[0]["subreddit"] == "ClaudeCode"


# ---------------------------------------------------------------------------
# 4. Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_duplicate_urls_removed(self):
        p1 = _make_post(subreddit="ClaudeCode", score=50, url="https://same")
        p2 = _make_post(subreddit="ClaudeAI", score=30, title="Claude Code post", url="https://same")
        result = filter_posts([p1, p2], SUBREDDIT_CONFIG)
        assert len(result) == 1

    def test_different_urls_kept(self):
        p1 = _make_post(score=50, url="https://a")
        p2 = _make_post(score=30, url="https://b")
        result = filter_posts([p1, p2], SUBREDDIT_CONFIG)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# 5. Sort order
# ---------------------------------------------------------------------------

class TestSorting:
    def test_sorted_by_score_descending_within_subreddit(self):
        low = _make_post(subreddit="ClaudeCode", score=10, url="https://low")
        high = _make_post(subreddit="ClaudeCode", score=100, url="https://high")
        result = filter_posts([low, high], SUBREDDIT_CONFIG)
        assert result[0]["score"] == 100
        assert result[1]["score"] == 10

    def test_subreddit_groups_preserved(self):
        """Posts are grouped by subreddit in config order, sorted within each group."""
        cc = _make_post(subreddit="ClaudeCode", score=10, url="https://cc")
        ai = _make_post(subreddit="ClaudeAI", score=200, title="Claude Code post", url="https://ai")
        result = filter_posts([ai, cc], SUBREDDIT_CONFIG)
        # ClaudeCode comes first in config, even though ClaudeAI post has higher score
        assert result[0]["subreddit"] == "ClaudeCode"
        assert result[1]["subreddit"] == "ClaudeAI"


# ---------------------------------------------------------------------------
# Integration: empty input
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_input(self):
        result = filter_posts([], SUBREDDIT_CONFIG)
        assert result == []

    def test_all_posts_filtered_out(self):
        old = _make_post(created_utc=time.time() - 90000)
        result = filter_posts([old], SUBREDDIT_CONFIG)
        assert result == []
