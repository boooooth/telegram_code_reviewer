import asyncio

from reviewbot.graph.state import ReviewState
from reviewbot.memory.episodic import recent_events
from reviewbot.memory.semantic import query_facts

RECENCY_LIMIT = 3
SEMANTIC_TOP_K = 3
SNIPPET_LEN = 200


async def retrieve_memory(state: ReviewState) -> dict:
    chat_id = state["chat_id"]
    parts = []

    events = await asyncio.to_thread(recent_events, chat_id, limit=RECENCY_LIMIT)
    if events:
        lines = [
            f"- [{event['created_at']}] reviewed {event['source_ref'] or 'a pasted snippet'}: "
            f"{event['output'][:SNIPPET_LEN]}"
            for event in events
        ]
        parts.append("Recent review history for this chat (most recent first):\n" + "\n".join(lines))

    facts = await asyncio.to_thread(
        query_facts, chat_id, state.get("review_target", ""), n_results=SEMANTIC_TOP_K
    )
    if facts:
        parts.append(
            "Known durable facts/preferences about this user's codebase:\n"
            + "\n".join(f"- {fact}" for fact in facts)
        )

    return {"memory_context": "\n\n".join(parts)}
