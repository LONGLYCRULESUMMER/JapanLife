from agents.specialists.tax import tax_tools
from agents.specialists.visa import visa_tools
from agents.specialists.ward_office import ward_office_tools


def test_tax_tools_include_knowledge_and_calculators():
    names = {t.name for t in tax_tools()}
    assert "search_knowledge_base" in names
    assert "estimate_income_tax" in names


def test_visa_tools_include_knowledge():
    names = {t.name for t in visa_tools()}
    assert "search_knowledge_base" in names
    assert "check_permanent_residency_eligibility" in names


def test_ward_office_tools_include_handoffs():
    names = {t.name for t in ward_office_tools()}
    assert "search_knowledge_base" in names
    assert "transfer_to_visa" in names
    assert "transfer_to_tax" in names
