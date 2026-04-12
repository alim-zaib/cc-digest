"""Reddit scraping via public .json endpoints."""

import logging
import time

import requests

import config

logger = logging.getLogger(__name__)


def _extract_post(raw: dict, subreddit: str) -> dict:
    """Extract a normalized post dict from a Reddit API child object."""
    data = raw.get("data", {})
    selftext = data.get("selftext", "") or ""
    return {
        "id": data.get("id", ""),
        "title": data.get("title", ""),
        "author": data.get("author", ""),
        "score": data.get("score", 0),
        "num_comments": data.get("num_comments", 0),
        "created_utc": data.get("created_utc", 0.0),
        "url": data.get("url", ""),
        "selftext": selftext[:500],
        "permalink": "https://www.reddit.com" + data.get("permalink", ""),
        "link_flair_text": data.get("link_flair_text"),
        "subreddit": subreddit,
    }


def scrape_subreddits(subreddit_config: dict) -> list[dict]:
    """Scrape posts from configured subreddits via Reddit .json endpoints."""
    all_posts: list[dict] = []
    headers = {
        "User-Agent": config.USER_AGENT,
    }

    for i, (subreddit, settings) in enumerate(subreddit_config.items()):
        if i > 0:
            time.sleep(config.REQUEST_DELAY_SECONDS)

        sort = settings.get("sort", "hot")
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params = {
            "limit": config.POST_LIMIT_PER_SUBREDDIT,
            "raw_json": 1,
            "t": "day",
        }

        logger.info("Scraping r/%s (%s)", subreddit, sort)

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
        except requests.ConnectionError:
            logger.error("Connection error for r/%s — skipping", subreddit)
            continue
        except requests.Timeout:
            logger.error("Timeout for r/%s — skipping", subreddit)
            continue
        except requests.RequestException as exc:
            logger.error("Request failed for r/%s: %s — skipping", subreddit, exc)
            continue

        if resp.status_code == 429:
            logger.warning("Rate limited (429) on r/%s — skipping", subreddit)
            continue
        if resp.status_code in (403, 404):
            logger.warning("HTTP %d on r/%s — skipping", resp.status_code, subreddit)
            continue
        if not resp.ok:
            logger.warning("HTTP %d on r/%s — skipping", resp.status_code, subreddit)
            continue

        try:
            data = resp.json()
        except (ValueError, requests.JSONDecodeError):
            logger.error("JSON decode error for r/%s — skipping", subreddit)
            continue

        children = data.get("data", {}).get("children", [])
        posts = [_extract_post(child, subreddit) for child in children]
        logger.info("Got %d posts from r/%s", len(posts), subreddit)
        all_posts.extend(posts)

    logger.info("Total scraped: %d posts", len(all_posts))
    return all_posts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    test_config = {
        "ClaudeCode": config.SUBREDDITS["ClaudeCode"],
    }
    results = scrape_subreddits(test_config)
    for post in results[:5]:
        print(f"  [{post['score']} pts, {post['num_comments']} comments]")
        print(f"  {post['title']}")
        print(f"  {post['permalink']}")
        print()
