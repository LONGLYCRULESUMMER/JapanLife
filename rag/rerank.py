from __future__ import annotations

from functools import lru_cache

from sentence_transformers import CrossEncoder

from core.config import settings


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.reranker_model)


def rerank(
    query: str, candidates: list[tuple[str, float, dict]], top_n: int
) -> list[tuple[str, float, dict]]:
    if not candidates:
        return []
    model = get_reranker()
    pairs = [(query, pl.get("content", "")) for _cid, _score, pl in candidates]
    scores = model.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [(cid, float(score), pl) for (cid, _old, pl), score in ranked[:top_n]]
