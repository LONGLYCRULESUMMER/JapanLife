from __future__ import annotations

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage

from tools.knowledge_tool import KNOWLEDGE_TOOL_NAME


def _text(message: AnyMessage) -> str:
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)


def extract_reply(messages: list[AnyMessage]) -> str:
    """Return the text of the last non-empty AI message."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return _text(m)
    return ""


def extract_citations(messages: list[AnyMessage]) -> list[str]:
    """Collect citation lines from knowledge-search tool messages."""
    cites: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage) and getattr(m, "name", "") == KNOWLEDGE_TOOL_NAME:
            text = m.content if isinstance(m.content, str) else str(m.content)
            if "Sources:" in text:
                for line in text.split("Sources:", 1)[1].strip().splitlines():
                    line = line.strip()
                    if line and line not in cites:
                        cites.append(line)
    return cites


def reconstruct_messages(messages: list[AnyMessage]) -> list[dict]:
    """Rebuild display turns from a stored message list.

    Returns a flat list of {role, content, citations} entries: one 'user' entry per
    human turn, followed by a single 'assistant' entry holding that turn's final answer
    (intermediate tool-preamble messages are folded away) and its citations.
    """
    out: list[dict] = []
    tools: list[AnyMessage] = []
    assistant_idx: int | None = None
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": _text(m), "citations": []})
            tools = []
            assistant_idx = None
        elif isinstance(m, ToolMessage):
            tools.append(m)
            if assistant_idx is not None:
                out[assistant_idx]["citations"] = extract_citations(tools)
        elif isinstance(m, AIMessage):
            text = _text(m)
            if text.strip():
                if assistant_idx is None:
                    out.append({"role": "assistant", "content": text, "citations": extract_citations(tools)})
                    assistant_idx = len(out) - 1
                else:
                    out[assistant_idx]["content"] = text
                    out[assistant_idx]["citations"] = extract_citations(tools)
    return out
