from __future__ import annotations

from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command


def make_handoff_tool(target: str):
    """Build a tool that hands the conversation off to another specialist node."""

    @tool(
        f"transfer_to_{target}",
        description=f"Hand the conversation off to the {target} specialist for a related follow-up.",
    )
    def handoff(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        return Command(
            goto=target,
            graph=Command.PARENT,
            update={
                "active_domain": target,
                "messages": [ToolMessage(content=f"Transferred to {target}.", tool_call_id=tool_call_id)],
            },
        )

    return handoff
