from pathlib import Path

from rag.chunking import Chunk

from app.knowledge_admin import KnowledgeAdminService


class _FakeES:
    def __init__(self):
        self.deleted: list[list[str]] = []

    def delete_chunks(self, ids: list[str]) -> None:
        self.deleted.append(ids)


class _FakeQdrant:
    def __init__(self):
        self.deleted: list[list[str]] = []

    def delete(self, ids: list[str]) -> None:
        self.deleted.append(ids)


def test_delete_stale_chunks_deletes_manifest_ids_missing_from_current_chunks(
    tmp_path: Path,
):
    service = KnowledgeAdminService(tmp_path)
    stale_chunk = Chunk(
        text="old",
        metadata={
            "doc_id": "tax/old-guide.md",
            "domain": "tax",
            "section_path": "Old",
            "chunk_index": 0,
        },
    )
    current_chunk = Chunk(
        text="new",
        metadata={
            "doc_id": "tax/current-guide.md",
            "domain": "tax",
            "section_path": "Current",
            "chunk_index": 0,
        },
    )
    service.write_manifest_from_chunks([stale_chunk, current_chunk])
    manifest = service.read_manifest()
    assert set(manifest) >= {"documents", "deleted_documents"}
    assert manifest["documents"]["tax/old-guide.md"]["chunk_ids"] == [stale_chunk.chunk_id]
    es = _FakeES()
    qdrant = _FakeQdrant()

    stale = service.delete_stale_chunks({current_chunk.chunk_id}, es, qdrant)

    assert stale == [stale_chunk.chunk_id]
    assert es.deleted == [[stale_chunk.chunk_id]]
    assert qdrant.deleted == [[stale_chunk.chunk_id]]


def test_delete_stale_chunks_without_manifest_is_noop(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    es = _FakeES()
    qdrant = _FakeQdrant()

    stale = service.delete_stale_chunks({"current"}, es, qdrant)

    assert stale == []
    assert es.deleted == []
    assert qdrant.deleted == []


def test_soft_delete_preserves_deleted_document_record(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    (tmp_path / "tax").mkdir()
    (tmp_path / "tax" / "old-guide.md").write_text(
        "---\n"
        "doc_title: Old Guide\n"
        "source_url: https://example.com/old\n"
        "language: en\n"
        "---\n\n"
        "# Old Guide\n\n## Intro\nOld body.",
        encoding="utf-8",
    )
    chunks = service.all_active_chunks()
    service.write_manifest_from_chunks(chunks)

    service.soft_delete_document("tax/old-guide.md")

    manifest = service.read_manifest()
    assert "tax/old-guide.md" not in manifest["documents"]
    assert manifest["deleted_documents"]["tax/old-guide.md"]["chunk_ids"] == [
        chunks[0].chunk_id
    ]
