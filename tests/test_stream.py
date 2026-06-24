import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk, ToolMessage

from app.main import app
from app.routes import get_graph
from core.config import settings


class _StreamStubGraph:
    """Mimics graph.stream(stream_mode="messages", subgraphs=True): yields
    (namespace, (chunk, metadata)) tuples like LangGraph does."""

    def stream(self, state, config=None, stream_mode=None, subgraphs=False):
        meta = {"langgraph_node": "model"}
        ns = ("tax:abc123",)
        yield ns, (AIMessageChunk(content="Let me check."), meta)
        yield ns, (ToolMessage(content="CTX\n\nSources:\n[1] Doc | S1", tool_call_id="x", name="search_knowledge_base"), {"langgraph_node": "tools"})
        yield ns, (AIMessageChunk(content="streamed "), meta)
        yield ns, (AIMessageChunk(content="answer"), meta)


def test_chat_stream_emits_token_route_and_done(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    app.dependency_overrides[get_graph] = lambda: _StreamStubGraph()
    with TestClient(app) as client:
        with client.stream("POST", "/chat/stream", json={"message": "hi"}) as r:
            assert r.status_code == 200
            text = "".join(chunk for chunk in r.iter_text())
    assert "event: route" in text and "tax" in text
    assert "event: token" in text and "streamed " in text and "answer" in text
    assert "event: tool" in text and "search_knowledge_base" in text
    assert "event: done" in text and "[1] Doc | S1" in text
    app.dependency_overrides.clear()


def test_chat_stream_emits_error_event_on_failure(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")

    class _BoomStream:
        def stream(self, state, config=None, stream_mode=None, subgraphs=False):
            raise RuntimeError("boom")
            yield  # make this a generator

    app.dependency_overrides[get_graph] = lambda: _BoomStream()
    with TestClient(app) as client:
        with client.stream("POST", "/chat/stream", json={"message": "hi"}) as r:
            text = "".join(chunk for chunk in r.iter_text())
    assert "event: error" in text
    app.dependency_overrides.clear()
