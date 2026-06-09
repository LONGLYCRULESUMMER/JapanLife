"""JapanLife — Streamlit demo.

A decoupled UI that talks to the FastAPI backend over HTTP. Showcases the tech stack,
architecture, an interactive multi-agent chat, and a hybrid-retrieval inspector.

Run:  make demo   (or  poetry run streamlit run streamlit_app.py)
Set API_URL to point at the backend (default http://localhost:8000).
"""
from __future__ import annotations

import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="JapanLife — 在日外国人智能助手", page_icon="🗾", layout="wide")


# --------------------------------------------------------------------------- helpers
def api_health() -> dict | None:
    try:
        return httpx.get(f"{API_URL}/health", timeout=5).json()
    except Exception:
        return None


def get_search(query: str, domain: str, top_k: int) -> dict:
    params = {"q": query, "top_k": top_k}
    if domain:
        params["domain"] = domain
    r = httpx.get(f"{API_URL}/search", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def stream_chat_events(message: str, thread_id: str | None):
    """Yield (event, data) tuples from the backend SSE /chat/stream endpoint."""
    payload = {"message": message}
    if thread_id:
        payload["thread_id"] = thread_id
    with httpx.stream("POST", f"{API_URL}/chat/stream", json=payload, timeout=None) as r:
        r.raise_for_status()
        event = None
        for line in r.iter_lines():
            if not line or line.startswith(":"):  # blank or keep-alive ping
                continue
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                yield event, json.loads(line[len("data:"):].strip())


def list_conversations() -> list[dict]:
    try:
        return httpx.get(f"{API_URL}/conversations", timeout=15).json().get("conversations", [])
    except Exception:
        return []


def load_conversation(thread_id: str) -> list[dict]:
    r = httpx.get(f"{API_URL}/conversations/{thread_id}", timeout=30)
    r.raise_for_status()
    return r.json().get("messages", [])


def delete_conversation(thread_id: str) -> None:
    try:
        httpx.delete(f"{API_URL}/conversations/{thread_id}", timeout=15)
    except Exception:
        pass


RETRIEVAL_DOT = """
digraph {
  rankdir=LR; bgcolor="transparent"; node [shape=box, style="rounded,filled", fillcolor="#eef3fb", fontname="Helvetica"];
  q  [label="Query (EN/JA)"];
  emb[label="BGE-m3\\nembed"];
  es [label="ElasticSearch\\nBM25 + kuromoji", fillcolor="#fdebd0"];
  qd [label="Qdrant\\ndense vectors", fillcolor="#d6eadf"];
  rrf[label="RRF fuse"];
  rr [label="cross-encoder\\nrerank"];
  out[label="cited chunks", fillcolor="#e8daef"];
  q -> emb -> qd -> rrf; q -> es -> rrf; rrf -> rr -> out;
}
"""

AGENT_DOT = """
digraph {
  rankdir=TB; bgcolor="transparent"; node [shape=box, style="rounded,filled", fillcolor="#eef3fb", fontname="Helvetica"];
  u  [label="User (EN/JA)"];
  sup[label="Supervisor (route)", fillcolor="#d4e6f1"];
  tax[label="tax agent"]; visa[label="visa agent"]; ward[label="ward_office agent"];
  kb [label="tools + hybrid\\nknowledge search", shape=ellipse, fillcolor="#fcf3cf"];
  u -> sup;
  sup -> tax; sup -> visa; sup -> ward;
  tax -> sup; visa -> sup; ward -> sup [label="answer"];
  ward -> visa [label="handoff", style=dashed, color="#c0392b"];
  ward -> tax  [label="handoff", style=dashed, color="#c0392b"];
  tax -> kb [style=dotted]; visa -> kb [style=dotted]; ward -> kb [style=dotted];
}
"""

TECH_STACK = [
    ("Orchestration", "LangGraph — supervisor + ReAct specialists + handoff"),
    ("LLM", "DeepSeek (langchain-deepseek); swappable in core/llm.py"),
    ("Sparse retrieval", "ElasticSearch BM25 + kuromoji (Japanese tokenizer)"),
    ("Dense retrieval", "Qdrant + BGE-m3 embeddings"),
    ("Fusion / rerank", "Reciprocal Rank Fusion + bge-reranker-v2-m3"),
    ("State", "LangGraph SQLite checkpointer (per thread_id)"),
    ("API", "FastAPI (/chat, /chat/stream SSE, /search, /health)"),
    ("Packaging", "Poetry, Docker, docker-compose, GitHub Actions CI"),
]

EVAL_ROWS = [
    ("es_only (BM25 + kuromoji)", "1.000", "0.833"),
    ("qdrant_only (BGE-m3 dense)", "1.000", "1.000"),
    ("hybrid (RRF + rerank)", "1.000", "0.929"),
]

DOMAIN_EMOJI = {"tax": "🧾", "visa": "🛂", "ward_office": "🏛️"}


# --------------------------------------------------------------------------- sidebar
st.session_state.setdefault("messages", [])
st.session_state.setdefault("thread_id", None)

with st.sidebar:
    st.title("🗾 JapanLife")
    st.caption("Multi-agent assistant for foreigners living in Japan")
    health = api_health()
    if health is None:
        st.warning(f"Backend unreachable at {API_URL}.\n\nStart it with `make up` (or `make serve`).")
    else:
        ok = health.get("status") == "ok"
        (st.success if ok else st.warning)(f"Backend: {health.get('status')}")
        st.write(
            f"- ElasticSearch: {'🟢' if health.get('elasticsearch') else '🔴'}\n"
            f"- Qdrant: {'🟢' if health.get('qdrant') else '🔴'}"
        )

    st.divider()
    hist_header = st.columns([4, 1])
    hist_header[0].subheader("🕑 History")
    if hist_header[1].button("↻", help="Refresh history"):
        st.session_state.pop("conversations_cache", None)
    if st.button("➕ New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.session_state.pop("conversations_cache", None)
        st.rerun()

    if "conversations_cache" not in st.session_state:
        st.session_state.conversations_cache = list_conversations() if health else []
    conversations = st.session_state.conversations_cache
    if not conversations:
        st.caption("No past conversations yet." if health else "Connect the backend to see history.")
    for conv in conversations:
        tid = conv["thread_id"]
        is_current = tid == st.session_state.thread_id
        row = st.columns([5, 1])
        label = ("▶ " if is_current else "") + (conv.get("title") or "(untitled)")
        if row[0].button(label, key=f"open_{tid}", use_container_width=True, help=f"{conv.get('turns', 0)} turn(s)"):
            try:
                st.session_state.messages = load_conversation(tid)
                st.session_state.thread_id = tid
                st.rerun()
            except Exception as exc:
                st.error(f"Could not load conversation: {exc}")
        if row[1].button("🗑", key=f"del_{tid}", help="Delete"):
            delete_conversation(tid)
            st.session_state.pop("conversations_cache", None)
            if st.session_state.thread_id == tid:
                st.session_state.messages = []
                st.session_state.thread_id = None
            st.rerun()

    st.divider()
    st.caption("Tech: LangGraph · LangChain · DeepSeek · ElasticSearch · Qdrant · FastAPI · Docker")
    st.caption(f"API: {API_URL}")


# --------------------------------------------------------------------------- tabs
overview_tab, chat_tab, retrieval_tab = st.tabs(
    ["📐 Overview & Architecture", "💬 Chat", "🔎 Retrieval inspector"]
)

with overview_tab:
    st.header("在日外国人智能助手")
    st.markdown(
        "Ask a question in **English or Japanese**. A LangGraph **supervisor** routes it to the "
        "right specialist (**tax / visa / ward_office**), which answers using deterministic domain "
        "tools and **cited** retrieval from a bilingual knowledge base. The ward-office agent can "
        "**hand off** to the visa/tax agents for cross-cutting procedures."
    )

    st.subheader("Architecture")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Hybrid retrieval (RAG)**")
        st.graphviz_chart(RETRIEVAL_DOT, use_container_width=True)
    with c2:
        st.markdown("**Multi-agent graph**")
        st.graphviz_chart(AGENT_DOT, use_container_width=True)

    st.subheader("Tech stack")
    st.table({"Concern": [c for c, _ in TECH_STACK], "Choice": [v for _, v in TECH_STACK]})

    st.subheader("Retrieval evaluation")
    st.caption("hybrid vs single-store baselines on the eval set (see docs/eval-report.md)")
    st.table(
        {
            "Method": [m for m, _, _ in EVAL_ROWS],
            "Recall@5": [r for _, r, _ in EVAL_ROWS],
            "MRR": [m for _, _, m in EVAL_ROWS],
        }
    )
    st.info(
        "On this small corpus dense retrieval already saturates rank-1, so hybrid does not beat it "
        "here; its advantage shows at scale and on rare-term / exact-match queries. Reported as-is.",
        icon="ℹ️",
    )

with chat_tab:
    st.header("💬 Chat with the assistant")
    if health is None:
        st.warning("Backend is unreachable — start it with `make up` / `make serve`.")
    st.caption("Try: *When is the tax filing deadline?* · *転入届はいつまでに出す必要がありますか？* · *How many years for permanent residency?*")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m.get("route"):
                st.caption(f"{DOMAIN_EMOJI.get(m['route'], '🤖')} routed to **{m['route']}**")
            st.markdown(m["content"])
            if m.get("citations"):
                with st.expander(f"Sources ({len(m['citations'])})"):
                    for cite in m["citations"]:
                        st.markdown(f"- {cite}")

    prompt = st.chat_input("Ask about tax, visa, or ward-office procedures…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            status_box = st.empty()
            answer_box = st.empty()
            answer = ""
            route = None
            tools_used: list[str] = []
            citations: list[str] = []

            def render_status():
                bits = []
                if route:
                    bits.append(f"{DOMAIN_EMOJI.get(route, '🤖')} routed to **{route}**")
                if tools_used:
                    bits.append("🔧 " + ", ".join(dict.fromkeys(tools_used)))
                if bits:
                    status_box.caption(" · ".join(bits))

            try:
                for event, data in stream_chat_events(prompt, st.session_state.thread_id):
                    if event == "route":
                        route = data.get("route")
                        render_status()
                    elif event == "tool":
                        tools_used.append(data.get("name", "tool"))
                        answer = ""  # text before a tool call was a preamble — reset
                        answer_box.empty()
                        render_status()
                    elif event == "token":
                        answer += data.get("text", "")
                        answer_box.markdown(answer + " ▌")
                    elif event == "error":
                        answer_box.error("The assistant stream failed. Is the stack up and the key set?")
                    elif event == "done":
                        st.session_state.thread_id = data.get("thread_id", st.session_state.thread_id)
                        citations = data.get("citations") or []
                answer_box.markdown(answer)
                if citations:
                    with st.expander(f"Sources ({len(citations)})"):
                        for cite in citations:
                            st.markdown(f"- {cite}")
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "route": route, "citations": citations}
                )
                st.session_state.pop("conversations_cache", None)  # new/updated convo shows in history
            except httpx.HTTPStatusError as exc:
                st.error(f"Backend returned {exc.response.status_code}. Is `DEEPSEEK_API_KEY` set and the stack ingested?")
            except Exception as exc:
                st.error(f"Could not reach the backend at {API_URL}: {exc}")

with retrieval_tab:
    st.header("🔎 Hybrid retrieval inspector")
    st.caption("Runs the hybrid pipeline (BM25 ∥ dense → RRF → rerank) — no LLM/API key needed.")
    c1, c2, c3 = st.columns([4, 2, 1])
    query = c1.text_input("Query", placeholder="ふるさと納税 / permanent residency / 転入届 …")
    domain_choice = c2.selectbox("Domain", ["(all)", "tax", "visa", "ward_office"])
    top_k = c3.number_input("Top K", min_value=1, max_value=10, value=5)
    if st.button("Search", type="primary") and query:
        domain = "" if domain_choice == "(all)" else domain_choice
        with st.spinner("Retrieving…"):
            try:
                data = get_search(query, domain, int(top_k))
                results = data.get("results", [])
                if not results:
                    st.info("No results. Have you run `make ingest`?")
                for r in results:
                    st.markdown(
                        f"**#{r['rank']}** · `{r.get('domain')}` · score **{r['score']}**  \n"
                        f"_{r['citation']}_"
                    )
                    st.caption(r["snippet"] + ("…" if len(r["snippet"]) >= 400 else ""))
                    st.divider()
            except httpx.HTTPStatusError as exc:
                st.error(f"Backend returned {exc.response.status_code}.")
            except Exception as exc:
                st.error(f"Could not reach the backend at {API_URL}: {exc}")
