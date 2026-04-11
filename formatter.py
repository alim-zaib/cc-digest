"""Discord embed building from filtered post data."""

import logging
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

MAX_EMBEDS_PER_MESSAGE = 10
MAX_TOTAL_CHARS = 6000
MAX_FIELDS_PER_EMBED = 25
MAX_FIELD_VALUE_CHARS = 1024


def _format_score(score: int) -> str:
    """Format score with k suffix for thousands."""
    if score >= 1000:
        return f"{score / 1000:.1f}k"
    return str(score)


def _post_field_value(post: dict) -> str:
    """Build the field value string for a single post."""
    score = _format_score(post["score"])
    line = (
        f"\u2b06\ufe0f {score} | \U0001f4ac {post['num_comments']}\n"
        f"{post['title']}\n"
        f"{post['permalink']}"
    )
    if len(line) > MAX_FIELD_VALUE_CHARS:
        # Truncate title to fit within limit
        overhead = len(line) - len(post["title"])
        max_title = MAX_FIELD_VALUE_CHARS - overhead - 3
        line = (
            f"\u2b06\ufe0f {score} | \U0001f4ac {post['num_comments']}\n"
            f"{post['title'][:max_title]}...\n"
            f"{post['permalink']}"
        )
    return line


def _group_by_subreddit(posts: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group posts by subreddit, preserving input order of first appearance."""
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for post in posts:
        sub = post["subreddit"]
        if sub not in groups:
            groups[sub] = []
            order.append(sub)
        groups[sub].append(post)
    return [(sub, groups[sub]) for sub in order]


def _estimate_embed_chars(embed: dict) -> int:
    """Estimate character count for a single embed towards the 6000 limit."""
    total = 0
    total += len(embed.get("title", ""))
    total += len(embed.get("description", ""))
    footer = embed.get("footer", {})
    total += len(footer.get("text", ""))
    for field in embed.get("fields", []):
        total += len(field.get("name", ""))
        total += len(field.get("value", ""))
    return total


def _build_no_posts_payload() -> list[dict]:
    """Build a payload for when no posts made it through filtering."""
    today = datetime.now(timezone.utc).strftime("%d %b %Y").lstrip("0")
    return [{"embeds": [{
        "title": f"\U0001f525 Claude Code Digest \u2014 {today}",
        "description": "No Claude Code activity in the last 24 hours.",
        "color": 0x7C3AED,
        "footer": {"text": "Next digest at 7am UK time"},
    }]}]


def _build_embeds_without_ai(posts: list[dict]) -> list[dict]:
    """Build Discord embed payloads without AI enrichment."""
    today = datetime.now(timezone.utc).strftime("%d %b %Y").lstrip("0")
    grouped = _group_by_subreddit(posts)

    # Build all embeds: one title embed + one per subreddit group
    all_embeds = []

    title_embed = {
        "title": f"\U0001f525 Claude Code Digest \u2014 {today}",
        "color": 0x7C3AED,
    }
    all_embeds.append(title_embed)

    for sub, sub_posts in grouped:
        count = len(sub_posts)
        label = f"{count} post{'s' if count != 1 else ''}"
        embed: dict = {
            "title": f"\U0001f4cc r/{sub} ({label})",
            "color": 0x7C3AED,
            "fields": [],
        }

        for post in sub_posts:
            value = _post_field_value(post)
            embed["fields"].append({
                "name": "\u200b",
                "value": value,
                "inline": False,
            })

            # Respect max fields per embed
            if len(embed["fields"]) >= MAX_FIELDS_PER_EMBED:
                break

        all_embeds.append(embed)

    # Add footer to the last embed
    all_embeds[-1]["footer"] = {"text": "Next digest at 7am UK time"}

    # --- Enforce Discord limits ---
    # Truncate lowest-scored posts first if over char limit
    all_embeds = _truncate_to_char_limit(all_embeds, grouped)

    # Split into multiple payloads if more than MAX_EMBEDS_PER_MESSAGE
    payloads = _split_into_payloads(all_embeds)

    return payloads


def _truncate_to_char_limit(embeds: list[dict], grouped: list[tuple[str, list[dict]]]) -> list[dict]:
    """Remove lowest-scored posts until total chars fit within Discord limit."""
    total_chars = sum(_estimate_embed_chars(e) for e in embeds)

    while total_chars > MAX_TOTAL_CHARS:
        # Find the subreddit embed with the lowest-scored last field and remove it
        removed = False
        worst_score = float("inf")
        worst_embed_idx = -1

        for i, embed in enumerate(embeds):
            fields = embed.get("fields", [])
            if not fields:
                continue
            # The fields are ordered by score desc, so the last field is lowest
            # We need the original post score — find it from grouped data
            # Simpler: just remove the last field from the embed with most fields
            if i > 0 and fields:  # skip title embed
                worst_embed_idx = i

        if worst_embed_idx >= 0 and embeds[worst_embed_idx].get("fields"):
            removed_field = embeds[worst_embed_idx]["fields"].pop()
            total_chars -= len(removed_field.get("name", "")) + len(removed_field.get("value", ""))
            removed = True

            # If embed has no more fields, remove it entirely
            if not embeds[worst_embed_idx].get("fields"):
                removed_embed = embeds.pop(worst_embed_idx)
                total_chars -= _estimate_embed_chars(removed_embed)

        if not removed:
            break

    return embeds


def _split_into_payloads(embeds: list[dict]) -> list[dict]:
    """Split embeds into multiple payloads respecting Discord's 10-embed limit."""
    if len(embeds) <= MAX_EMBEDS_PER_MESSAGE:
        return [{"embeds": embeds}]

    payloads = []
    for i in range(0, len(embeds), MAX_EMBEDS_PER_MESSAGE):
        chunk = embeds[i : i + MAX_EMBEDS_PER_MESSAGE]
        payloads.append({"embeds": chunk})

    return payloads


def _build_embeds_with_ai(posts: list[dict], ai_data: dict) -> list[dict]:
    """Build Discord embed payloads with AI enrichment."""
    # TODO: implement when AI is enabled
    # Will add: TL;DR in description, category emoji per post,
    # one-line summary under each title, "⭐ Top Picks" section
    logger.warning("AI-enriched formatting not yet implemented, falling back to standard")
    return _build_embeds_without_ai(posts)


def build_embeds(posts: list[dict], ai_data: dict | None) -> list[dict]:
    """Build Discord webhook payload(s) from filtered posts and optional AI data."""
    if not posts:
        logger.info("No posts to format — building empty digest")
        return _build_no_posts_payload()

    if ai_data is not None:
        return _build_embeds_with_ai(posts, ai_data)

    return _build_embeds_without_ai(posts)
