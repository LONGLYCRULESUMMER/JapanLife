from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from agents.supervisor import Route, make_supervisor


class _FakeStructuredLLM:
    def __init__(self, route: str):
        self._route = route

    def with_structured_output(self, schema):
        route = self._route

        class _R:
            def invoke(self, _messages):
                return Route(next=route)

        return _R()


def test_supervisor_routes_to_specialist():
    sup = make_supervisor(_FakeStructuredLLM("tax"))
    cmd = sup({"messages": [HumanMessage("tax question")], "user_language": "en", "active_domain": None, "citations": []})
    assert cmd.goto == "tax"
    assert cmd.update["active_domain"] == "tax"


def test_supervisor_finishes():
    sup = make_supervisor(_FakeStructuredLLM("FINISH"))
    cmd = sup({"messages": [AIMessage("answer")], "user_language": "en", "active_domain": "tax", "citations": []})
    assert cmd.goto == END


def test_supervisor_finishes_deterministically_without_calling_llm():
    class _RaisingLLM:
        def with_structured_output(self, schema):
            class _R:
                def invoke(self, _messages):
                    raise AssertionError("router must not be called when a specialist already answered")

            return _R()

    sup = make_supervisor(_RaisingLLM())
    cmd = sup({"messages": [AIMessage("specialist answer")], "user_language": "en", "active_domain": "tax", "citations": []})
    assert cmd.goto == END
