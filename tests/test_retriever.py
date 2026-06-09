import pytest
from qdrant_client import QdrantClient

import rag.retriever as retriever_mod
from core.config import settings
from rag.qdrant_store import QdrantStore
from rag.retriever import HybridRetriever, RetrievedChunk


class _FakeES:
    def __init__(self, hits):
        self._hits = hits

    def search(self, query, top_k, domain=None):
        return self._hits


@pytest.fixture
def qdrant(monkeypatch):
    monkeypatch.setattr(settings, "embedding_dim", 4)
    s = QdrantStore(client=QdrantClient(":memory:"), collection="rt_kb")
    s.ensure_collection()
    s.upsert(
        ids=["a", "b"],
        vectors=[[1.0, 0, 0, 0], [0, 1.0, 0, 0]],
        payloads=[
            {"domain": "tax", "content": "tax doc A", "doc_title": "A", "section_path": "S1", "source_url": ""},
            {"domain": "tax", "content": "tax doc B", "doc_title": "B", "section_path": "S2", "source_url": ""},
        ],
    )
    return s


def test_search_returns_reranked_chunks(monkeypatch, qdrant):
    es = _FakeES([("a", 7.0, {"chunk_id": "a", "content": "tax doc A", "doc_title": "A", "section_path": "S1", "source_url": ""})])
    monkeypatch.setattr(retriever_mod, "embed_query", lambda q: [1.0, 0, 0, 0])

    class _Stub:
        def predict(self, pairs):
            return [1.0 if "A" in doc else 0.0 for _q, doc in pairs]

    import rag.rerank as rerank_mod
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _Stub())

    r = HybridRetriever(es=es, qdrant=qdrant)
    out = r.search("tax", domain="tax", top_k=5)
    assert isinstance(out[0], RetrievedChunk)
    assert out[0].metadata["chunk_id"] == "a"
    assert out[0].citation == "A | S1"


def test_search_degrades_when_es_raises(monkeypatch, qdrant):
    class _BrokenES:
        def search(self, *a, **k):
            raise RuntimeError("es down")

    monkeypatch.setattr(retriever_mod, "embed_query", lambda q: [0, 1.0, 0, 0])
    import rag.rerank as rerank_mod
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: type("S", (), {"predict": lambda self, p: [1.0] * len(p)})())

    r = HybridRetriever(es=_BrokenES(), qdrant=qdrant)
    out = r.search("anything", top_k=5)
    assert len(out) >= 1
