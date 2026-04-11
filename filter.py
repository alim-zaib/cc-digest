"""Post filtering by score, recency, keywords, and deduplication."""

import logging
import time

import config

logger = logging.getLogger(__name__)


def _is_recent(post: dict, max_age_hours: int) -> bool:
    """Check if a post was created within the time window."""
    cutoff = time.time() - (max_age_hours * 3600)
    return post["created_utc"] >= cutoff


def _matches_keywords(post: dict, keywords: list[str]) -> bool:
    """Check if title or selftext contains any keyword (case-insensitive)."""
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    return any(kw.lower() in text for kw in keywords)


def filter_posts(posts: list[dict], subreddit_config: dict) -> list[dict]:
    """Apply recency, keyword, score, dedup, and sort filters in order."""
    # 1. Recency
    filtered = [p for p in posts if _is_recent(p, config.TIME_WINDOW_HOURS)]
    dropped = len(posts) - len(filtered)
    if dropped:
        logger.info("Recency filter dropped %d posts", dropped)

    # 2. Keyword match (only for filter_mode: "keyword" subreddits)
    after_kw = []
    for post in filtered:
        sub = post["subreddit"]
        mode = subreddit_config.get(sub, {}).get("filter_mode", "all")
        if mode == "keyword":
            if _matches_keywords(post, config.KEYWORDS):
                after_kw.append(post)
        else:
            after_kw.append(post)
    kw_dropped = len(filtered) - len(after_kw)
    if kw_dropped:
        logger.info("Keyword filter dropped %d posts", kw_dropped)
    filtered = after_kw

    # 3. Score threshold
    after_score = []
    for post in filtered:
        sub = post["subreddit"]
        min_score = subreddit_config.get(sub, {}).get("min_score", 0)
        if post["score"] >= min_score:
            after_score.append(post)
    score_dropped = len(filtered) - len(after_score)
    if score_dropped:
        logger.info("Score filter dropped %d posts", score_dropped)
    filtered = after_score

    # 4. Deduplication by URL (keep first occurrence)
    seen_urls: set[str] = set()
    deduped = []
    for post in filtered:
        if post["url"] not in seen_urls:
            seen_urls.add(post["url"])
            deduped.append(post)
    dup_dropped = len(filtered) - len(deduped)
    if dup_dropped:
        logger.info("Dedup filter dropped %d posts", dup_dropped)
    filtered = deduped

    # 5. Sort by score descending within each subreddit group
    subreddit_order = list(subreddit_config.keys())
    groups: dict[str, list[dict]] = {sub: [] for sub in subreddit_order}
    for post in filtered:
        sub = post["subreddit"]
        if sub in groups:
            groups[sub].append(post)
        else:
            groups[sub] = [post]

    result = []
    for sub in subreddit_order:
        sorted_posts = sorted(groups.get(sub, []), key=lambda p: p["score"], reverse=True)
        result.extend(sorted_posts)

    logger.info("Filter result: %d posts from %d input", len(result), len(posts))
    return result
