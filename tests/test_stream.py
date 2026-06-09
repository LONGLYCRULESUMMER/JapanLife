import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app
from app.routes import get_graph
from core.config import settings


class _StreamStubGraph:
    def stream(self, state, config=None, stream_mode=None):
        yield {"supervisor": {"active_domain": "tax"}}
        yield {"tax": {"messages": [AIMessage("streamed answer")]}}


def test_chat_stream_emits_sse_events(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    app.dependency_overrides[get_graph] = lambda: _StreamStubGraph()
    with TestClient(app) as client:
        with client.stream("POST", "/chat/stream", json={"message": "hi"}) as r:
            assert r.status_code == 200
            text = "".join(chunk for chunk in r.iter_text())
    assert "streamed answer" in text
    assert "data:" in text
    app.dependency_overrides.clear()


def test_chat_stream_emits_error_event_on_failure(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")

    class _BoomStream:
        def stream(self, state, config=None, stream_mode=None):
            raise RuntimeError("boom")
            yield  # make this a generator

    app.dependency_overrides[get_graph] = lambda: _BoomStream()
    with TestClient(app) as client:
        with client.stream("POST", "/chat/stream", json={"message": "hi"}) as r:
            text = "".join(chunk for chunk in r.iter_text())
    assert "error" in text
    app.dependency_overrides.clear()
