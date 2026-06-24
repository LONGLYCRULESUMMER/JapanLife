from __future__ import annotations

import argparse
from pathlib import Path

from rag.chunking import Chunk, chunk_markdown, split_front_matter
from rag.embeddings import embed_texts
from rag.es_store import ESStore
from rag.qdrant_store import QdrantStore

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def load_documents(base: Path = KNOWLEDGE_DIR) -> list[tuple[str, str, str, str]]:
    docs = []
    for md in sorted(base.glob("*/*.md")):
        docs.append((md.parent.name, md.name, md.stem, md.read_text(encoding="utf-8")))
    return docs


def build_chunks(docs: list[tuple[str, str, str, str]]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for domain, filename, title, text in docs:
        front_matter, body = split_front_matter(text)
        meta = {
            "domain": domain,
            "doc_id": f"{domain}/{filename}",
            "doc_title": front_matter.get("doc_title") or title,
            "source_url": front_matter.get("source_url", ""),
            "language": front_matter.get("language", "mixed"),
        }
        chunks.extend(chunk_markdown(body, meta))
    return chunks


def ingest(base: Path = KNOWLEDGE_DIR) -> int:
    chunks = build_chunks(load_documents(base))
    ids = [c.chunk_id for c in chunks]
    texts = [c.text for c in chunks]
    payloads = [{**c.metadata, "content": c.text} for c in chunks]

    es = ESStore()
    es.ensure_index()
    es.index_chunks(ids, texts, payloads)

    qd = QdrantStore()
    qd.ensure_collection()
    qd.upsert(ids, embed_texts(texts), payloads)

    print(f"Ingested {len(chunks)} chunks from {len(set(p['doc_id'] for p in payloads))} documents.")
    return len(chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest knowledge into ES + Qdrant.")
    parser.add_argument("--knowledge-dir", type=Path, default=KNOWLEDGE_DIR)
    args = parser.parse_args()
    ingest(args.knowledge_dir)
