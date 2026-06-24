from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from core.config import settings
from rag.cache import get_embedding_cache


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def _encode(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_texts(texts: list[str]) -> list[list[float]]:
    texts = list(texts)
    if not texts:
        return []
    cache = get_embedding_cache()
    if cache is None:
        return _encode(texts)

    cached = cache.get_many(texts)
    missing = [i for i, vec in enumerate(cached) if vec is None]
    if missing:
        fresh = _encode([texts[i] for i in missing])
        for slot, idx in enumerate(missing):
            cached[idx] = fresh[slot]
        cache.set_many([texts[i] for i in missing], fresh)
    return cached  # type: ignore[return-value]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
