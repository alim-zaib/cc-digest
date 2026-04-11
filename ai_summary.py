"""Optional AI enrichment — passthrough when disabled."""

import logging

import config

logger = logging.getLogger(__name__)

# Categories that AI providers should assign to each post
VALID_CATEGORIES = ("new_feature", "tip", "bug", "workflow", "tool", "discussion")


def summarise(posts: list[dict]) -> dict | None:
    """Enrich posts with AI-generated summaries, categories, and picks.

    Returns None when AI is disabled. When enabled, returns:
        {
            "tldr": str,                 # one paragraph daily summary
            "categories": {post_id: category_str, ...},
            "top_picks": [{"id": str, "reason": str}, ...],
            "summaries": {post_id: one_line_summary_str, ...},
        }
    """
    if not config.ENABLE_AI:
        logger.info("AI disabled — skipping enrichment")
        return None

    if not config.AI_API_KEY:
        logger.warning("AI enabled but no API key configured — skipping")
        return None

    try:
        provider_fn = _get_provider(config.AI_PROVIDER)
        return provider_fn(posts, config.AI_API_KEY)
    except NotImplementedError:
        logger.warning("AI provider '%s' not yet implemented — skipping", config.AI_PROVIDER)
        return None
    except Exception as exc:
        logger.error("AI enrichment failed: %s — skipping", exc)
        return None


# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------

def _get_provider(provider_name: str):
    """Factory function — select the AI provider function by name."""
    providers = {
        "gemini": _summarise_gemini,
        "groq": _summarise_groq,
        "anthropic": _summarise_anthropic,
    }
    fn = providers.get(provider_name)
    if fn is None:
        raise ValueError(f"Unknown AI provider: {provider_name!r}. Choose from: {list(providers)}")
    return fn


# ---------------------------------------------------------------------------
# Provider stubs — each will use raw HTTP requests (no SDKs)
# ---------------------------------------------------------------------------

def _summarise_gemini(posts: list[dict], api_key: str) -> dict:
    """Send posts to Google Gemini for AI enrichment."""
    raise NotImplementedError(
        "Gemini provider not yet implemented. "
        "Will POST to generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    )


def _summarise_groq(posts: list[dict], api_key: str) -> dict:
    """Send posts to Groq for AI enrichment."""
    raise NotImplementedError(
        "Groq provider not yet implemented. "
        "Will POST to api.groq.com/openai/v1/chat/completions"
    )


def _summarise_anthropic(posts: list[dict], api_key: str) -> dict:
    """Send posts to Anthropic Claude for AI enrichment."""
    raise NotImplementedError(
        "Anthropic provider not yet implemented. "
        "Will POST to api.anthropic.com/v1/messages"
    )
