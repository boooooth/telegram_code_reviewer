from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ReviewState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    chat_id: int
    raw_input: str
    source: Literal["snippet", "pr"]
    review_target: str
    source_ref: str | None
    memory_context: str
    reply: str
