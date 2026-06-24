from tools.visa_tools import (
    VISA_TOOLS,
    check_permanent_residency_eligibility,
    visa_renewal_checklist,
)


def test_pr_eligible_after_10_years():
    r = check_permanent_residency_eligibility(years_in_japan=10, years_on_work_visa=6)
    assert r["eligible"] is True


def test_pr_not_eligible_too_few_years():
    r = check_permanent_residency_eligibility(years_in_japan=3, years_on_work_visa=2)
    assert r["eligible"] is False
    assert r["years_short"] == 7


def test_pr_highly_skilled_fast_track():
    r = check_permanent_residency_eligibility(
        years_in_japan=2, years_on_work_visa=2, highly_skilled=True
    )
    assert r["eligible"] is True


def test_renewal_checklist_has_documents():
    r = visa_renewal_checklist()
    assert isinstance(r["documents"], list) and r["documents"]
    assert r["apply_window_months_before_expiry"] == 3


def test_visa_tools_exported():
    names = {t.name for t in VISA_TOOLS}
    assert names == {"check_permanent_residency_eligibility", "visa_renewal_checklist"}
