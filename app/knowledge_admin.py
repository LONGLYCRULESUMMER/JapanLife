from __future__ import annotations

import json
import ipaddress
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from rag.chunking import Chunk, chunk_markdown, split_front_matter


class KnowledgeAdminService:
    ALLOWED_DOMAINS = {"tax", "visa", "ward_office"}
    FILENAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.ja)?\.md$")
    REQUIRED_METADATA = ("doc_title", "source_url", "language")
    VALID_LANGUAGES = {"en", "ja", "mixed"}

    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = Path(knowledge_dir).resolve()
        self.manifest_path = self.knowledge_dir / ".manifest.json"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def resolve_doc_path(self, doc_id: str) -> Path:
        domain, filename = self._split_doc_id(doc_id)
        return self._path_for(domain, filename)

    def parse_markdown_document(self, markdown: str) -> tuple[dict, str]:
        return split_front_matter(markdown)

    def render_markdown_document(self, metadata: dict, body: str) -> str:
        clean_body = body.rstrip()
        if not metadata:
            return f"{clean_body}\n" if clean_body else ""

        lines = ["---"]
        for key, value in metadata.items():
            if value is None:
                continue
            rendered_value = str(value).replace("\n", " ").strip()
            lines.append(f"{key}: {rendered_value}")
        lines.extend(["---", "", clean_body])
        return "\n".join(lines).rstrip() + "\n"

    def list_documents(
        self, domain: str | None = None, q: str | None = None
    ) -> list[dict]:
        domains = [domain] if domain else sorted(self.ALLOWED_DOMAINS)
        for candidate in domains:
            self._validate_domain(candidate)

        query = (q or "").strip().lower()
        documents: list[dict] = []
        for current_domain in domains:
            domain_dir = self.knowledge_dir / current_domain
            if not domain_dir.exists():
                continue
            for path in sorted(domain_dir.glob("*.md")):
                if not self.FILENAME_RE.fullmatch(path.name):
                    continue
                document = self._document_from_path(path)
                if query and query not in self._search_text(document):
                    continue
                documents.append(document)
        return sorted(documents, key=lambda doc: doc["doc_id"])

    def get_document(self, doc_id: str) -> dict:
        path = self.resolve_doc_path(doc_id)
        if not path.exists():
            raise FileNotFoundError(doc_id)
        return self._document_from_path(path) | {"needs_reindex": True}

    def create_document(self, payload: Any) -> dict:
        data = self._normalise_payload(payload)
        validation = self.validate_document(data, check_source=False)
        if not validation["valid"]:
            raise ValueError("; ".join(validation["errors"]))

        path = self._path_for(data["domain"], data["filename"])
        if path.exists():
            raise FileExistsError(data["doc_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.render_markdown_document(data["metadata"], data["body"]),
            encoding="utf-8",
        )
        return self._document_from_path(path) | {"needs_reindex": True}

    def update_document(self, doc_id: str, payload: Any) -> dict:
        path = self.resolve_doc_path(doc_id)
        if not path.exists():
            raise FileNotFoundError(doc_id)

        data = self._normalise_payload(payload)
        path_domain, path_filename = self._split_doc_id(doc_id)
        if data["domain"] != path_domain or data["filename"] != path_filename:
            raise ValueError("payload domain and filename must match doc_id")

        validation = self.validate_document(data, check_source=False)
        if not validation["valid"]:
            raise ValueError("; ".join(validation["errors"]))

        path.write_text(
            self.render_markdown_document(data["metadata"], data["body"]),
            encoding="utf-8",
        )
        return self._document_from_path(path) | {"needs_reindex": True}

    def soft_delete_document(self, doc_id: str) -> dict:
        path = self.resolve_doc_path(doc_id)
        if not path.exists():
            raise FileNotFoundError(doc_id)

        document = self._document_from_path(path)
        domain, filename = self._split_doc_id(doc_id)
        manifest = self.read_manifest()
        existing = manifest.get("documents", {}).pop(doc_id, None)
        chunk_ids = list((existing or {}).get("chunk_ids", []))
        if not chunk_ids:
            chunk_ids = [chunk.chunk_id for chunk in self._chunks_for_document(document)]
        manifest.setdefault("deleted_documents", {})[doc_id] = {
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "chunk_ids": chunk_ids,
        }
        self.write_manifest(manifest)
        trash_path = self._trash_path(domain, filename)
        trash_path.parent.mkdir(parents=True, exist_ok=True)
        if trash_path.exists():
            trash_path.unlink()
        path.replace(trash_path)
        return document | {"needs_reindex": True}

    def validate_document(self, payload: Any, check_source: bool = True) -> dict:
        errors: list[str] = []
        warnings: list[str] = []
        data = self._normalise_payload(payload, validate_paths=False)

        try:
            self._validate_domain(data.get("domain", ""))
        except ValueError as exc:
            errors.append(str(exc))

        try:
            self._validate_filename(data.get("filename", ""))
        except ValueError as exc:
            errors.append(str(exc))

        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            errors.append("metadata must be an object")
            metadata = {}
        for key in self.REQUIRED_METADATA:
            if not str(metadata.get(key, "")).strip():
                errors.append(f"Missing {key}")
        language = str(metadata.get("language", "")).strip()
        if language and language not in self.VALID_LANGUAGES:
            errors.append("language must be en, ja, or mixed")

        body = data.get("body") or ""
        if not isinstance(body, str) or not body.strip():
            errors.append("body is required")
        elif not re.search(r"^#{1,6}\s+\S+", body, flags=re.MULTILINE):
            errors.append("Markdown body must contain at least one heading")

        if check_source:
            warnings.extend(self._source_warnings(metadata))

        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def preview_chunks(self, doc_id: str) -> list[dict]:
        document = self.get_document(doc_id)
        return [
            self._chunk_response(chunk)
            for chunk in self._chunks_for_document(document)
        ]

    def all_active_chunks(self) -> list[Chunk]:
        chunks: list[Chunk] = []
        for path in self._active_markdown_paths():
            chunks.extend(self._chunks_for_document(self._document_from_path(path)))
        return chunks

    def read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"documents": {}, "deleted_documents": {}}
        with self.manifest_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if "documents" not in data:
            documents: dict[str, dict] = {}
            for record in data.get("chunks", []):
                doc_id = record.get("doc_id", "")
                if not doc_id:
                    continue
                documents.setdefault(doc_id, {"status": "active", "chunk_ids": [], "updated_at": data.get("updated_at", "")})
                documents[doc_id]["chunk_ids"].append(record.get("chunk_id", ""))
            data = {"documents": documents, "deleted_documents": {}}
        data.setdefault("documents", {})
        data.setdefault("deleted_documents", {})
        return data

    def write_manifest(self, manifest: dict) -> dict:
        normalised = {
            "documents": manifest.get("documents", {}),
            "deleted_documents": manifest.get("deleted_documents", {}),
            "updated_at": manifest.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        }
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        next_path = self.manifest_path.with_name(".manifest.json.next")
        next_path.write_text(
            json.dumps(normalised, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        next_path.replace(self.manifest_path)
        return normalised

    def write_manifest_from_chunks(self, chunks: Iterable[Chunk]) -> dict:
        chunk_list = list(chunks)
        now = datetime.now(timezone.utc).isoformat()
        documents: dict[str, dict] = {}
        for chunk in chunk_list:
            doc_id = str(chunk.metadata.get("doc_id", ""))
            if not doc_id:
                continue
            documents.setdefault(doc_id, {"status": "active", "chunk_ids": [], "updated_at": now})
            documents[doc_id]["chunk_ids"].append(chunk.chunk_id)
        for record in documents.values():
            record["chunk_ids"] = sorted(set(record["chunk_ids"]))
        manifest = {
            "updated_at": now,
            "documents": documents,
            "deleted_documents": self.read_manifest().get("deleted_documents", {}),
        }
        return self.write_manifest(manifest)

    def delete_stale_chunks(
        self, current_chunk_ids: Iterable[str], es, qdrant
    ) -> list[str]:
        manifest = self.read_manifest()
        previous_ids = {
            chunk_id
            for record in manifest.get("documents", {}).values()
            for chunk_id in record.get("chunk_ids", [])
        }
        previous_ids.update(
            chunk_id
            for record in manifest.get("deleted_documents", {}).values()
            for chunk_id in record.get("chunk_ids", [])
        )
        stale_ids = sorted(previous_ids - set(current_chunk_ids))
        if stale_ids:
            es.delete_chunks(stale_ids)
            qdrant.delete(stale_ids)
            stale_set = set(stale_ids)
            changed = False
            for record in manifest.get("deleted_documents", {}).values():
                original = list(record.get("chunk_ids", []))
                remaining = [chunk_id for chunk_id in original if chunk_id not in stale_set]
                if remaining != original:
                    record["chunk_ids"] = remaining
                    record["cleaned_at"] = datetime.now(timezone.utc).isoformat()
                    changed = True
            if changed:
                self.write_manifest(manifest)
        return stale_ids

    def _normalise_payload(
        self, payload: Any, validate_paths: bool = True
    ) -> dict[str, Any]:
        if hasattr(payload, "model_dump"):
            raw = payload.model_dump(exclude_none=True)
        else:
            raw = dict(payload or {})

        metadata = dict(raw.get("metadata") or {})
        for key in self.REQUIRED_METADATA:
            if raw.get(key) is not None:
                metadata[key] = raw.get(key)
        body = raw.get("body") or ""
        content = raw.get("content")
        if content is not None and not body:
            parsed_metadata, parsed_body = self.parse_markdown_document(str(content))
            metadata = metadata or parsed_metadata
            body = parsed_body

        domain = raw.get("domain") or ""
        filename = raw.get("filename") or ""
        data = {
            "domain": domain,
            "filename": filename,
            "doc_id": f"{domain}/{filename}" if domain and filename else "",
            "metadata": dict(metadata) if isinstance(metadata, dict) else metadata,
            "body": body,
        }
        if validate_paths:
            self._validate_domain(domain)
            self._validate_filename(filename)
        return data

    def _split_doc_id(self, doc_id: str) -> tuple[str, str]:
        parts = doc_id.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("doc_id must be in the form domain/filename")
        domain, filename = parts
        self._validate_domain(domain)
        self._validate_filename(filename)
        return domain, filename

    def _validate_domain(self, domain: str) -> None:
        if domain not in self.ALLOWED_DOMAINS:
            allowed = ", ".join(sorted(self.ALLOWED_DOMAINS))
            raise ValueError(f"domain must be one of: {allowed}")

    def _validate_filename(self, filename: str) -> None:
        if not self.FILENAME_RE.fullmatch(filename or ""):
            raise ValueError(
                "filename must be lowercase kebab-case ending in .md or .ja.md"
            )

    def _path_for(self, domain: str, filename: str) -> Path:
        self._validate_domain(domain)
        self._validate_filename(filename)
        domain_dir = (self.knowledge_dir / domain).resolve()
        path = (domain_dir / filename).resolve()
        if path.parent != domain_dir:
            raise ValueError("doc_id cannot traverse outside the domain directory")
        return path

    def _trash_path(self, domain: str, filename: str) -> Path:
        trash_domain = (self.knowledge_dir / ".trash" / domain).resolve()
        path = (trash_domain / filename).resolve()
        if path.parent != trash_domain:
            raise ValueError("doc_id cannot traverse outside the trash directory")
        return path

    def _document_from_path(self, path: Path) -> dict:
        metadata, body = self.parse_markdown_document(path.read_text(encoding="utf-8"))
        domain = path.parent.name
        filename = path.name
        doc_id = f"{domain}/{filename}"
        content = self.render_markdown_document(metadata, body)
        return {
            "doc_id": doc_id,
            "domain": domain,
            "filename": filename,
            "doc_title": metadata.get("doc_title") or Path(filename).stem,
            "source_url": metadata.get("source_url", ""),
            "language": metadata.get("language", "mixed"),
            "metadata": metadata,
            "body": body,
            "content": content,
            "needs_reindex": False,
        }

    def _search_text(self, document: dict) -> str:
        values = [
            document["doc_id"],
            document["filename"],
            document["body"],
            *[str(value) for value in document["metadata"].values()],
        ]
        return "\n".join(values).lower()

    def _chunk_metadata(self, document: dict) -> dict:
        metadata = document["metadata"]
        return {
            "domain": document["domain"],
            "doc_id": document["doc_id"],
            "doc_title": metadata.get("doc_title") or Path(document["filename"]).stem,
            "source_url": metadata.get("source_url", ""),
            "language": metadata.get("language", "mixed"),
        }

    def _chunks_for_document(self, document: dict) -> list[Chunk]:
        return chunk_markdown(document["body"], self._chunk_metadata(document))

    def _chunk_response(self, chunk: Chunk) -> dict:
        return {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "metadata": chunk.metadata,
        }

    def _source_warnings(self, metadata: dict) -> list[str]:
        source_url = str(metadata.get("source_url", "")).strip()
        if not source_url:
            return ["source_url is missing"]

        parsed = urlparse(source_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not parsed.hostname
        ):
            return ["source_url should be an absolute http(s) URL"]

        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            return []
        address_warning = self._unsafe_source_address_warning(address)
        if address_warning:
            return [address_warning]
        return []

    def _active_markdown_paths(self) -> list[Path]:
        paths: list[Path] = []
        for domain in sorted(self.ALLOWED_DOMAINS):
            domain_dir = self.knowledge_dir / domain
            if domain_dir.exists():
                paths.extend(sorted(domain_dir.glob("*.md")))
        return paths

    def _unsafe_source_address_warning(self, address: ipaddress._BaseAddress) -> str | None:
        if (
            address.is_loopback
            or address.is_link_local
            or address.is_private
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            return (
                "source_url resolves to a private or link-local "
                f"address: {address}"
            )
        return None
