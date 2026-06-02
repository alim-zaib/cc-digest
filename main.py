"""Entry point - orchestrates the scrape -> filter -> format -> post pipeline."""

import logging
import sys

import ai_summary
import config
import filter as filter_mod
import formatter
import poster
import scraper

logger = logging.getLogger("digest")


def _setup_logging() -> None:
    """Configure process logging for local runs and GitHub Actions."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    """Run the full digest pipeline. Returns exit code."""
    _setup_logging()

    try:
        reddit = scraper.get_reddit_client()
    except scraper.ScrapeFailedError as exc:
        logger.error("%s", exc)
        return 1

    if not config.DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL is not set - cannot post digest")
        return 1

    # 1. Scrape
    logger.info("Scraping %d subreddits", len(config.SUBREDDITS))
    try:
        posts = scraper.scrape_subreddits(config.SUBREDDITS, reddit=reddit)
    except scraper.ScrapeFailedError as exc:
        logger.error("%s", exc)
        return 1

    if posts:
        logger.info("Reddit scraping succeeded: scraped %d posts total", len(posts))
    else:
        logger.info("Reddit scraping succeeded: scraped 0 posts total")

    # 2. Filter
    filtered = filter_mod.filter_posts(posts, config.SUBREDDITS)
    if filtered:
        logger.info("Posts matched filters: %d posts", len(filtered))
    else:
        logger.info("No posts matched the filters; building a no-activity digest")

    # 3. AI enrichment (passthrough when disabled)
    ai_data = ai_summary.summarise(filtered)

    # 4. Format
    payloads = formatter.build_embeds(filtered, ai_data)
    logger.info("Built %d payload(s) to send", len(payloads))

    # 5. Post
    success = poster.send_to_discord(payloads, config.DISCORD_WEBHOOK_URL)

    if success:
        logger.info("Digest posted successfully (%d posts)", len(filtered))
        return 0

    logger.error("Failed to post digest to Discord")
    return 1


if __name__ == "__main__":
    sys.exit(main())
