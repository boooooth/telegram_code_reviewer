from langchain_core.messages import HumanMessage

from reviewbot.llm.models import summarizer_model
from reviewbot.memory.episodic import count_events, recent_events
from reviewbot.memory.semantic import add_fact, query_facts

CONSOLIDATION_INTERVAL = 5
KNOWN_FACTS_TOP_K = 3

SUMMARIZER_PROMPT = """Below are recent code review exchanges for one user, plus facts already known \
about them. Distill the exchanges into at most 5 NEW durable facts about this user's codebase and \
preferences (coding style, recurring bug patterns, tech stack, conventions) that would help a future \
code reviewer. Do not repeat facts already known below. Output nothing if there's nothing new.

Already known:
{known_facts}

Recent exchanges:
{events}
"""


def _format_events(events: list[dict]) -> str:
    parts = [f"Input:\n{event['input']}\nReview:\n{event['output']}\n" for event in reversed(events)]
    return "\n---\n".join(parts)


def maybe_consolidate(chat_id: int) -> None:
    total = count_events(chat_id)
    if total == 0 or total % CONSOLIDATION_INTERVAL != 0:
        return

    events = recent_events(chat_id, limit=CONSOLIDATION_INTERVAL)
    events_text = _format_events(events)
    known = query_facts(chat_id, events_text, n_results=KNOWN_FACTS_TOP_K)
    known_facts = "\n".join(f"- {fact}" for fact in known) or "(none yet)"

    prompt = SUMMARIZER_PROMPT.format(known_facts=known_facts, events=events_text)
    response = summarizer_model().invoke([HumanMessage(content=prompt)])

    facts = str(response.content).strip()
    if facts:
        add_fact(chat_id, facts)
