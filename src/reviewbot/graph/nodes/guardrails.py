import asyncio
import re

from langchain_core.messages import RemoveMessage

from reviewbot.config import settings
from reviewbot.graph.state import ReviewState
from reviewbot.memory.consolidation import maybe_consolidate
from reviewbot.memory.episodic import log_event

EMPTY_FALLBACK = "The reviewer returned an empty response. Please try again."

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),  # Slack tokens
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub tokens
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),  # Google API keys
    re.compile(r"sk-(ant-)?[A-Za-z0-9_-]{20,}"),  # Anthropic/OpenAI-style secret keys
]


def _redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _trim_working_memory(messages: list) -> list[RemoveMessage]:
    excess = len(messages) - settings.max_working_memory_messages
    if excess <= 0:
        return []
    return [RemoveMessage(id=m.id) for m in messages[:excess]]


async def guardrails(state: ReviewState) -> dict:
    messages = state.get("messages", [])
    content = messages[-1].content if messages else ""
    if not isinstance(content, str) or not content.strip():
        reply = EMPTY_FALLBACK
    else:
        reply = _redact(content)

    await asyncio.to_thread(
        log_event,
        chat_id=state["chat_id"],
        source=state.get("source", "snippet"),
        source_ref=state.get("source_ref"),
        input_text=state.get("review_target", ""),
        output_text=reply,
    )
    await asyncio.to_thread(maybe_consolidate, state["chat_id"])
    return {"reply": reply, "messages": _trim_working_memory(messages)}
