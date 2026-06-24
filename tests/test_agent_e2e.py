import os

import pytest

from core.config import settings


@pytest.mark.integration
def test_real_agent_answers_tax_question():
    if not settings.deepseek_api_key and not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY not set")

    from langchain_core.messages import HumanMessage

    from agents.graph import build_graph
    from core.llm import get_llm

    graph = build_graph(llm=get_llm())
    result = graph.invoke(
        {"messages": [HumanMessage("When is the income tax filing deadline in Japan?")],
         "user_language": "en", "active_domain": None, "citations": []},
        config={"configurable": {"thread_id": "e2e-1"}},
    )
    from agents.output import extract_reply

    assert extract_reply(result["messages"]).strip()
