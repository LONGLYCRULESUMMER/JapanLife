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


def test_build_chunks_uses_front_matter(tmp_path: Path):
    (tmp_path / "visa").mkdir()
    (tmp_path / "visa" / "renewal.md").write_text(
        "---\n"
        "doc_title: Visa Renewal\n"
        "source_url: https://immi.example/renewal\n"
        "language: en\n"
        "---\n"
        "# Renewal\n## Window\nApply within 3 months of expiry.",
        encoding="utf-8",
    )
    chunks = build_chunks(load_documents(tmp_path))
    assert chunks
    c = chunks[0]
    assert c.metadata["doc_title"] == "Visa Renewal"
    assert c.metadata["source_url"] == "https://immi.example/renewal"
    assert c.metadata["language"] == "en"
    assert "doc_title" not in c.text  # front matter stripped from indexed text


def test_build_chunks_without_front_matter_falls_back_to_stem(tmp_path: Path):
    (tmp_path / "tax").mkdir()
    (tmp_path / "tax" / "guide.md").write_text("# T\n## S\nbody", encoding="utf-8")
    chunks = build_chunks(load_documents(tmp_path))
    assert chunks[0].metadata["doc_title"] == "guide"
    assert chunks[0].metadata["source_url"] == ""
    assert chunks[0].metadata["language"] == "mixed"
