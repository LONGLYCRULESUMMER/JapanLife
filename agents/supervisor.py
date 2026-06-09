from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command
from pydantic import BaseModel

from agents.prompts import SUPERVISOR_PROMPT
from agents.state import GraphState


class Route(BaseModel):
    next: Literal["tax", "visa", "ward_office", "FINISH"]


def make_supervisor(llm):
    router = llm.with_structured_output(Route)

    def supervisor(state: GraphState) -> Command:
        messages = state["messages"]
        # Deterministic backstop: once a specialist has produced an answer (the last
        # message is an AIMessage), finish. Guarantees termination even if the LLM never
        # returns FINISH, and saves an extra model call.
        if messages and isinstance(messages[-1], AIMessage):
            return Command(goto=END)
        decision = router.invoke([SystemMessage(content=SUPERVISOR_PROMPT), *messages])
        if decision.next == "FINISH":
            return Command(goto=END)
        return Command(goto=decision.next, update={"active_domain": decision.next})

    return supervisor
