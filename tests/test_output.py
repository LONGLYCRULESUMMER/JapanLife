from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agents.output import extract_citations, extract_reply


def test_extract_reply_returns_last_ai_text():
    msgs = [HumanMessage("q"), AIMessage("first"), ToolMessage("t", tool_call_id="x"), AIMessage("final answer")]
    assert extract_reply(msgs) == "final answer"


def test_extract_reply_empty_when_no_ai():
    assert extract_reply([HumanMessage("q")]) == ""


def test_extract_citations_from_knowledge_tool_messages():
    tm = ToolMessage(content="CTX\n\nSources:\n[1] Doc A | S1\n[2] Doc B | S2", tool_call_id="x", name="search_knowledge_base")
    cites = extract_citations([HumanMessage("q"), tm, AIMessage("ans")])
    assert cites == ["[1] Doc A | S1", "[2] Doc B | S2"]


def test_extract_citations_ignores_other_tools():
    tm = ToolMessage(content="Sources:\n[1] x", tool_call_id="x", name="estimate_income_tax")
    assert extract_citations([tm]) == []
