from __future__ import annotations

from langchain.agents import create_agent

from agents.prompts import VISA_PROMPT
from tools.knowledge_tool import make_knowledge_search_tool
from tools.visa_tools import VISA_TOOLS


def visa_tools():
    return [*VISA_TOOLS, make_knowledge_search_tool("visa")]


def build_visa_agent(llm):
    return create_agent(llm, tools=visa_tools(), system_prompt=VISA_PROMPT, name="visa")
