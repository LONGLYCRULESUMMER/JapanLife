from rag.chunking import Chunk, chunk_markdown

MD = """# 税务指南

## 确定申告
确定申告是日本的年度个人所得税申报。

## ふるさと納税
ふるさと納税是一种向地方政府捐款的制度。
"""


def test_splits_by_section():
    chunks = chunk_markdown(MD, {"doc_id": "tax/guide.md"})
    paths = [c.metadata["section_path"] for c in chunks]
    assert "税务指南 > 确定申告" in paths
    assert "税务指南 > ふるさと納税" in paths


def test_long_section_splits_with_overlap():
    body = "あ" * 3000
    md = f"# T\n## S\n{body}"
    chunks = chunk_markdown(md, {"doc_id": "d"}, max_chars=1000, overlap=100)
    assert len(chunks) >= 3
    assert chunks[0].text[-50:] in chunks[1].text


def test_chunk_id_is_deterministic_and_unique():
    chunks = chunk_markdown(MD, {"doc_id": "tax/guide.md"})
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    again = chunk_markdown(MD, {"doc_id": "tax/guide.md"})
    assert ids == [c.chunk_id for c in again]


def test_metadata_is_preserved():
    chunks = chunk_markdown(MD, {"doc_id": "tax/guide.md", "domain": "tax"})
    assert all(c.metadata["domain"] == "tax" for c in chunks)
