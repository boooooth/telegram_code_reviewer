from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from reviewbot.graph.nodes.agent import agent
from reviewbot.graph.nodes.guardrails import guardrails
from reviewbot.graph.nodes.intake import intake
from reviewbot.graph.nodes.retrieve_memory import retrieve_memory
from reviewbot.graph.state import ReviewState


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    graph = StateGraph(ReviewState)
    graph.add_node("intake", intake)
    graph.add_node("retrieve_memory", retrieve_memory)
    graph.add_node("agent", agent)
    graph.add_node("guardrails", guardrails)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "retrieve_memory")
    graph.add_edge("retrieve_memory", "agent")
    graph.add_edge("agent", "guardrails")
    graph.add_edge("guardrails", END)

    return graph.compile(checkpointer=checkpointer)
