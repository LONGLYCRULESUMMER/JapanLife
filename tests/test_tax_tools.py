from tools.tax_tools import (
    TAX_TOOLS,
    calculate_furusato_nozei_limit,
    estimate_income_tax,
    get_tax_deadlines,
)


def test_estimate_income_tax_known_value():
    r = estimate_income_tax(5_000_000, employment_type="employee")
    assert r["taxable_income"] == 2_330_000
    assert r["total_tax"] == 138_345
    assert r["tax_bracket"] == "10%"


def test_estimate_income_tax_zero_income():
    r = estimate_income_tax(0)
    assert r["taxable_income"] == 0
    assert r["total_tax"] == 0


def test_furusato_limit_scales_with_income():
    low = calculate_furusato_nozei_limit(3_000_000)["estimated_limit"]
    high = calculate_furusato_nozei_limit(8_000_000)["estimated_limit"]
    assert high > low > 0


def test_tax_deadlines_structure():
    d = get_tax_deadlines()
    assert "deadlines" in d and isinstance(d["deadlines"], list)
    assert all("days_remaining" in x for x in d["deadlines"])


def test_tax_tools_exported_as_langchain_tools():
    names = {t.name for t in TAX_TOOLS}
    assert names == {"estimate_income_tax", "calculate_furusato_nozei_limit", "get_tax_deadlines"}
