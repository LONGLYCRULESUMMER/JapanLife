from __future__ import annotations


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = 60
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def fuse(
    es_hits: list[tuple[str, float, dict]],
    qdrant_hits: list[tuple[str, float, dict]],
    k: int = 60,
) -> list[tuple[str, float, dict]]:
    payloads: dict[str, dict] = {}
    for cid, _, pl in [*es_hits, *qdrant_hits]:
        payloads.setdefault(cid, pl)
    es_ranking = [cid for cid, _, _ in es_hits]
    qd_ranking = [cid for cid, _, _ in qdrant_hits]
    fused = reciprocal_rank_fusion([es_ranking, qd_ranking], k=k)
    ordered = sorted(fused.items(), key=lambda x: x[1], reverse=True)
    return [(cid, score, payloads[cid]) for cid, score in ordered]
