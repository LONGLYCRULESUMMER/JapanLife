"""Answer-level evaluation harness for JapanLife.

Unlike ``run_eval.py`` (which scores *retrieval*), this scores the *answers* the
agent produces against :mod:`eval.answer_metrics`.

Run modes:
- ``--stub``  : fully offline. A deterministic ``StubAnswerer`` stands in for the
                LLM + retrieval stack so the harness (and CI) runs with no key and
                no services.
- default     : uses the real LangGraph agent + hybrid retriever. If no
                ``DEEPSEEK_API_KEY`` is configured it **skips gracefully** (exit 0)
                rather than failing.

Example:
    poetry run python -m eval.run_answer_eval --stub
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from core.i18n import detect_language
from eval.answer_metrics import score_answer

DATASETS = Path(__file__).resolve().parent / "datasets"
ANSWER_CASES = DATASETS / "answer_cases.jsonl"

_METRIC_KEYS = (
    "citation_present",
    "citation_supported",
    "refusal_or_disclaimer",
    "language_match",
    "route_correct",
)

# Minimal keyword router + canned facts for the offline stub answerer.
_ROUTE_KEYWORDS = {
    "tax": ("tax", "確定申告", "住民税", "ふるさと", "deduction", "控除", "freelancer",
            "e-tax", "etax", "年末調整", "青色申告", "income"),
    "visa": ("visa", "在留", "永住", "residence card", "在留カード", "dependent",
             "家族滞在", "status", "ビザ", "資格外活動", "permanent residency"),
    "ward_office": ("ward", "区役所", "転入", "転出", "住民票", "my number",
                    "マイナンバー", "insurance", "保険", "pension", "年金", "garbage",
                    "ごみ", "粗大", "seal", "印鑑"),
}

_STUB_FACTS = {
    ("tax", "en"): "In Japan the final income tax return (kakutei shinkoku) is filed from February 16 to March 15.",
    ("tax", "ja"): "日本の確定申告の期間は2月16日から3月15日までです。",
    ("visa", "en"): "Most residence statuses come with a residence card that you must carry, and renewals can be filed up to 3 months before expiry.",
    ("visa", "ja"): "多くの在留資格では在留カードを携帯する必要があり、更新は有効期限の3か月前から申請できます。",
    ("ward_office", "en"): "After moving you must file a moving-in notification at the ward office within 14 days.",
    ("ward_office", "ja"): "引っ越したら14日以内に区役所へ転入届を提出する必要があります。",
}

_STUB_DISCLAIMER = {
    "en": " Note: this is general demo information, not legal or tax advice; please verify with the official agency or a professional.",
    "ja": " なお、これは一般的なデモ情報であり、正式な手続きは公式の窓口や専門家にご確認ください。",
}


class StubAnswerer:
    """Deterministic offline stand-in for the agent.

    Routes by keyword and returns a localized, disclaimered answer that echoes a
    canned context snippet — enough to exercise every metric without an LLM or
    any running services.
    """

    def _route(self, question: str) -> str:
        q = question.lower()
        best, best_hits = "tax", 0
        for route, words in _ROUTE_KEYWORDS.items():
            hits = sum(1 for w in words if w in q)
            if hits > best_hits:
                best, best_hits = route, hits
        return best

    def __call__(self, question: str) -> dict:
        route = self._route(question)
        lang = "ja" if detect_language(question) == "ja" else "en"
        context = _STUB_FACTS[(route, lang)]
        answer = context + _STUB_DISCLAIMER[lang]
        return {
            "answer": answer,
            "citations": [f"[1] {route} knowledge base"],
            "contexts": [context],
            "route": route,
        }


def build_real_answerer():
    """Build an answerer backed by the real LangGraph agent + hybrid retriever."""
    from langchain_core.messages import HumanMessage

    from agents.graph import build_graph
    from agents.output import extract_citations, extract_reply
    from core.llm import get_llm
    from rag.retriever import get_default_retriever

    graph = build_graph(llm=get_llm())
    retriever = get_default_retriever()
    counter = {"n": 0}

    def answerer(question: str) -> dict:
        counter["n"] += 1
        state = {
            "messages": [HumanMessage(content=question)],
            "user_language": "",
            "active_domain": None,
            "citations": [],
        }
        try:
            result = graph.invoke(
                state,
                config={"configurable": {"thread_id": f"answer-eval-{counter['n']}"},
                        "recursion_limit": 50},
            )
            messages = result["messages"]
            answer = extract_reply(messages)
            citations = extract_citations(messages)
            route = result.get("active_domain")
        except Exception as exc:  # keep the eval running if one question fails
            answer, citations, route = f"[error: {exc}]", [], None
        contexts = []
        try:
            contexts = [chunk.text for chunk in retriever.search(question)[:5]]
        except Exception:
            contexts = []
        return {
            "answer": answer,
            "citations": citations,
            "contexts": contexts,
            "route": route,
        }

    return answerer


def load_answer_cases(path: Path = ANSWER_CASES) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def aggregate(rows: list[dict]) -> dict:
    """Aggregate per-case metrics into rates over the dataset."""
    n = len(rows) or 1
    agg = {key: sum(1 for r in rows if r["metrics"][key]) / n for key in _METRIC_KEYS}

    expected = [r for r in rows if r["case"].get("expects_disclaimer")]
    if expected:
        ok = sum(1 for r in expected if r["metrics"]["refusal_or_disclaimer"])
        agg["disclaimer_compliance"] = ok / len(expected)
    else:
        agg["disclaimer_compliance"] = 1.0
    return agg


def run_answer_eval(cases: list[dict], answerer, judge=None) -> dict:
    """Run the answerer over every case and score it. Pure/offline-friendly."""
    rows = []
    for case in cases:
        result = answerer(case["question"])
        metrics = score_answer(case, result, judge=judge)
        rows.append({"case": case, "result": result, "metrics": metrics})
    return {"n": len(rows), "rows": rows, "aggregate": aggregate(rows)}


def _print_report(report: dict, label: str) -> None:
    agg = report["aggregate"]
    print(f"=== Answer evaluation ({label}) — {report['n']} cases ===")
    for key in _METRIC_KEYS:
        print(f"  {key:<22} {agg[key]:.3f}")
    print(f"  {'disclaimer_compliance':<22} {agg['disclaimer_compliance']:.3f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer-level evaluation for JapanLife.")
    parser.add_argument("--stub", action="store_true",
                        help="Run fully offline with a deterministic stub answerer.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of cases.")
    args = parser.parse_args(argv)

    cases = load_answer_cases()
    if args.limit:
        cases = cases[: args.limit]

    if args.stub:
        answerer, label = StubAnswerer(), "stub"
    elif settings_has_key():
        answerer, label = build_real_answerer(), "real-agent"
    else:
        print("No DEEPSEEK_API_KEY set — skipping answer eval. "
              "Run with --stub for an offline demo.")
        return 0

    report = run_answer_eval(cases, answerer)
    _print_report(report, label)
    return 0


def settings_has_key() -> bool:
    from core.config import settings

    return bool(settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY"))


if __name__ == "__main__":
    raise SystemExit(main())
