"""Answer-level evaluation metrics for JapanLife.

These are deliberately small, dependency-free heuristics so the answer eval can
run offline (no LLM key, no services). ``citation_supported`` accepts a pluggable
``judge`` so a real LLM-based grader can be swapped in later via :class:`LLMJudge`.

Metrics:
- ``citation_present``      — did the answer carry at least one citation?
- ``citation_supported``    — is the answer text grounded in the retrieved context?
- ``refusal_or_disclaimer`` — does a high-risk answer include a disclaimer / "consult"?
- ``language_match``        — is the answer in the same language as the question?
- ``route_correct``         — did the supervisor route to the expected domain?
"""

from __future__ import annotations

import re
from typing import Iterable, Protocol, runtime_checkable

from core.i18n import detect_language

_WORD_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]")

# Very small English stop list — enough to stop trivial overlap from inflating scores.
_EN_STOP = {
    "the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "on", "for",
    "you", "your", "it", "be", "as", "at", "by", "with", "from", "this", "that",
    "can", "may", "do", "does", "if", "not", "no", "we", "they", "my", "will",
}

_DISCLAIMER_MARKERS = (
    # English (matched against a lower-cased answer)
    "not legal advice", "not tax advice", "not formal", "consult", "professional",
    "attorney", "lawyer", "official source", "immigration services agency",
    "national tax agency", "seek advice", "verify with", "demo knowledge",
    "is not advice", "should confirm", "may change",
    # Japanese (case-insensitive lower keeps these intact)
    "税理士", "行政書士", "専門家", "弁護士", "公式", "正式", "相談", "当局",
    "ご確認", "確認してください",
)

_DEFAULT_SUPPORT_THRESHOLD = 0.25


def _tokens(text: str) -> set[str]:
    """Bag of content tokens: ASCII words (>=2 chars, non-stop) + CJK char bigrams."""
    text = text or ""
    tokens: set[str] = set()
    for word in _WORD_RE.findall(text.lower()):
        if len(word) >= 2 and word not in _EN_STOP:
            tokens.add(word)
    cjk = "".join(_CJK_RE.findall(text))
    if len(cjk) == 1:
        tokens.add(cjk)
    for i in range(len(cjk) - 1):
        tokens.add(cjk[i : i + 2])
    return tokens


def support_score(answer: str, contexts: Iterable[str]) -> float:
    """Fraction of the answer's content tokens that also appear in the context."""
    answer_tokens = _tokens(answer)
    if not answer_tokens:
        return 0.0
    context_tokens: set[str] = set()
    for ctx in contexts or []:
        context_tokens |= _tokens(ctx)
    return len(answer_tokens & context_tokens) / len(answer_tokens)


@runtime_checkable
class SupportJudge(Protocol):
    """Interface for deciding whether an answer is supported by its context."""

    def is_supported(self, answer: str, contexts: list[str]) -> bool: ...


class HeuristicJudge:
    """Default offline judge: token-overlap >= threshold."""

    def __init__(self, threshold: float = _DEFAULT_SUPPORT_THRESHOLD):
        self.threshold = threshold

    def is_supported(self, answer: str, contexts: list[str]) -> bool:
        return support_score(answer, list(contexts)) >= self.threshold


class LLMJudge:
    """LLM-backed grounding judge (extension point; not used by default).

    ``llm`` is any callable ``(prompt: str) -> str`` — for example a thin wrapper
    around the chat model. The eval keeps using :class:`HeuristicJudge` unless an
    ``LLMJudge`` is explicitly passed, so nothing here requires an API key.
    """

    _PROMPT = (
        "You are grading whether an ANSWER is supported by the CONTEXT.\n"
        "Reply with only 'yes' or 'no'.\n\nCONTEXT:\n{ctx}\n\nANSWER:\n{ans}\n"
    )

    def __init__(self, llm):
        self._llm = llm

    def is_supported(self, answer: str, contexts: list[str]) -> bool:
        reply = self._llm(self._PROMPT.format(ctx="\n---\n".join(contexts), ans=answer))
        return "yes" in (reply or "").strip().lower()[:5]


def citation_present(citations: Iterable[str]) -> bool:
    """True if at least one non-empty citation line is present."""
    return any((c or "").strip() for c in (citations or []))


def citation_supported(
    answer: str, contexts: Iterable[str], judge: SupportJudge | None = None
) -> bool:
    """Whether the answer is grounded in the retrieved context."""
    judge = judge or HeuristicJudge()
    return judge.is_supported(answer, list(contexts or []))


def refusal_or_disclaimer(answer: str) -> bool:
    """True if the answer carries a disclaimer or advises consulting officials/pros."""
    lowered = (answer or "").lower()
    return any(marker in lowered for marker in _DISCLAIMER_MARKERS)


def language_match(question: str, answer: str) -> bool:
    """True if the answer's detected language matches the question's."""
    return detect_language(question) == detect_language(answer)


def route_correct(expected, actual: str | None) -> bool:
    """True if the actual route matches the expected route (str or collection)."""
    if actual is None:
        return False
    if isinstance(expected, (list, set, tuple)):
        return actual in set(expected)
    return expected == actual


def score_answer(case: dict, result: dict, judge: SupportJudge | None = None) -> dict:
    """Compute all answer-level metrics for one (case, result) pair.

    ``case``   : {"question", "expected_route", "expects_disclaimer", "lang"}
    ``result`` : {"answer", "citations", "contexts", "route"}
    """
    question = case.get("question", "")
    answer = result.get("answer", "")
    citations = result.get("citations") or []
    contexts = result.get("contexts") or []
    route = result.get("route")
    return {
        "citation_present": citation_present(citations),
        "citation_supported": citation_supported(answer, contexts, judge=judge),
        "refusal_or_disclaimer": refusal_or_disclaimer(answer),
        "language_match": language_match(question, answer),
        "route_correct": route_correct(case.get("expected_route"), route),
    }
