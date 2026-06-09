from __future__ import annotations

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from core.config import settings

INDEX_BODY = {
    "settings": {
        "analysis": {
            "analyzer": {
                "ja_analyzer": {"type": "custom", "tokenizer": "kuromoji_tokenizer"}
            }
        }
    },
    "mappings": {
        "properties": {
            "content": {
                "type": "text",
                "analyzer": "standard",
                "fields": {"ja": {"type": "text", "analyzer": "ja_analyzer"}},
            },
            "domain": {"type": "keyword"},
            "doc_id": {"type": "keyword"},
            "doc_title": {"type": "keyword"},
            "section_path": {"type": "keyword"},
            "source_url": {"type": "keyword"},
            "language": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
        }
    },
}


class ESStore:
    def __init__(self, client: Elasticsearch | None = None, index: str | None = None):
        self.client = client or Elasticsearch(hosts=[settings.es_url])
        self.index = index or settings.index_name

    def ensure_index(self) -> None:
        if not self.client.indices.exists(index=self.index):
            self.client.indices.create(
                index=self.index,
                settings=INDEX_BODY["settings"],
                mappings=INDEX_BODY["mappings"],
            )

    def index_chunks(
        self, ids: list[str], texts: list[str], payloads: list[dict]
    ) -> None:
        actions = [
            {
                "_index": self.index,
                "_id": cid,
                "_source": {"content": txt, "chunk_id": cid, **pl},
            }
            for cid, txt, pl in zip(ids, texts, payloads)
        ]
        bulk(self.client, actions)
        self.client.indices.refresh(index=self.index)

    def search(
        self, query: str, top_k: int, domain: str | None = None
    ) -> list[tuple[str, float, dict]]:
        bool_q: dict = {
            "must": [
                {"multi_match": {"query": query, "fields": ["content", "content.ja"]}}
            ]
        }
        if domain:
            bool_q["filter"] = [{"term": {"domain": domain}}]
        res = self.client.search(index=self.index, query={"bool": bool_q}, size=top_k)
        return [
            (hit["_source"]["chunk_id"], hit["_score"], hit["_source"])
            for hit in res["hits"]["hits"]
        ]
