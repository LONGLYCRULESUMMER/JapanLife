from pathlib import Path

import pytest

from app.knowledge_admin import KnowledgeAdminService


def _payload(
    *,
    domain: str = "tax",
    filename: str = "sample-guide.md",
    body: str = "# Sample Guide\n\n## Overview\nBring your documents.",
    metadata: dict | None = None,
) -> dict:
    return {
        "domain": domain,
        "filename": filename,
        "doc_title": (metadata or {}).get("doc_title", "Sample Guide"),
        "source_url": (metadata or {}).get("source_url", "https://example.com/sample"),
        "language": (metadata or {}).get("language", "en"),
        "metadata": metadata
        or {
            "doc_title": "Sample Guide",
            "source_url": "https://example.com/sample",
            "language": "en",
        },
        "body": body,
    }


def test_parse_and_render_markdown_document_round_trips_front_matter(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    markdown = (
        "---\n"
        "doc_title: Tax Filing\n"
        "source_url: https://example.com/tax\n"
        "language: en\n"
        "---\n\n"
        "# Tax Filing\n\nBody text."
    )

    metadata, body = service.parse_markdown_document(markdown)

    assert metadata == {
        "doc_title": "Tax Filing",
        "source_url": "https://example.com/tax",
        "language": "en",
    }
    assert body == "# Tax Filing\n\nBody text."
    rendered = service.render_markdown_document(metadata, body)
    assert service.parse_markdown_document(rendered) == (metadata, body)


@pytest.mark.parametrize(
    "doc_id",
    [
        "tax/../secret.md",
        "tax/nested/file.md",
        "../tax/file.md",
        "unknown/sample-guide.md",
        "tax/Sample-Guide.md",
        "tax/sample_guide.md",
        "tax/sample-guide.txt",
    ],
)
def test_resolve_doc_path_rejects_path_traversal_and_invalid_names(
    tmp_path: Path, doc_id: str
):
    service = KnowledgeAdminService(tmp_path)

    with pytest.raises(ValueError):
        service.resolve_doc_path(doc_id)


def test_create_list_get_update_and_soft_delete_document(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    created = service.create_document(_payload(filename="sample-guide.ja.md"))

    assert created["doc_id"] == "tax/sample-guide.ja.md"
    assert (tmp_path / "tax" / "sample-guide.ja.md").exists()
    assert "doc_title: Sample Guide" in created["content"]

    listed = service.list_documents(domain="tax", q="sample")
    assert [doc["doc_id"] for doc in listed] == ["tax/sample-guide.ja.md"]

    got = service.get_document("tax/sample-guide.ja.md")
    assert got["metadata"]["language"] == "en"
    assert got["body"].startswith("# Sample Guide")

    updated = service.update_document(
        "tax/sample-guide.ja.md",
        _payload(
            filename="sample-guide.ja.md",
            body="# Sample Guide\n\n## Updated\nUpdated body.",
        ),
    )
    assert "Updated body" in updated["body"]
    assert "Updated body" in (tmp_path / "tax" / "sample-guide.ja.md").read_text(
        encoding="utf-8"
    )

    deleted = service.soft_delete_document("tax/sample-guide.ja.md")
    assert deleted["doc_id"] == "tax/sample-guide.ja.md"
    assert not (tmp_path / "tax" / "sample-guide.ja.md").exists()
    assert (tmp_path / ".trash" / "tax" / "sample-guide.ja.md").exists()
    assert service.list_documents(domain="tax") == []
    with pytest.raises(FileNotFoundError):
        service.get_document("tax/sample-guide.ja.md")


def test_validate_document_returns_errors_and_source_warnings(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)

    invalid = service.validate_document(
        {
            "domain": "bad",
            "filename": "Bad_Name.md",
            "metadata": {"source_url": "ftp://example.com/doc"},
            "body": "",
        }
    )

    assert invalid["valid"] is False
    assert any("domain" in error for error in invalid["errors"])
    assert any("filename" in error for error in invalid["errors"])
    assert any("body" in error for error in invalid["errors"])
    assert "Missing doc_title" in invalid["errors"]
    assert "Missing language" in invalid["errors"]
    assert any("source_url" in warning for warning in invalid["warnings"])

    invalid_language = service.validate_document(
        _payload(metadata={"doc_title": "Sample", "source_url": "https://example.com", "language": "xx"}),
        check_source=False,
    )

    assert invalid_language["valid"] is False
    assert "language must be en, ja, or mixed" in invalid_language["errors"]

    valid_with_warning = service.validate_document(
        _payload(metadata={"doc_title": "Sample", "source_url": "not-a-url", "language": "en"}),
        check_source=True,
    )

    assert valid_with_warning["valid"] is True
    assert valid_with_warning["errors"] == []
    assert any("source_url" in warning for warning in valid_with_warning["warnings"])


def test_validate_document_warns_for_private_source_url(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)

    result = service.validate_document(
        _payload(
            metadata={
                "doc_title": "Sample",
                "source_url": "http://169.254.169.254/latest/meta-data/",
                "language": "en",
            }
        )
    )

    assert result["valid"] is True
    assert any(
        "private" in warning or "link-local" in warning
        for warning in result["warnings"]
    )


def test_create_document_accepts_flat_front_matter_fields(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)

    created = service.create_document(
        {
            "domain": "tax",
            "filename": "flat-guide.md",
            "doc_title": "Flat Guide",
            "source_url": "https://example.com/flat",
            "language": "en",
            "body": "# Flat Guide\n\n## Overview\nBody.",
        }
    )

    assert created["doc_title"] == "Flat Guide"
    assert created["metadata"]["doc_title"] == "Flat Guide"


def test_preview_chunks_returns_chunk_ids_text_and_metadata(tmp_path: Path):
    service = KnowledgeAdminService(tmp_path)
    service.create_document(
        _payload(
            body="# Sample Guide\n\n## Requirements\nBring your passport and card.",
        )
    )

    chunks = service.preview_chunks("tax/sample-guide.md")

    assert chunks
    first = chunks[0]
    assert set(first) == {"chunk_id", "text", "metadata"}
    assert first["text"] == "Bring your passport and card."
    assert first["metadata"]["domain"] == "tax"
    assert first["metadata"]["doc_id"] == "tax/sample-guide.md"
    assert first["metadata"]["doc_title"] == "Sample Guide"


def test_all_active_chunks_tracks_non_admin_filename_that_ingest_would_index(
    tmp_path: Path,
):
    service = KnowledgeAdminService(tmp_path)
    (tmp_path / "tax").mkdir()
    (tmp_path / "tax" / "README.md").write_text(
        "# Legacy\n\n## Intro\nLegacy body.",
        encoding="utf-8",
    )

    chunks = service.all_active_chunks()

    assert [chunk.metadata["doc_id"] for chunk in chunks] == ["tax/README.md"]
