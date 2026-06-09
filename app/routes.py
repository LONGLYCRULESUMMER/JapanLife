from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import HumanMessage
from sse_starlette.sse import EventSourceResponse

from agents.output import extract_citations, extract_reply
from app.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_RECURSION_LIMIT = 50


def get_graph(request: Request):
    return request.app.state.graph


def get_retriever():
    from rag.retriever import get_default_retriever

    return get_default_retriever()


def _initial_state(message: str) -> dict:
    return {"messages": [HumanMessage(content=message)], "user_language": "", "active_domain": None, "citations": []}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, graph=Depends(get_graph)) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    try:
        result = graph.invoke(
            _initial_state(req.message),
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": _RECURSION_LIMIT},
        )
    except Exception:
        logger.exception("Chat graph execution failed for thread %s", thread_id)
        raise HTTPException(status_code=503, detail="The assistant is temporarily unavailable. Please try again.")
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


@router.get("/search")
def search(q: str, domain: str = "", top_k: int = 5, retriever=Depends(get_retriever)):
    try:
        chunks = retriever.search(q, domain=domain or None)[:top_k]
    except Exception:
        logger.exception("Search failed for query %r", q)
        raise HTTPException(status_code=503, detail="Search is temporarily unavailable.")
    return {
        "query": q,
        "domain": domain or None,
        "results": [
            {
                "rank": i,
                "citation": c.citation,
                "score": round(c.score, 4),
                "domain": c.metadata.get("domain"),
                "snippet": c.text[:400],
            }
            for i, c in enumerate(chunks, 1)
        ],
    }


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, graph=Depends(get_graph)):
    thread_id = req.thread_id or str(uuid.uuid4())

    def event_gen():
        try:
            for update in graph.stream(
                _initial_state(req.message),
                config={"configurable": {"thread_id": thread_id}, "recursion_limit": _RECURSION_LIMIT},
                stream_mode="updates",
            ):
                for node, payload in update.items():
                    msgs = payload.get("messages", []) if isinstance(payload, dict) else []
                    text = extract_reply(msgs)
                    data = {"node": node, "delta": text, "route": payload.get("active_domain") if isinstance(payload, dict) else None}
                    yield {"event": "update", "data": json.dumps(data, ensure_ascii=False)}
        except Exception:
            logger.exception("Chat stream failed for thread %s", thread_id)
            yield {"event": "error", "data": json.dumps({"error": "The assistant stream failed."}, ensure_ascii=False)}
            return
        yield {"event": "done", "data": json.dumps({"thread_id": thread_id}, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
