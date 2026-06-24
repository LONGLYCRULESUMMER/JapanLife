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


def test_search_returns_ranked_chunks(monkeypatch):
    from rag.retriever import RetrievedChunk
    from app.routes import get_retriever

    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")

    class _StubRetriever:
        def search(self, query, domain=None, top_k=None):
            return [
                RetrievedChunk(text="tax body text here", metadata={"domain": "tax"}, score=0.9, citation="Doc A | S1"),
                RetrievedChunk(text="more text", metadata={"domain": "tax"}, score=0.8, citation="Doc B | S2"),
            ]

    app.dependency_overrides[get_retriever] = lambda: _StubRetriever()
    with TestClient(app) as c:
        r = c.get("/search", params={"q": "確定申告", "top_k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "確定申告"
    assert len(body["results"]) == 2
    assert body["results"][0]["citation"] == "Doc A | S1"
    assert body["results"][0]["score"] == 0.9
    assert body["results"][0]["domain"] == "tax"
    app.dependency_overrides.clear()


class _ConvCursor(list):
    def fetchall(self):
        return list(self)


class _ConvConn:
    def execute(self, sql, params=()):
        return _ConvCursor([("t-1", "c2"), ("t-2", "c1")])


class _ConvCheckpointer:
    def __init__(self):
        self.conn = _ConvConn()
        self.deleted = None

    def delete_thread(self, tid):
        self.deleted = tid


class _ConvState:
    def __init__(self, messages):
        self.values = {"messages": messages}


class _ConvGraph:
    def __init__(self):
        self.checkpointer = _ConvCheckpointer()

    def get_state(self, config):
        from langchain_core.messages import AIMessage, HumanMessage
        tid = config["configurable"]["thread_id"]
        return _ConvState([HumanMessage(f"Q {tid}"), AIMessage(f"A {tid}")])


def test_list_get_delete_conversations(monkeypatch):
    from app.routes import get_graph
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    g = _ConvGraph()
    app.dependency_overrides[get_graph] = lambda: g
    with TestClient(app) as c:
        lst = c.get("/conversations").json()["conversations"]
        assert [x["thread_id"] for x in lst] == ["t-1", "t-2"]
        assert lst[0]["title"] == "Q t-1"
        assert lst[0]["turns"] == 1

        one = c.get("/conversations/t-1").json()
        assert one["thread_id"] == "t-1"
        assert one["messages"][0] == {"role": "user", "content": "Q t-1", "citations": []}
        assert one["messages"][1]["content"] == "A t-1"

        d = c.delete("/conversations/t-1").json()
        assert d["deleted"] == "t-1"
        assert g.checkpointer.deleted == "t-1"
    app.dependency_overrides.clear()
