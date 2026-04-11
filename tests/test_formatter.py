"""Unit tests for formatter.py — Discord embed building and limit enforcement."""

import time

import pytest

from formatter import (
    build_embeds,
    _format_score,
    _post_field_value,
    _estimate_embed_chars,
    MAX_EMBEDS_PER_MESSAGE,
    MAX_TOTAL_CHARS,
    MAX_FIELD_VALUE_CHARS,
)


def _make_post(
    subreddit: str = "ClaudeCode",
    score: int = 50,
    num_comments: int = 10,
    title: str = "Test post",
    permalink: str = "",
) -> dict:
    """Build a minimal post dict for testing."""
    return {
        "id": f"post_{score}",
        "title": title,
        "author": "testuser",
        "score": score,
        "num_comments": num_comments,
        "created_utc": time.time(),
        "url": permalink or f"https://reddit.com/{subreddit}/{score}",
        "selftext": "",
        "permalink": permalink or f"https://www.reddit.com/r/{subreddit}/comments/abc/test/",
        "link_flair_text": None,
        "subreddit": subreddit,
    }


# ---------------------------------------------------------------------------
# Score formatting
# ---------------------------------------------------------------------------

class TestFormatScore:
    def test_below_thousand(self):
        assert _format_score(847) == "847"

    def test_exactly_thousand(self):
        assert _format_score(1000) == "1.0k"

    def test_above_thousand(self):
        assert _format_score(1200) == "1.2k"

    def test_zero(self):
        assert _format_score(0) == "0"


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_no_posts_returns_single_payload(self):
        payloads = build_embeds([], None)
        assert len(payloads) == 1

    def test_no_posts_has_one_embed(self):
        payloads = build_embeds([], None)
        assert len(payloads[0]["embeds"]) == 1

    def test_no_posts_message(self):
        payloads = build_embeds([], None)
        embed = payloads[0]["embeds"][0]
        assert "No Claude Code activity" in embed["description"]

    def test_no_posts_has_footer(self):
        payloads = build_embeds([], None)
        embed = payloads[0]["embeds"][0]
        assert embed["footer"]["text"] == "Next digest at 7am UK time"

    def test_no_posts_title_has_date(self):
        payloads = build_embeds([], None)
        embed = payloads[0]["embeds"][0]
        assert "Digest" in embed["title"]
        # Should contain a date like "11 Apr 2026"
        assert "202" in embed["title"]


# ---------------------------------------------------------------------------
# Basic embed structure
# ---------------------------------------------------------------------------

class TestEmbedStructure:
    def test_single_subreddit_creates_title_plus_group_embeds(self):
        posts = [_make_post(subreddit="ClaudeCode", score=50)]
        payloads = build_embeds(posts, None)
        embeds = payloads[0]["embeds"]
        # Title embed + 1 subreddit embed
        assert len(embeds) == 2

    def test_two_subreddits_creates_three_embeds(self):
        posts = [
            _make_post(subreddit="ClaudeCode", score=50, permalink="https://a"),
            _make_post(subreddit="ClaudeAI", score=30, permalink="https://b"),
        ]
        payloads = build_embeds(posts, None)
        embeds = payloads[0]["embeds"]
        # Title embed + 2 subreddit embeds
        assert len(embeds) == 3

    def test_title_embed_has_digest_title(self):
        posts = [_make_post()]
        payloads = build_embeds(posts, None)
        title_embed = payloads[0]["embeds"][0]
        assert "Claude Code Digest" in title_embed["title"]

    def test_footer_on_last_embed(self):
        posts = [_make_post()]
        payloads = build_embeds(posts, None)
        last = payloads[0]["embeds"][-1]
        assert last["footer"]["text"] == "Next digest at 7am UK time"

    def test_subreddit_embed_title_has_count(self):
        posts = [
            _make_post(subreddit="ClaudeCode", score=50, permalink="https://a"),
            _make_post(subreddit="ClaudeCode", score=30, permalink="https://b"),
        ]
        payloads = build_embeds(posts, None)
        sub_embed = payloads[0]["embeds"][1]
        assert "2 posts" in sub_embed["title"]
        assert "r/ClaudeCode" in sub_embed["title"]

    def test_singular_post_label(self):
        posts = [_make_post(subreddit="ClaudeCode", score=50)]
        payloads = build_embeds(posts, None)
        sub_embed = payloads[0]["embeds"][1]
        assert "1 post)" in sub_embed["title"]

    def test_post_field_contains_score_and_comments(self):
        posts = [_make_post(score=847, num_comments=203)]
        payloads = build_embeds(posts, None)
        field = payloads[0]["embeds"][1]["fields"][0]
        assert "847" in field["value"]
        assert "203" in field["value"]

    def test_post_field_contains_title_and_link(self):
        posts = [_make_post(title="My great post", permalink="https://www.reddit.com/r/test/abc")]
        payloads = build_embeds(posts, None)
        field = payloads[0]["embeds"][1]["fields"][0]
        assert "My great post" in field["value"]
        assert "https://www.reddit.com/r/test/abc" in field["value"]


# ---------------------------------------------------------------------------
# Field value length limit
# ---------------------------------------------------------------------------

class TestFieldValueLimit:
    def test_long_title_truncated(self):
        long_title = "A" * 1000
        post = _make_post(title=long_title)
        value = _post_field_value(post)
        assert len(value) <= MAX_FIELD_VALUE_CHARS


# ---------------------------------------------------------------------------
# Discord total char limit
# ---------------------------------------------------------------------------

class TestCharLimit:
    def test_many_posts_stay_under_char_limit(self):
        posts = [
            _make_post(
                subreddit="ClaudeCode",
                score=100 - i,
                title=f"Post number {i} with a reasonably long title for testing",
                permalink=f"https://www.reddit.com/r/ClaudeCode/comments/{i}/test/",
            )
            for i in range(50)
        ]
        payloads = build_embeds(posts, None)
        for payload in payloads:
            total = sum(_estimate_embed_chars(e) for e in payload["embeds"])
            assert total <= MAX_TOTAL_CHARS


# ---------------------------------------------------------------------------
# Payload splitting (>10 embeds)
# ---------------------------------------------------------------------------

class TestPayloadSplitting:
    def test_splits_when_over_embed_limit(self):
        # Create posts across 12 subreddits → 1 title + 12 group embeds = 13
        posts = [
            _make_post(
                subreddit=f"sub{i}",
                score=50,
                permalink=f"https://www.reddit.com/r/sub{i}/comments/abc/test/",
            )
            for i in range(12)
        ]
        payloads = build_embeds(posts, None)
        for payload in payloads:
            assert len(payload["embeds"]) <= MAX_EMBEDS_PER_MESSAGE


# ---------------------------------------------------------------------------
# AI data passthrough
# ---------------------------------------------------------------------------

class TestAIPath:
    def test_none_ai_data_uses_standard_format(self):
        posts = [_make_post()]
        payloads = build_embeds(posts, None)
        # Should produce standard format without errors
        assert len(payloads) >= 1

    def test_ai_data_falls_back_for_now(self):
        posts = [_make_post()]
        ai_data = {"tldr": "test", "categories": {}, "top_picks": [], "summaries": {}}
        payloads = build_embeds(posts, ai_data)
        # Should still produce output (falls back to standard until AI is implemented)
        assert len(payloads) >= 1
