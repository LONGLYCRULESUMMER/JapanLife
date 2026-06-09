import tools.knowledge_tool as kt
from tools.knowledge_tool import make_knowledge_search_tool


def test_knowledge_tool_passes_domain_and_formats(monkeypatch):
    captured = {}

    def fake_search(query, domain="", top_k=5):
        captured["query"] = query
        captured["domain"] = domain
        return {"context": "CTX", "citations": "[1] Doc | S1", "result_count": 1}

    monkeypatch.setattr(kt, "_search", fake_search)
    t = make_knowledge_search_tool("tax")
    assert t.name == "search_knowledge_base"
    out = t.invoke({"query": "確定申告"})
    assert "CTX" in out and "[1] Doc | S1" in out
    assert captured == {"query": "確定申告", "domain": "tax"}


def test_knowledge_tool_handles_empty(monkeypatch):
    monkeypatch.setattr(kt, "_search", lambda query, domain="", top_k=5: {"context": "No relevant information found in the knowledge base.", "citations": "", "result_count": 0})
    t = make_knowledge_search_tool("visa")
    out = t.invoke({"query": "x"})
    assert "No relevant information" in out
