import rag.rerank as rerank_mod
from rag.rerank import rerank


class _StubReranker:
    def predict(self, pairs):
        return [1.0 if "match" in doc else 0.0 for _q, doc in pairs]


def test_rerank_orders_by_cross_encoder(monkeypatch):
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _StubReranker())
    candidates = [
        ("a", 0.1, {"content": "no relation"}),
        ("b", 0.2, {"content": "a strong match here"}),
    ]
    out = rerank("query", candidates, top_n=2)
    assert [cid for cid, _, _ in out] == ["b", "a"]


def test_rerank_respects_top_n(monkeypatch):
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _StubReranker())
    candidates = [
        ("a", 0.1, {"content": "match"}),
        ("b", 0.2, {"content": "match"}),
        ("c", 0.3, {"content": "x"}),
    ]
    out = rerank("q", candidates, top_n=1)
    assert len(out) == 1


def test_rerank_empty_returns_empty(monkeypatch):
    monkeypatch.setattr(rerank_mod, "get_reranker", lambda: _StubReranker())
    assert rerank("q", [], top_n=3) == []
