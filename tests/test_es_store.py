import uuid

import pytest

from rag.es_store import ESStore


@pytest.mark.integration
def test_index_and_search(es_client):
    index = f"test_kb_{uuid.uuid4().hex[:8]}"
    store = ESStore(client=es_client, index=index)
    store.ensure_index()
    try:
        store.index_chunks(
            ids=["a", "b"],
            texts=["確定申告 is the annual tax return", "permanent residency requires 10 years"],
            payloads=[{"domain": "tax"}, {"domain": "visa"}],
        )
        hits = store.search("確定申告", top_k=5)
        assert hits and hits[0][0] == "a"
        filtered = store.search("residency", top_k=5, domain="visa")
        assert [h[0] for h in filtered] == ["b"]
    finally:
        es_client.indices.delete(index=index, ignore_unavailable=True)
