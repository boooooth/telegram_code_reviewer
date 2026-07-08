import html

TELEGRAM_MAX_LEN = 4096
_PRE_TAG_OVERHEAD = len("<pre></pre>")


def _split_raw(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


def split_for_telegram(text: str, limit: int = TELEGRAM_MAX_LEN) -> list[str]:
    """Split text into Telegram-sized chunks, each wrapped in its own <pre>
    block so it renders as monospace. Send these with parse_mode="HTML"."""
    body_limit = limit - _PRE_TAG_OVERHEAD
    raw_chunks = _split_raw(text, body_limit)
    return [f"<pre>{html.escape(chunk)}</pre>" for chunk in raw_chunks]
