from __future__ import annotations

from dataclasses import dataclass

from core.config import settings
from rag.embeddings import embed_query
from rag.es_store import ESStore
from rag.hybrid import fuse
from rag.qdrant_store import QdrantStore
from rag.rerank import rerank


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict
    score: float
    citation: str


def _citation(payload: dict) -> str:
    parts = [payload.get("doc_title"), payload.get("section_path"), payload.get("source_url")]
    return " | ".join(p for p in parts if p) or "Unknown source"


class HybridRetriever:
    def __init__(self, es=None, qdrant=None):
        self.es = es or ESStore()
        self.qdrant = qdrant or QdrantStore()

    def search(
        self, query: str, domain: str | None = None, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.retrieval_top_k
        try:
            es_hits = self.es.search(query, top_k=top_k, domain=domain)
        except Exception:
            es_hits = []
        try:
            qd_hits = self.qdrant.search(embed_query(query), top_k=top_k, domain=domain)
        except Exception:
            qd_hits = []

        fused = fuse(es_hits, qd_hits, k=settings.rrf_k)
        reranked = rerank(query, fused, top_n=settings.rerank_top_n) if fused else []
        return [
            RetrievedChunk(
                text=pl.get("content", ""),
                metadata=pl,
                score=score,
                citation=_citation(pl),
            )
            for _cid, score, pl in reranked
        ]


def search_knowledge_base(query: str, domain: str = "", top_k: int = 5) -> dict:
    """Plain-function knowledge search; Plan 2 wraps this as a LangChain @tool."""
    results = HybridRetriever().search(query, domain=domain or None)[:top_k]
    context = "\n\n---\n\n".join(
        f"[Source {i}: {r.citation}]\n{r.text}" for i, r in enumerate(results, 1)
    )
    citations = "\n".join(f"[{i}] {r.citation}" for i, r in enumerate(results, 1))
    return {
        "context": context or "No relevant information found in the knowledge base.",
        "citations": citations,
        "result_count": len(results),
    }
