from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    citations: list[str]
    thread_id: str
    route: str | None = None


class KnowledgeDocRequest(BaseModel):
    domain: str
    filename: str
    doc_title: str = ""
    source_url: str = ""
    language: str = ""
    body: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: str | None = None


class KnowledgeDocResponse(BaseModel):
    doc_id: str
    domain: str
    filename: str
    doc_title: str
    source_url: str
    language: str
    metadata: dict[str, Any]
    body: str
    content: str
    needs_reindex: bool = False


class KnowledgeDocListResponse(BaseModel):
    documents: list[KnowledgeDocResponse]


class KnowledgeValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class ChunkPreviewItem(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any]


class ChunkPreviewResponse(BaseModel):
    chunks: list[ChunkPreviewItem]
