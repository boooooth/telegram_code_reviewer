from functools import lru_cache
from pathlib import Path

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from reviewbot.graph.state import ReviewState
from reviewbot.llm.models import agent_model

PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"


def _load_system_prompt() -> str:
    base = (PROMPTS_DIR / "system_prompt.md").read_text(encoding="utf-8").strip()

    procedural_dir = PROMPTS_DIR / "procedural"
    procedural_texts = [
        path.read_text(encoding="utf-8").strip() for path in sorted(procedural_dir.glob("*.md"))
    ]
    if procedural_texts:
        base += "\n\n" + "\n\n".join(procedural_texts)
    return base


@lru_cache(maxsize=1)
def _react_agent():
    return create_react_agent(model=agent_model(), tools=[], prompt=_load_system_prompt())


async def agent(state: ReviewState) -> dict:
    context = state.get("memory_context") or ""
    extra = [SystemMessage(content=context)] if context else []
    input_messages = extra + list(state["messages"])

    result = await _react_agent().ainvoke({"messages": input_messages})
    new_messages = result["messages"][len(input_messages):]
    return {"messages": new_messages}
