import json
from pathlib import Path

DATASETS = Path(__file__).resolve().parent.parent / "eval" / "datasets"
KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"
DOMAINS = ("tax", "visa", "ward_office")


def _load(name: str) -> list[dict]:
    text = (DATASETS / name).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_each_domain_has_at_least_20_cases():
    for domain in DOMAINS:
        cases = _load(f"{domain}.jsonl")
        assert len(cases) >= 20, f"{domain} has only {len(cases)} cases"


def test_total_at_least_60_cases():
    total = sum(len(_load(f"{d}.jsonl")) for d in DOMAINS)
    assert total >= 60, total


def test_relevant_doc_ids_exist_on_disk():
    for domain in DOMAINS:
        for case in _load(f"{domain}.jsonl"):
            assert case.get("relevant"), case
            for doc_id in case["relevant"]:
                assert (KNOWLEDGE / doc_id).exists(), f"missing knowledge doc: {doc_id}"


def test_language_tags_are_valid():
    for domain in DOMAINS:
        for case in _load(f"{domain}.jsonl"):
            assert case.get("lang") in {"en", "ja", "mixed"}, case


def test_datasets_cover_required_query_types():
    types: set[str] = set()
    for domain in DOMAINS:
        for case in _load(f"{domain}.jsonl"):
            types.add(case.get("type", ""))
    # the suite must exercise more than plain keyword lookups
    for required in ("keyword", "semantic", "numeric", "cross", "confusing"):
        assert required in types, f"missing query type: {required}"
