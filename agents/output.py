from __future__ import annotations

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage


def extract_reply(messages: list[AnyMessage]) -> str:
    """Return the text of the last non-empty AI message."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def extract_citations(messages: list[AnyMessage]) -> list[str]:
    """Collect citation lines from knowledge-search tool messages."""
    cites: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage) and getattr(m, "name", "") == "search_knowledge_base":
            text = m.content if isinstance(m.content, str) else str(m.content)
            if "Sources:" in text:
                for line in text.split("Sources:", 1)[1].strip().splitlines():
                    line = line.strip()
                    if line and line not in cites:
                        cites.append(line)
    return cites
