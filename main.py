"""Entry point — orchestrates the scrape → filter → format → post pipeline."""

import json
import logging
import sys

import config
import scraper
import filter as filter_mod
import ai_summary
import formatter
import poster

logger = logging.getLogger("digest")


def main() -> int:
    """Run the full digest pipeline. Returns exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    if not config.DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL is not set — cannot post digest")
        return 1

    # 1. Scrape
    logger.info("Scraping %d subreddits", len(config.SUBREDDITS))
    posts = scraper.scrape_subreddits(config.SUBREDDITS)
    logger.info("Scraped %d posts total", len(posts))

    # 2. Filter
    filtered = filter_mod.filter_posts(posts, config.SUBREDDITS)
    logger.info("Filtered down to %d posts", len(filtered))

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
    else:
        logger.error("Failed to post digest to Discord")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stdout,
        )
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)
