from __future__ import annotations

from typing import Literal

from langchain_core.messages import SystemMessage
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
        decision = router.invoke([SystemMessage(content=SUPERVISOR_PROMPT), *state["messages"]])
        if decision.next == "FINISH":
            return Command(goto=END)
        return Command(goto=decision.next, update={"active_domain": decision.next})

    return supervisor
