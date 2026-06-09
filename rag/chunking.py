from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        base = "::".join(
            [
                str(self.metadata.get("doc_id", "")),
                str(self.metadata.get("section_path", "")),
                str(self.metadata.get("chunk_index", 0)),
            ]
        )
        return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    stack: list[str] = []
    buf: list[str] = []
    path = ""

    def flush() -> None:
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            sections.append((path, body))
        buf = []

    for line in markdown.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            stack[:] = stack[: level - 1]
            while len(stack) < level - 1:
                stack.append("")
            stack.append(title)
            path = " > ".join(s for s in stack if s)
        else:
            buf.append(line)
    flush()
    return sections


def chunk_markdown(
    markdown: str,
    metadata: dict,
    max_chars: int = 1200,
    overlap: int = 150,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for section_path, body in _split_sections(markdown):
        start = 0
        while start < len(body):
            piece = body[start : start + max_chars].strip()
            meta = {**metadata, "section_path": section_path, "chunk_index": idx}
            chunks.append(Chunk(text=piece, metadata=meta))
            idx += 1
            if start + max_chars >= len(body):
                break
            start += max_chars - overlap
    return chunks
