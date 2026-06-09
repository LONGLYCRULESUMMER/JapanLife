import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.main import app
from app.routes import get_graph
from core.config import settings


class _StubGraph:
    def invoke(self, state, config=None):
        return {
            "messages": [
                HumanMessage(state["messages"][0].content),
                ToolMessage(content="CTX\n\nSources:\n[1] Doc | S1", tool_call_id="x", name="search_knowledge_base"),
                AIMessage("stub reply"),
            ],
            "active_domain": "tax",
            "citations": [],
        }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    app.dependency_overrides[get_graph] = lambda: _StubGraph()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_chat_returns_reply_route_citations(client):
    r = client.post("/chat", json={"message": "確定申告について"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "stub reply"
    assert body["route"] == "tax"
    assert body["citations"] == ["[1] Doc | S1"]
    assert body["thread_id"]


def test_chat_reuses_thread_id(client):
    r = client.post("/chat", json={"message": "hi", "thread_id": "abc"})
    assert r.json()["thread_id"] == "abc"


def test_health_returns_dependency_status(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "elasticsearch" in body and "qdrant" in body and "status" in body


def test_chat_returns_503_when_graph_fails(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")

    class _BoomGraph:
        def invoke(self, state, config=None):
            raise RuntimeError("llm down")

    app.dependency_overrides[get_graph] = lambda: _BoomGraph()
    with TestClient(app) as c:
        r = c.post("/chat", json={"message": "hi"})
    assert r.status_code == 503
    app.dependency_overrides.clear()
