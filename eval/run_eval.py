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
DOMAINS = ("tax", "visa", "ward_office")
K = 5


def load_cases() -> list[dict]:
    """Load the retrieval evaluation cases for the three known domains.

    Loaded by explicit domain name (not a glob) so unrelated datasets such as
    ``answer_cases.jsonl`` never leak into the retrieval evaluation.
    """
    cases = []
    for domain in DOMAINS:
        path = DATASETS / f"{domain}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def dataset_composition(cases: list[dict] | None = None) -> dict:
    """Summarise how many cases there are per language and per query type."""
    cases = cases if cases is not None else load_cases()
    comp: dict = {"total": len(cases), "lang": {}, "type": {}}
    for case in cases:
        lang = case.get("lang", "?")
        typ = case.get("type", "?")
        comp["lang"][lang] = comp["lang"].get(lang, 0) + 1
        comp["type"][typ] = comp["type"].get(typ, 0) + 1
    return comp


def _doc_ids(hits: list[tuple[str, float, dict]]) -> list[str]:
    seen, out = set(), []
    for _cid, _score, pl in hits:
        doc = pl.get("doc_id", "")
        if doc and doc not in seen:
            seen.add(doc)
            out.append(doc)
    return out


def _evaluate(name: str, run) -> tuple[float, float]:
    cases = load_cases()
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

    comp = dataset_composition()
    print(f"=== Dataset: {comp['total']} cases ===")
    print(f"  by language: {comp['lang']}")
    print(f"  by type:     {comp['type']}\n")

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
