from __future__ import annotations

from langchain.agents import create_agent

from agents.prompts import TAX_PROMPT
from tools.knowledge_tool import make_knowledge_search_tool
from tools.tax_tools import TAX_TOOLS


def tax_tools():
    return [*TAX_TOOLS, make_knowledge_search_tool("tax")]


def build_tax_agent(llm):
    return create_agent(llm, tools=tax_tools(), system_prompt=TAX_PROMPT, name="tax")
