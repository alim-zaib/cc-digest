"""Discord webhook POST logic with retry handling."""

import logging
import time

import requests

logger = logging.getLogger(__name__)


def send_to_discord(payloads: list[dict], webhook_url: str) -> bool:
    """POST each payload to the Discord webhook. Returns True if all succeed."""
    if not webhook_url:
        logger.error("No Discord webhook URL configured")
        return False

    all_ok = True

    for i, payload in enumerate(payloads):
        logger.info("Sending payload %d/%d to Discord", i + 1, len(payloads))

        try:
            resp = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
        except requests.RequestException as exc:
            logger.error("Failed to send payload %d: %s", i + 1, exc)
            all_ok = False
            continue

        # Handle rate limiting — retry once after Retry-After delay
        if resp.status_code == 429:
            retry_after = _get_retry_after(resp)
            logger.warning("Rate limited (429), retrying after %.1fs", retry_after)
            time.sleep(retry_after)

            try:
                resp = requests.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15,
                )
            except requests.RequestException as exc:
                logger.error("Retry failed for payload %d: %s", i + 1, exc)
                all_ok = False
                continue

        if resp.ok:
            logger.info("Payload %d sent successfully (HTTP %d)", i + 1, resp.status_code)
        else:
            logger.error(
                "Payload %d failed: HTTP %d — %s", i + 1, resp.status_code, resp.text[:200]
            )
            all_ok = False

    return all_ok


def _get_retry_after(resp: requests.Response) -> float:
    """Extract Retry-After delay from response, defaulting to 5 seconds."""
    try:
        return float(resp.headers.get("Retry-After", 5))
    except (ValueError, TypeError):
        return 5.0
