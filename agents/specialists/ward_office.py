from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from agents.handoffs import make_handoff_tool
from agents.prompts import WARD_OFFICE_PROMPT
from tools.knowledge_tool import make_knowledge_search_tool
from tools.ward_office_tools import WARD_OFFICE_TOOLS


def ward_office_tools():
    return [
        *WARD_OFFICE_TOOLS,
        make_knowledge_search_tool("ward_office"),
        make_handoff_tool("visa"),
        make_handoff_tool("tax"),
    ]


def build_ward_office_agent(llm):
    return create_react_agent(llm, tools=ward_office_tools(), prompt=WARD_OFFICE_PROMPT, name="ward_office")
