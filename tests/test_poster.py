"""Unit tests for poster.py — Discord webhook posting and retry logic."""

from unittest.mock import patch, MagicMock

import pytest

from poster import send_to_discord, _get_retry_after


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, headers: dict | None = None, text: str = "ok"):
    """Build a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.headers = headers or {}
    resp.text = text
    return resp


WEBHOOK = "https://discord.com/api/webhooks/test/token"
PAYLOAD = [{"embeds": [{"title": "test"}]}]


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------

class TestSuccess:
    @patch("poster.requests.post")
    def test_single_payload_success(self, mock_post):
        mock_post.return_value = _mock_response(200)
        assert send_to_discord(PAYLOAD, WEBHOOK) is True
        mock_post.assert_called_once()

    @patch("poster.requests.post")
    def test_multiple_payloads_all_succeed(self, mock_post):
        mock_post.return_value = _mock_response(204)
        payloads = [{"embeds": [{"title": "a"}]}, {"embeds": [{"title": "b"}]}]
        assert send_to_discord(payloads, WEBHOOK) is True
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------

class TestFailure:
    @patch("poster.requests.post")
    def test_http_error_returns_false(self, mock_post):
        mock_post.return_value = _mock_response(400, text="Bad Request")
        assert send_to_discord(PAYLOAD, WEBHOOK) is False

    @patch("poster.requests.post")
    def test_connection_error_returns_false(self, mock_post):
        import requests
        mock_post.side_effect = requests.ConnectionError("refused")
        assert send_to_discord(PAYLOAD, WEBHOOK) is False

    def test_empty_webhook_url_returns_false(self):
        assert send_to_discord(PAYLOAD, "") is False


# ---------------------------------------------------------------------------
# Rate limiting (429)
# ---------------------------------------------------------------------------

class TestRateLimit:
    @patch("poster.time.sleep")
    @patch("poster.requests.post")
    def test_429_retries_after_delay(self, mock_post, mock_sleep):
        rate_resp = _mock_response(429, headers={"Retry-After": "2"})
        ok_resp = _mock_response(200)
        mock_post.side_effect = [rate_resp, ok_resp]

        assert send_to_discord(PAYLOAD, WEBHOOK) is True
        mock_sleep.assert_called_once_with(2.0)
        assert mock_post.call_count == 2

    @patch("poster.time.sleep")
    @patch("poster.requests.post")
    def test_429_retry_also_fails(self, mock_post, mock_sleep):
        rate_resp = _mock_response(429, headers={"Retry-After": "1"})
        fail_resp = _mock_response(500, text="Server Error")
        mock_post.side_effect = [rate_resp, fail_resp]

        assert send_to_discord(PAYLOAD, WEBHOOK) is False

    @patch("poster.time.sleep")
    @patch("poster.requests.post")
    def test_429_missing_retry_after_defaults_to_5(self, mock_post, mock_sleep):
        rate_resp = _mock_response(429)
        ok_resp = _mock_response(200)
        mock_post.side_effect = [rate_resp, ok_resp]

        send_to_discord(PAYLOAD, WEBHOOK)
        mock_sleep.assert_called_once_with(5.0)


# ---------------------------------------------------------------------------
# Retry-After parsing
# ---------------------------------------------------------------------------

class TestRetryAfterParsing:
    def test_numeric_header(self):
        resp = _mock_response(headers={"Retry-After": "3.5"})
        assert _get_retry_after(resp) == 3.5

    def test_missing_header_defaults_to_5(self):
        resp = _mock_response(headers={})
        assert _get_retry_after(resp) == 5.0

    def test_invalid_header_defaults_to_5(self):
        resp = _mock_response(headers={"Retry-After": "not-a-number"})
        assert _get_retry_after(resp) == 5.0
