import eval.run_answer_eval as rae
from core.i18n import detect_language
from eval.run_answer_eval import StubAnswerer, load_answer_cases, run_answer_eval


def test_stub_answerer_shape_and_tax_routing():
    out = StubAnswerer()("When is the income tax filing deadline?")
    assert set(out) == {"answer", "citations", "contexts", "route"}
    assert out["route"] == "tax"
    assert out["citations"] and out["contexts"]


def test_stub_routes_visa_and_ward_office():
    stub = StubAnswerer()
    assert stub("How many years for permanent residency?")["route"] == "visa"
    assert stub("転入届はいつまでに区役所へ出しますか")["route"] == "ward_office"


def test_stub_answers_in_question_language():
    stub = StubAnswerer()
    assert detect_language(stub("確定申告はいつですか")["answer"]) == "ja"
    assert detect_language(stub("When is the deadline?")["answer"]) == "en"


def test_load_answer_cases_has_required_fields():
    cases = load_answer_cases()
    assert len(cases) >= 12
    for case in cases:
        assert "question" in case
        assert "expected_route" in case
        assert "expects_disclaimer" in case


def test_run_answer_eval_aggregates_rates():
    cases = [
        {"question": "q1", "expected_route": "tax", "expects_disclaimer": True, "lang": "en"},
        {"question": "q2", "expected_route": "visa", "expects_disclaimer": False, "lang": "en"},
    ]

    def fake(_question):
        return {
            "answer": "Please consult a professional. You can work 28 hours per week.",
            "citations": ["[1] x"],
            "contexts": ["work up to 28 hours per week"],
            "route": "tax",
        }

    report = run_answer_eval(cases, fake)
    assert report["n"] == 2
    agg = report["aggregate"]
    assert agg["citation_present"] == 1.0
    assert agg["route_correct"] == 0.5  # only the tax case matches
    assert agg["disclaimer_compliance"] == 1.0  # the one case that expects it has it


def test_stub_end_to_end_quality_is_well_behaved():
    report = run_answer_eval(load_answer_cases(), StubAnswerer())
    agg = report["aggregate"]
    assert agg["citation_present"] == 1.0
    assert agg["citation_supported"] == 1.0
    assert agg["language_match"] == 1.0
    assert agg["disclaimer_compliance"] == 1.0


def test_main_stub_runs_and_prints(capsys):
    rc = rae.main(["--stub", "--limit", "3"])
    assert rc == 0
    assert "Answer evaluation (stub)" in capsys.readouterr().out


def test_main_skips_gracefully_without_key(monkeypatch, capsys):
    monkeypatch.setattr(rae, "settings_has_key", lambda: False)
    rc = rae.main([])
    assert rc == 0
    assert "skipping answer eval" in capsys.readouterr().out
