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


def test_reconstruct_messages_pairs_turns_with_citations():
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from agents.output import reconstruct_messages

    msgs = [
        HumanMessage("q1"),
        AIMessage("let me check"),  # preamble, folded away
        ToolMessage("CTX\n\nSources:\n[1] Doc | S1", tool_call_id="x", name="search_knowledge_base"),
        AIMessage("final answer 1"),
        HumanMessage("q2"),
        AIMessage("answer 2"),
    ]
    turns = reconstruct_messages(msgs)
    assert [t["role"] for t in turns] == ["user", "assistant", "user", "assistant"]
    assert turns[0]["content"] == "q1"
    assert turns[1]["content"] == "final answer 1"
    assert turns[1]["citations"] == ["[1] Doc | S1"]
    assert turns[3]["content"] == "answer 2"
    assert turns[3]["citations"] == []


def test_reconstruct_messages_user_only_turn():
    from langchain_core.messages import HumanMessage
    from agents.output import reconstruct_messages

    assert reconstruct_messages([HumanMessage("just asked")]) == [
        {"role": "user", "content": "just asked", "citations": []}
    ]
