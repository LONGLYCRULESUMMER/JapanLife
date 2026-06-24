from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from sse_starlette.sse import EventSourceResponse

from agents.output import extract_citations, extract_reply, reconstruct_messages
from app.knowledge_admin import KnowledgeAdminService
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkPreviewResponse,
    KnowledgeDocListResponse,
    KnowledgeDocRequest,
    KnowledgeDocResponse,
    KnowledgeValidationResponse,
)

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


def get_job_registry(request: Request):
    return request.app.state.job_registry


def get_ingest_fn():
    """Return the default ingest callable. Overridable in tests (no services needed)."""
    from rag.ingest import ingest

    return ingest


def get_knowledge_admin_service():
    return KnowledgeAdminService(Path(__file__).resolve().parent.parent / "knowledge")


def get_reindex_fn(service: KnowledgeAdminService = Depends(get_knowledge_admin_service)):
    def _reindex() -> int:
        from rag.es_store import ESStore
        from rag.ingest import ingest
        from rag.qdrant_store import QdrantStore

        count = ingest(service.knowledge_dir)
        chunks = service.all_active_chunks()
        service.delete_stale_chunks(
            [chunk.chunk_id for chunk in chunks], ESStore(), QdrantStore()
        )
        service.write_manifest_from_chunks(chunks)
        return count

    return _reindex


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


_LIST_THREADS_SQL = (
    "SELECT thread_id, MAX(checkpoint_id) AS mx FROM checkpoints "
    "GROUP BY thread_id ORDER BY mx DESC LIMIT ?"
)


@router.get("/conversations")
def list_conversations(limit: int = 30, graph=Depends(get_graph)):
    """List past conversations (most recent first), titled by their first user message."""
    try:
        rows = graph.checkpointer.conn.execute(_LIST_THREADS_SQL, (limit,)).fetchall()
    except Exception:
        logger.exception("Listing conversations failed")
        return {"conversations": []}

    conversations = []
    for tid, _mx in rows:
        try:
            state = graph.get_state({"configurable": {"thread_id": tid}})
            turns = reconstruct_messages(state.values.get("messages", []))
        except Exception:
            turns = []
        title = next((t["content"] for t in turns if t["role"] == "user"), None)
        if not title:
            continue
        conversations.append(
            {"thread_id": tid, "title": title[:80], "turns": sum(1 for t in turns if t["role"] == "user")}
        )
    return {"conversations": conversations}


@router.get("/conversations/{thread_id}")
def get_conversation(thread_id: str, graph=Depends(get_graph)):
    """Return a past conversation's messages as display turns."""
    try:
        state = graph.get_state({"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])
    except Exception:
        logger.exception("Loading conversation %s failed", thread_id)
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"thread_id": thread_id, "messages": reconstruct_messages(messages)}


@router.delete("/conversations/{thread_id}")
def delete_conversation(thread_id: str, graph=Depends(get_graph)):
    """Delete a stored conversation from the checkpointer."""
    try:
        graph.checkpointer.delete_thread(thread_id)
    except Exception:
        logger.exception("Deleting conversation %s failed", thread_id)
        raise HTTPException(status_code=503, detail="Could not delete conversation.")
    return {"deleted": thread_id}


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


@router.post("/admin/ingest", status_code=202)
def trigger_ingest(
    background_tasks: BackgroundTasks,
    registry=Depends(get_job_registry),
    ingest_fn=Depends(get_ingest_fn),
):
    """Kick off a knowledge-base ingest as a background job; returns the job record."""
    job = registry.create()
    background_tasks.add_task(registry.run, job.id, ingest_fn)
    return job.to_dict()


def _knowledge_doc_id(domain: str, filename: str) -> str:
    return f"{domain}/{filename}"


def _knowledge_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail="Knowledge document not found.")
    if isinstance(exc, FileExistsError):
        return HTTPException(status_code=409, detail="Knowledge document already exists.")
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/admin/knowledge/docs", response_model=KnowledgeDocListResponse)
def list_knowledge_documents(
    domain: str = "",
    q: str = "",
    service: KnowledgeAdminService = Depends(get_knowledge_admin_service),
):
    try:
        documents = service.list_documents(domain=domain or None, q=q or None)
    except ValueError as exc:
        raise _knowledge_error(exc)
    return KnowledgeDocListResponse(documents=documents)


@router.get(
    "/admin/knowledge/docs/{domain}/{filename}",
    response_model=KnowledgeDocResponse,
)
def get_knowledge_document(
    domain: str,
    filename: str,
    service: KnowledgeAdminService = Depends(get_knowledge_admin_service),
):
    try:
        return service.get_document(_knowledge_doc_id(domain, filename))
    except (FileNotFoundError, ValueError) as exc:
        raise _knowledge_error(exc)


@router.post(
    "/admin/knowledge/docs",
    response_model=KnowledgeDocResponse,
    status_code=201,
)
def create_knowledge_document(
    payload: KnowledgeDocRequest,
    service: KnowledgeAdminService = Depends(get_knowledge_admin_service),
):
    try:
        return service.create_document(payload)
    except (FileExistsError, ValueError) as exc:
        raise _knowledge_error(exc)


@router.put(
    "/admin/knowledge/docs/{domain}/{filename}",
    response_model=KnowledgeDocResponse,
)
def update_knowledge_document(
    domain: str,
    filename: str,
    payload: KnowledgeDocRequest,
    service: KnowledgeAdminService = Depends(get_knowledge_admin_service),
):
    try:
        return service.update_document(_knowledge_doc_id(domain, filename), payload)
    except (FileNotFoundError, ValueError) as exc:
        raise _knowledge_error(exc)


@router.delete(
    "/admin/knowledge/docs/{domain}/{filename}",
    response_model=KnowledgeDocResponse,
)
def delete_knowledge_document(
    domain: str,
    filename: str,
    service: KnowledgeAdminService = Depends(get_knowledge_admin_service),
):
    try:
        return service.soft_delete_document(_knowledge_doc_id(domain, filename))
    except (FileNotFoundError, ValueError) as exc:
        raise _knowledge_error(exc)


@router.post(
    "/admin/knowledge/validate",
    response_model=KnowledgeValidationResponse,
)
def validate_knowledge_document(
    payload: KnowledgeDocRequest,
    service: KnowledgeAdminService = Depends(get_knowledge_admin_service),
):
    return service.validate_document(payload)


@router.get(
    "/admin/knowledge/docs/{domain}/{filename}/chunks",
    response_model=list[ChunkPreviewResponse],
)
def preview_knowledge_chunks(
    domain: str,
    filename: str,
    service: KnowledgeAdminService = Depends(get_knowledge_admin_service),
):
    try:
        return service.preview_chunks(_knowledge_doc_id(domain, filename))
    except (FileNotFoundError, ValueError) as exc:
        raise _knowledge_error(exc)


@router.post("/admin/knowledge/reindex", status_code=202)
def trigger_knowledge_reindex(
    background_tasks: BackgroundTasks,
    registry=Depends(get_job_registry),
    reindex_fn=Depends(get_reindex_fn),
):
    job = registry.create()
    background_tasks.add_task(registry.run, job.id, reindex_fn)
    return job.to_dict()


@router.get("/admin/ingest/jobs")
def list_ingest_jobs(registry=Depends(get_job_registry)):
    return {"jobs": [job.to_dict() for job in registry.list()]}


@router.get("/admin/ingest/jobs/{job_id}")
def get_ingest_job(job_id: str, registry=Depends(get_job_registry)):
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingest job not found.")
    return job.to_dict()


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
