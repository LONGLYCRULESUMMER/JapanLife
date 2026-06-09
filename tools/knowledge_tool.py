from __future__ import annotations

from langchain_core.tools import StructuredTool

from rag.retriever import search_knowledge_base as _search


def make_knowledge_search_tool(domain: str) -> StructuredTool:
    """Build a domain-scoped knowledge-search tool for a specialist agent."""

    def _run(query: str) -> str:
        result = _search(query, domain=domain)
        citations = result["citations"]
        body = result["context"]
        if citations:
            return f"{body}\n\nSources:\n{citations}"
        return body

    return StructuredTool.from_function(
        func=_run,
        name="search_knowledge_base",
        description=(
            f"Search the authoritative {domain} knowledge base for living-in-Japan "
            "information. Input: a natural-language query in English or Japanese. "
            "Always cite the returned sources in your answer."
        ),
    )
