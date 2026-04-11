"""Unit tests for ai_summary.py — passthrough and provider routing."""

from unittest.mock import patch

import pytest

from ai_summary import summarise, _get_provider, VALID_CATEGORIES


SAMPLE_POSTS = [{"id": "abc123", "title": "Test", "selftext": "", "score": 50}]


# ---------------------------------------------------------------------------
# Passthrough when disabled
# ---------------------------------------------------------------------------

class TestPassthrough:
    @patch("ai_summary.config")
    def test_returns_none_when_disabled(self, mock_config):
        mock_config.ENABLE_AI = False
        assert summarise(SAMPLE_POSTS) is None

    @patch("ai_summary.config")
    def test_returns_none_when_no_api_key(self, mock_config):
        mock_config.ENABLE_AI = True
        mock_config.AI_API_KEY = ""
        assert summarise(SAMPLE_POSTS) is None


# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------

class TestProviderRouting:
    def test_gemini_provider_exists(self):
        fn = _get_provider("gemini")
        assert callable(fn)

    def test_groq_provider_exists(self):
        fn = _get_provider("groq")
        assert callable(fn)

    def test_anthropic_provider_exists(self):
        fn = _get_provider("anthropic")
        assert callable(fn)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            _get_provider("openai")


# ---------------------------------------------------------------------------
# Provider stubs raise NotImplementedError
# ---------------------------------------------------------------------------

class TestProviderStubs:
    def test_gemini_not_implemented(self):
        fn = _get_provider("gemini")
        with pytest.raises(NotImplementedError):
            fn(SAMPLE_POSTS, "fake-key")

    def test_groq_not_implemented(self):
        fn = _get_provider("groq")
        with pytest.raises(NotImplementedError):
            fn(SAMPLE_POSTS, "fake-key")

    def test_anthropic_not_implemented(self):
        fn = _get_provider("anthropic")
        with pytest.raises(NotImplementedError):
            fn(SAMPLE_POSTS, "fake-key")


# ---------------------------------------------------------------------------
# Graceful fallback when enabled but provider not implemented
# ---------------------------------------------------------------------------

class TestGracefulFallback:
    @patch("ai_summary.config")
    def test_not_implemented_returns_none(self, mock_config):
        mock_config.ENABLE_AI = True
        mock_config.AI_API_KEY = "fake-key"
        mock_config.AI_PROVIDER = "gemini"
        result = summarise(SAMPLE_POSTS)
        assert result is None

    @patch("ai_summary.config")
    def test_unknown_provider_returns_none(self, mock_config):
        mock_config.ENABLE_AI = True
        mock_config.AI_API_KEY = "fake-key"
        mock_config.AI_PROVIDER = "openai"
        # _get_provider raises ValueError, caught by the except Exception
        result = summarise(SAMPLE_POSTS)
        assert result is None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_valid_categories_defined(self):
        assert "new_feature" in VALID_CATEGORIES
        assert "tip" in VALID_CATEGORIES
        assert "bug" in VALID_CATEGORIES
        assert "discussion" in VALID_CATEGORIES
        assert len(VALID_CATEGORIES) == 6
