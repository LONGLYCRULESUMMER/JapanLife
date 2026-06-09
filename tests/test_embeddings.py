import pytest

from core.config import settings
from rag.embeddings import embed_query, embed_texts


@pytest.mark.integration
def test_embed_query_dim():
    vec = embed_query("How do I file taxes in Japan?")
    assert len(vec) == settings.embedding_dim


@pytest.mark.integration
def test_embed_texts_batch():
    vecs = embed_texts(["確定申告", "permanent residency"])
    assert len(vecs) == 2
    assert all(len(v) == settings.embedding_dim for v in vecs)
