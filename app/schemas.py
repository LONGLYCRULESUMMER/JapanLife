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
    metadata: dict[str, Any] = Field(default_factory=dict)
    body: str = ""
    content: str | None = None


class KnowledgeDocResponse(BaseModel):
    doc_id: str
    domain: str
    filename: str
    metadata: dict[str, Any]
    body: str
    content: str


class KnowledgeDocListResponse(BaseModel):
    documents: list[KnowledgeDocResponse]


class KnowledgeValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class ChunkPreviewResponse(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any]
