from pathlib import Path

from rag.ingest import build_chunks, load_documents


def test_load_and_build(tmp_path: Path):
    (tmp_path / "tax").mkdir()
    (tmp_path / "tax" / "guide.md").write_text("# T\n## S\nbody text", encoding="utf-8")

    docs = load_documents(tmp_path)
    assert docs and docs[0][0] == "tax"

    chunks = build_chunks(docs)
    assert chunks
    c = chunks[0]
    assert c.metadata["domain"] == "tax"
    assert c.metadata["doc_id"] == "tax/guide.md"
    assert "content" not in c.metadata
