Implement `main.py` as the pipeline orchestrator following SPEC.md. It should:

1. Set up logging to stdout with timestamps
2. Validate that `DISCORD_WEBHOOK_URL` is set, exit with a clear error if not
3. Call `scraper.scrape_subreddits()` with the config
4. Call `filter.filter_posts()` on the results
5. Call `ai_summary.summarise()` (will return None since AI is off)
6. Call `formatter.build_embeds()` with posts and ai_data
7. Call `poster.send_to_discord()` with the embeds and webhook URL
8. Log summary: how many posts scraped, how many passed filters, how many sent
9. Exit 0 on success, exit 1 if Discord posting fails

Wrap the entire pipeline in a try/except that catches unexpected errors, logs them, and exits with code 1. Then do a dry run — run `python main.py` without a real webhook URL to verify the scrape and filter stages work end-to-end. Check the logs to confirm posts are being pulled from Reddit and filtered correctly. Confirm the formatted embeds look right by printing them before the posting step.
