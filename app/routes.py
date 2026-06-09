from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage

from agents.output import extract_citations, extract_reply
from app.schemas import ChatRequest, ChatResponse

router = APIRouter()


def get_graph(request: Request):
    return request.app.state.graph


def _initial_state(message: str) -> dict:
    return {"messages": [HumanMessage(content=message)], "user_language": "", "active_domain": None, "citations": []}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, graph=Depends(get_graph)) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    result = graph.invoke(_initial_state(req.message), config={"configurable": {"thread_id": thread_id}})
    return ChatResponse(
        reply=extract_reply(result["messages"]),
        citations=extract_citations(result["messages"]),
        thread_id=thread_id,
        route=result.get("active_domain"),
    )


@router.get("/health")
def health():
    from rag.es_store import ESStore
    from rag.qdrant_store import QdrantStore

    def _ok(fn) -> bool:
        try:
            fn()
            return True
        except Exception:
            return False

    es = _ok(lambda: ESStore().client.info())
    qd = _ok(lambda: QdrantStore().client.get_collections())
    return {"status": "ok" if es and qd else "degraded", "elasticsearch": es, "qdrant": qd}
