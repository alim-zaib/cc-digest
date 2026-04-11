Implement `poster.py` and `ai_summary.py` following SPEC.md.

For `poster.py`: The `send_to_discord()` function takes a list of payload dicts and the webhook URL. It POSTs each payload sequentially with `Content-Type: application/json`. Returns `True` if all succeed (2xx). Handles 429 rate limiting by reading the `Retry-After` header and sleeping before retrying. Logs all failures. Returns `False` if any payload fails after retry.

For `ai_summary.py`: Implement the `summarise()` function as a clean passthrough for now — when `ENABLE_AI` is `False`, return `None`. Add a clear comment block and structure showing where the AI provider logic will go when enabled. Include the factory function skeleton that routes to gemini/groq/anthropic based on `AI_PROVIDER`, with each provider function stubbed out raising `NotImplementedError` with a helpful message. The function signature and return type should match SPEC.md exactly so the formatter is ready to consume it when AI is turned on.
