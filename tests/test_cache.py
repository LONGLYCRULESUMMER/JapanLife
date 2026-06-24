import threading

from core.config import settings
from rag import cache as cache_mod
from rag.cache import (
    EmbeddingCache,
    SqliteKVCache,
    TTLCache,
    get_embedding_cache,
    get_retrieval_cache,
    reset_caches,
)


def test_sqlite_kv_roundtrip_and_persistence(tmp_path):
    path = str(tmp_path / "kv.db")
    c = SqliteKVCache(path)
    assert c.get("a") is None
    c.set("a", "1")
    assert c.get("a") == "1"
    c.set("a", "2")  # overwrite
    assert c.get("a") == "2"
    c.close()
    reopened = SqliteKVCache(path)  # data survives a restart
    assert reopened.get("a") == "2"
    reopened.close()


def test_embedding_cache_roundtrip(tmp_path):
    ec = EmbeddingCache(str(tmp_path / "e.db"), model="m1")
    assert ec.get("hello") is None
    ec.set("hello", [0.1, 0.2, 0.3])
    assert ec.get("hello") == [0.1, 0.2, 0.3]
    assert ec.get_many(["hello", "missing"]) == [[0.1, 0.2, 0.3], None]


def test_embedding_cache_key_includes_model(tmp_path):
    path = str(tmp_path / "e.db")
    EmbeddingCache(path, model="m1").set("t", [1.0])
    assert EmbeddingCache(path, model="m2").get("t") is None  # model is part of the key


def test_ttl_cache_expires_on_clock():
    clock = {"t": 1000.0}
    c = TTLCache(ttl_seconds=10, clock=lambda: clock["t"])
    c.set("k", "v")
    assert c.get("k") == "v"
    clock["t"] += 9
    assert c.get("k") == "v"  # not yet expired
    clock["t"] += 2  # 11s > 10s ttl
    assert c.get("k") is None


def test_ttl_cache_is_thread_safe_smoke():
    c = TTLCache(ttl_seconds=100)

    def worker(n):
        for i in range(200):
            c.set((n, i), i)
            c.get((n, i))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(c) <= 8 * 200


def test_getters_respect_settings(monkeypatch):
    reset_caches()
    monkeypatch.setattr(settings, "enable_embedding_cache", False)
    monkeypatch.setattr(settings, "enable_retrieval_cache", False)
    assert get_embedding_cache() is None
    assert get_retrieval_cache() is None

    reset_caches()
    monkeypatch.setattr(settings, "enable_retrieval_cache", True)
    monkeypatch.setattr(settings, "cache_ttl_seconds", 30)
    assert isinstance(get_retrieval_cache(), TTLCache)
    reset_caches()


def test_embed_texts_uses_cache_and_only_encodes_misses(monkeypatch, tmp_path):
    import rag.embeddings as emb

    reset_caches()
    monkeypatch.setattr(settings, "enable_embedding_cache", True)
    monkeypatch.setattr(settings, "embedding_cache_path", str(tmp_path / "emb.db"))

    calls = {"n": 0}

    def fake_encode(texts):
        calls["n"] += 1
        return [[float(len(t))] for t in texts]

    monkeypatch.setattr(emb, "_encode", fake_encode)

    assert emb.embed_texts(["a", "bb"]) == [[1.0], [2.0]]
    assert calls["n"] == 1
    # identical inputs -> served entirely from cache
    assert emb.embed_texts(["a", "bb"]) == [[1.0], [2.0]]
    assert calls["n"] == 1
    # one new text -> only the miss is encoded
    assert emb.embed_texts(["a", "ccc"]) == [[1.0], [3.0]]
    assert calls["n"] == 2
    reset_caches()


def test_retriever_serves_repeat_query_from_cache(monkeypatch):
    import rag.retriever as rmod
    from rag.retriever import HybridRetriever

    reset_caches()
    monkeypatch.setattr(settings, "enable_retrieval_cache", True)
    monkeypatch.setattr(settings, "cache_ttl_seconds", 100)
    monkeypatch.setattr(rmod, "embed_query", lambda q: [0.0])
    monkeypatch.setattr(
        rmod,
        "fuse",
        lambda a, b, k: [("c1", 1.0, {"content": "x", "doc_title": "D", "section_path": "S", "source_url": ""})],
    )
    monkeypatch.setattr(rmod, "rerank", lambda q, fused, top_n: fused)

    calls = {"n": 0}

    class CountingES:
        def search(self, query, top_k, domain=None):
            calls["n"] += 1
            return []

    class FakeQdrant:
        def search(self, vector, top_k, domain=None):
            return []

    r = HybridRetriever(es=CountingES(), qdrant=FakeQdrant())
    first = r.search("q", top_k=5)
    second = r.search("q", top_k=5)
    assert calls["n"] == 1  # second call served from cache, backend not hit again
    assert first == second and first[0].citation == "D | S"
    reset_caches()
