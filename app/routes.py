from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from sse_starlette.sse import EventSourceResponse

from agents.output import extract_citations, extract_reply
from app.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_RECURSION_LIMIT = 50
_SPECIALISTS = {"tax", "visa", "ward_office"}


def _domain_from_namespace(namespace) -> str | None:
    """A specialist subgraph streams under a namespace like ('tax:<uuid>',)."""
    for part in namespace or ():
        name = part.split(":", 1)[0]
        if name in _SPECIALISTS:
            return name
    return None


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

    def _sse(event: str, payload: dict) -> dict:
        return {"event": event, "data": json.dumps(payload, ensure_ascii=False)}

    def event_gen():
        tool_messages: list = []
        route_sent: str | None = None
        try:
            for namespace, (chunk, _meta) in graph.stream(
                _initial_state(req.message),
                config={"configurable": {"thread_id": thread_id}, "recursion_limit": _RECURSION_LIMIT},
                stream_mode="messages",
                subgraphs=True,
            ):
                domain = _domain_from_namespace(namespace)
                if domain and domain != route_sent:
                    route_sent = domain
                    yield _sse("route", {"route": domain})

                if isinstance(chunk, ToolMessage):
                    tool_messages.append(chunk)
                    # A tool ran, so any text streamed before it was a preamble: tell the
                    # client to reset the in-progress answer and surface the tool step.
                    yield _sse("tool", {"name": getattr(chunk, "name", "") or "tool"})
                    continue

                if domain and isinstance(chunk, AIMessageChunk):
                    text = chunk.content if isinstance(chunk.content, str) else ""
                    if text:
                        yield _sse("token", {"text": text})
        except Exception:
            logger.exception("Chat stream failed for thread %s", thread_id)
            yield _sse("error", {"error": "The assistant stream failed."})
            return
        yield _sse("done", {"thread_id": thread_id, "citations": extract_citations(tool_messages)})

    return EventSourceResponse(event_gen())
