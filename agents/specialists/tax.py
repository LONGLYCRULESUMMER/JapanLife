from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from agents.prompts import TAX_PROMPT
from tools.knowledge_tool import make_knowledge_search_tool
from tools.tax_tools import TAX_TOOLS


def tax_tools():
    return [*TAX_TOOLS, make_knowledge_search_tool("tax")]


def build_tax_agent(llm):
    return create_react_agent(llm, tools=tax_tools(), prompt=TAX_PROMPT, name="tax")
