import pytest
from qdrant_client import QdrantClient

from core.config import settings
from rag.qdrant_store import QdrantStore, point_id


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(settings, "embedding_dim", 4)
    s = QdrantStore(client=QdrantClient(":memory:"), collection="test_kb")
    s.ensure_collection()
    return s


def test_point_id_is_stable():
    assert point_id("abc") == point_id("abc")


def test_upsert_and_search_returns_nearest(store):
    store.upsert(
        ids=["a", "b"],
        vectors=[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        payloads=[{"domain": "tax", "content": "A"}, {"domain": "visa", "content": "B"}],
    )
    hits = store.search([0.9, 0.1, 0.0, 0.0], top_k=1)
    assert hits[0][0] == "a"


def test_domain_filter(store):
    store.upsert(
        ids=["a", "b"],
        vectors=[[1.0, 0.0, 0.0, 0.0], [0.9, 0.1, 0.0, 0.0]],
        payloads=[{"domain": "tax", "content": "A"}, {"domain": "visa", "content": "B"}],
    )
    hits = store.search([1.0, 0.0, 0.0, 0.0], top_k=5, domain="visa")
    assert [h[0] for h in hits] == ["b"]
