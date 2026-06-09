from __future__ import annotations

import json
from pathlib import Path

from core.config import settings
from eval.metrics import mrr, recall_at_k
from rag.embeddings import embed_query
from rag.es_store import ESStore
from rag.hybrid import fuse
from rag.qdrant_store import QdrantStore
from rag.rerank import rerank

DATASETS = Path(__file__).resolve().parent / "datasets"
K = 5


def _load_cases() -> list[dict]:
    cases = []
    for f in sorted(DATASETS.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _doc_ids(hits: list[tuple[str, float, dict]]) -> list[str]:
    seen, out = set(), []
    for _cid, _score, pl in hits:
        doc = pl.get("doc_id", "")
        if doc and doc not in seen:
            seen.add(doc)
            out.append(doc)
    return out


def _evaluate(name: str, run) -> tuple[float, float]:
    cases = _load_cases()
    recalls, mrrs = [], []
    for case in cases:
        relevant = set(case["relevant"])
        docs = _doc_ids(run(case["question"]))
        recalls.append(recall_at_k(docs, relevant, K))
        mrrs.append(mrr(docs, relevant))
    avg_r = sum(recalls) / len(recalls)
    avg_m = sum(mrrs) / len(mrrs)
    print(f"{name:<16} Recall@{K}={avg_r:.3f}  MRR={avg_m:.3f}")
    return avg_r, avg_m


def main() -> None:
    es = ESStore()
    qd = QdrantStore()
    top_k = settings.retrieval_top_k

    def es_only(q: str):
        return es.search(q, top_k=top_k)

    def qdrant_only(q: str):
        return qd.search(embed_query(q), top_k=top_k)

    def hybrid(q: str):
        fused = fuse(es.search(q, top_k=top_k), qd.search(embed_query(q), top_k=top_k), k=settings.rrf_k)
        return rerank(q, fused, top_n=settings.rerank_top_n)

    print("=== Retrieval evaluation ===")
    _evaluate("es_only", es_only)
    _evaluate("qdrant_only", qdrant_only)
    _evaluate("hybrid", hybrid)


if __name__ == "__main__":
    main()
