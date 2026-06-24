from __future__ import annotations

from langgraph.graph import START, StateGraph

from agents.state import GraphState
from agents.supervisor import make_supervisor

_SPECIALIST_NAMES = ("tax", "visa", "ward_office")


def build_graph(llm=None, checkpointer=None, supervisor=None, specialists=None):
    """Assemble the supervisor + specialist graph.

    For production pass `llm` (real DeepSeek). For tests, inject `supervisor`
    and `specialists` stubs to exercise wiring without an LLM.
    """
    if supervisor is None:
        if llm is None:
            raise ValueError("Provide either `llm` or a `supervisor` stub.")
        supervisor = make_supervisor(llm)

    if specialists is None:
        if llm is None:
            raise ValueError("Provide either `llm` or `specialists` stubs.")
        from agents.specialists.tax import build_tax_agent
        from agents.specialists.visa import build_visa_agent
        from agents.specialists.ward_office import build_ward_office_agent

        specialists = {
            "tax": build_tax_agent(llm),
            "visa": build_visa_agent(llm),
            "ward_office": build_ward_office_agent(llm),
        }

    builder = StateGraph(GraphState)
    builder.add_node("supervisor", supervisor)
    for name, node in specialists.items():
        builder.add_node(name, node)
    builder.add_edge(START, "supervisor")
    for name in specialists:
        builder.add_edge(name, "supervisor")
    return builder.compile(checkpointer=checkpointer)
