"""Reddit scraping via authenticated PRAW access."""

import logging
from typing import Any

import praw
import prawcore

import config

logger = logging.getLogger(__name__)

PRAW_EXCEPTIONS = (prawcore.exceptions.PrawcoreException,)
praw_base_exception = getattr(praw.exceptions, "PRAWException", None)
if praw_base_exception is not None:
    PRAW_EXCEPTIONS = PRAW_EXCEPTIONS + (praw_base_exception,)


class ScrapeFailedError(RuntimeError):
    """Raised when Reddit scraping failed and an empty digest must not be posted."""

    def __init__(self, message: str, failures: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.failures = failures


class MissingRedditCredentialsError(ScrapeFailedError):
    """Raised when required Reddit API credentials are not configured."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        missing_names = ", ".join(missing)
        super().__init__(
            "Missing Reddit credentials: "
            f"{missing_names}. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and "
            "REDDIT_USER_AGENT as environment variables or GitHub Actions secrets.",
            [],
        )


def get_reddit_client() -> praw.Reddit:
    """Build a read-only PRAW Reddit client from environment-backed config."""
    credentials = {
        "REDDIT_CLIENT_ID": config.REDDIT_CLIENT_ID,
        "REDDIT_CLIENT_SECRET": config.REDDIT_CLIENT_SECRET,
        "REDDIT_USER_AGENT": config.REDDIT_USER_AGENT,
    }
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        raise MissingRedditCredentialsError(missing)

    return praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
    )


def _extract_post(submission: Any, subreddit: str) -> dict:
    """Extract a normalized post dict from a PRAW Submission object."""
    author = getattr(submission, "author", None)
    permalink = getattr(submission, "permalink", "") or ""
    if permalink and not permalink.startswith("http"):
        permalink = "https://www.reddit.com" + permalink

    return {
        "id": getattr(submission, "id", ""),
        "title": getattr(submission, "title", ""),
        "author": str(author) if author else "",
        "score": getattr(submission, "score", 0),
        "num_comments": getattr(submission, "num_comments", 0),
        "created_utc": getattr(submission, "created_utc", 0.0),
        "url": getattr(submission, "url", ""),
        "selftext": (getattr(submission, "selftext", "") or "")[:500],
        "permalink": permalink,
        "link_flair_text": getattr(submission, "link_flair_text", None),
        "subreddit": subreddit,
    }


def _failure(
    subreddit: str,
    sort: str,
    status_code: int | None,
    message: str,
) -> dict[str, Any]:
    """Build a scrape failure record."""
    return {
        "subreddit": subreddit,
        "sort": sort,
        "status_code": status_code,
        "message": message,
    }


def _status_code_from_exception(exc: BaseException) -> int | None:
    """Extract an HTTP status code from a PRAW/prawcore exception when present."""
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code is None:
        status_code = getattr(response, "status", None)
    if status_code is None:
        status_code = getattr(exc, "status_code", None)

    return status_code if isinstance(status_code, int) else None


def _format_failure(failure: dict[str, Any]) -> str:
    """Format one scrape failure for logs and exceptions."""
    subreddit = failure["subreddit"]
    sort = failure["sort"]
    status_code = failure.get("status_code")
    message = failure.get("message", "")

    if status_code is None:
        return f"r/{subreddit} ({sort}) {message}"

    if message:
        return f"r/{subreddit} ({sort}) HTTP {status_code} ({message})"

    return f"r/{subreddit} ({sort}) HTTP {status_code}"


def _format_failures(failures: list[dict[str, Any]]) -> str:
    """Format scrape failures for a single clear error line."""
    return ", ".join(_format_failure(failure) for failure in failures)


def _raise_scrape_failed(message: str, failures: list[dict[str, Any]]) -> None:
    """Raise the shared scrape failure exception with failure details."""
    raise ScrapeFailedError(f"{message} Failures: {_format_failures(failures)}", failures)


def _get_listing(subreddit: Any, settings: dict) -> Any:
    """Return the configured PRAW listing generator for a subreddit."""
    sort = settings.get("sort", "hot")
    limit = config.POST_LIMIT_PER_SUBREDDIT

    if sort == "hot":
        return subreddit.hot(limit=limit)
    if sort == "new":
        return subreddit.new(limit=limit)
    if sort == "top":
        time_filter = settings.get("time_filter", settings.get("t", "day"))
        return subreddit.top(time_filter=time_filter, limit=limit)

    raise ValueError("Unsupported Reddit sort "
                     f"{sort!r}; expected one of: hot, new, top")


def scrape_subreddits(subreddit_config: dict, reddit: praw.Reddit | None = None) -> list[dict]:
    """Scrape posts from configured subreddits via PRAW."""
    reddit = reddit or get_reddit_client()
    all_posts: list[dict] = []
    failures: list[dict[str, Any]] = []

    for subreddit_name, settings in subreddit_config.items():
        sort = settings.get("sort", "hot")
        logger.info("Scraping r/%s (%s)", subreddit_name, sort)

        try:
            subreddit = reddit.subreddit(subreddit_name)
            submissions = list(_get_listing(subreddit, settings))
        except PRAW_EXCEPTIONS + (ValueError,) as exc:
            failure = _failure(
                subreddit_name,
                sort,
                _status_code_from_exception(exc),
                str(exc) or type(exc).__name__,
            )
            failures.append(failure)
            logger.warning("Scrape failed for %s", _format_failure(failure))
            continue

        posts = [_extract_post(submission, subreddit_name) for submission in submissions]
        logger.info("Got %d posts from r/%s", len(posts), subreddit_name)
        all_posts.extend(posts)

    logger.info("Total scraped: %d posts", len(all_posts))

    if failures:
        logger.warning("Reddit scrape failures: %s", _format_failures(failures))

    if subreddit_config and len(failures) == len(subreddit_config):
        _raise_scrape_failed(
            "Reddit scraping failed for all subreddits. Refusing to post empty digest.",
            failures,
        )

    if failures and not all_posts:
        _raise_scrape_failed(
            "Reddit scraping returned 0 posts after Reddit failures. "
            "Refusing to post empty digest.",
            failures,
        )

    return all_posts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    results = scrape_subreddits({"ClaudeCode": config.SUBREDDITS["ClaudeCode"]})
    for post in results[:5]:
        print(f"  [{post['score']} pts, {post['num_comments']} comments]")
        print(f"  {post['title']}")
        print(f"  {post['permalink']}")
        print()
