from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from core.config import settings


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class QdrantStore:
    def __init__(self, client: QdrantClient | None = None, collection: str | None = None):
        self.client = client or QdrantClient(url=settings.qdrant_url)
        self.collection = collection or settings.index_name

    def ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim, distance=Distance.COSINE
                ),
            )

    def upsert(
        self, ids: list[str], vectors: list[list[float]], payloads: list[dict]
    ) -> None:
        points = [
            PointStruct(id=point_id(cid), vector=vec, payload={**pl, "chunk_id": cid})
            for cid, vec, pl in zip(ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=[point_id(chunk_id) for chunk_id in ids]),
        )

    def search(
        self, vector: list[float], top_k: int, domain: str | None = None
    ) -> list[tuple[str, float, dict]]:
        flt = None
        if domain:
            flt = Filter(
                must=[FieldCondition(key="domain", match=MatchValue(value=domain))]
            )
        res = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            query_filter=flt,
            with_payload=True,
        )
        return [(p.payload["chunk_id"], p.score, p.payload) for p in res.points]
