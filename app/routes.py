from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage
from sse_starlette.sse import EventSourceResponse

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


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, graph=Depends(get_graph)):
    thread_id = req.thread_id or str(uuid.uuid4())

    def event_gen():
        for update in graph.stream(
            _initial_state(req.message),
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            for node, payload in update.items():
                msgs = payload.get("messages", []) if isinstance(payload, dict) else []
                text = extract_reply(msgs)
                data = {"node": node, "delta": text, "route": payload.get("active_domain") if isinstance(payload, dict) else None}
                yield {"event": "update", "data": json.dumps(data, ensure_ascii=False)}
        yield {"event": "done", "data": json.dumps({"thread_id": thread_id}, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
