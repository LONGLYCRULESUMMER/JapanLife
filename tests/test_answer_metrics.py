from eval.answer_metrics import (
    HeuristicJudge,
    citation_present,
    citation_supported,
    language_match,
    refusal_or_disclaimer,
    route_correct,
    score_answer,
    support_score,
)


def test_citation_present_true_false():
    assert citation_present(["[1] Doc | S1"]) is True
    assert citation_present([]) is False
    assert citation_present(["", "   "]) is False


def test_support_score_high_when_answer_echoes_context():
    ans = "The filing period is February 16 to March 15."
    ctx = ["Filing period: February 16 to March 15 of the following year."]
    assert support_score(ans, ctx) > 0.6


def test_support_score_zero_for_empty_answer():
    assert support_score("", ["anything"]) == 0.0


def test_citation_supported_true_when_grounded():
    ans = "You can work up to 28 hours per week with permission."
    ctx = ["With permission you may work up to 28 hours per week."]
    assert citation_supported(ans, ctx) is True


def test_citation_supported_false_when_unrelated():
    ans = "The capital of France is Paris and the Eiffel tower is very tall."
    ctx = ["Resident tax is roughly 10 percent of last year's taxable income."]
    assert citation_supported(ans, ctx) is False


def test_citation_supported_japanese_grounded():
    ans = "確定申告の期間は2月16日から3月15日までです。"
    ctx = ["確定申告の期間は2月16日から3月15日までです。"]
    assert citation_supported(ans, ctx) is True


def test_refusal_or_disclaimer_english():
    assert refusal_or_disclaimer("Note: this is not legal advice; consult a professional.") is True
    assert refusal_or_disclaimer("The filing deadline is March 15.") is False


def test_refusal_or_disclaimer_japanese():
    assert refusal_or_disclaimer("正式な手続きは専門家にご相談ください。") is True


def test_language_match():
    assert language_match("When is the deadline?", "The deadline is March 15.") is True
    assert language_match("締め切りはいつですか", "確定申告は3月15日までです") is True
    assert language_match("When is the deadline?", "確定申告は3月15日までです") is False


def test_route_correct_handles_str_collection_and_none():
    assert route_correct("tax", "tax") is True
    assert route_correct("tax", "visa") is False
    assert route_correct("tax", None) is False
    assert route_correct(["tax", "ward_office"], "ward_office") is True


def test_heuristic_judge_threshold():
    judge = HeuristicJudge(threshold=0.3)
    assert judge.is_supported("28 hours per week", ["work up to 28 hours per week"]) is True
    assert judge.is_supported("completely different unrelated tokens", ["abc def ghi"]) is False


def test_score_answer_aggregates_all_metrics():
    case = {
        "question": "How many hours can a student work part-time?",
        "expected_route": "visa",
        "expects_disclaimer": False,
        "lang": "en",
    }
    result = {
        "answer": "A student can work up to 28 hours per week with permission.",
        "citations": ["[1] Student and Work Visa Basics | Part-Time Work"],
        "contexts": ["With permission you may work up to 28 hours per week."],
        "route": "visa",
    }
    metrics = score_answer(case, result)
    assert metrics["citation_present"] is True
    assert metrics["citation_supported"] is True
    assert metrics["language_match"] is True
    assert metrics["route_correct"] is True
    assert isinstance(metrics["refusal_or_disclaimer"], bool)
