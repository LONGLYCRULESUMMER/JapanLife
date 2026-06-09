from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    citations: list[str]
    thread_id: str
    route: str | None = None
