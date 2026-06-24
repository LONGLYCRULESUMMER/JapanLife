from __future__ import annotations

from datetime import date

from langchain_core.tools import tool


def estimate_income_tax(
    annual_income: int, employment_type: str = "employee", deductions: str = ""
) -> dict:
    """Estimate Japanese income tax for a foreign resident (reference only, not professional advice).

    Args:
        annual_income: Annual gross income in JPY.
        employment_type: "employee" or "self_employed".
        deductions: Comma-separated extra deductions, e.g. "medical,life_insurance,spouse".

    Returns:
        dict with taxable_income, income_tax, reconstruction_tax, total_tax,
        effective_rate, and tax_bracket.
    """
    if employment_type == "employee":
        if annual_income <= 1_625_000:
            employment_deduction = 550_000
        elif annual_income <= 1_800_000:
            employment_deduction = int(annual_income * 0.4) - 100_000
        elif annual_income <= 3_600_000:
            employment_deduction = int(annual_income * 0.3) + 80_000
        elif annual_income <= 6_600_000:
            employment_deduction = int(annual_income * 0.2) + 440_000
        elif annual_income <= 8_500_000:
            employment_deduction = int(annual_income * 0.1) + 1_100_000
        else:
            employment_deduction = 1_950_000
    else:
        employment_deduction = 0

    basic_deduction = 480_000
    social_insurance = int(annual_income * 0.15) if employment_type == "employee" else 0

    extra = 0
    for d in (x.strip().lower() for x in deductions.split(",") if x.strip()):
        extra += {
            "medical": 100_000,
            "life_insurance": 120_000,
            "earthquake_insurance": 50_000,
            "spouse": 380_000,
            "dependent": 380_000,
        }.get(d, 0)

    taxable_income = max(
        annual_income - employment_deduction - basic_deduction - social_insurance - extra, 0
    )

    brackets = [
        (1_950_000, 0.05, 0),
        (3_300_000, 0.10, 97_500),
        (6_950_000, 0.20, 427_500),
        (9_000_000, 0.23, 636_000),
        (18_000_000, 0.33, 1_536_000),
        (40_000_000, 0.40, 2_796_000),
        (float("inf"), 0.45, 4_796_000),
    ]
    income_tax = 0
    bracket = "0%"
    for upper, rate, ded in brackets:
        if taxable_income <= upper:
            income_tax = int(taxable_income * rate - ded)
            bracket = f"{int(rate * 100)}%"
            break
    income_tax = max(income_tax, 0)
    reconstruction_tax = int(income_tax * 0.021)
    total_tax = income_tax + reconstruction_tax
    effective_rate = round(total_tax / annual_income * 100, 1) if annual_income > 0 else 0.0

    return {
        "annual_income": annual_income,
        "taxable_income": taxable_income,
        "income_tax": income_tax,
        "reconstruction_tax": reconstruction_tax,
        "total_tax": total_tax,
        "effective_rate": effective_rate,
        "tax_bracket": bracket,
        "note": "Estimate only. Consult a tax professional (税理士) for accuracy.",
    }


def calculate_furusato_nozei_limit(
    annual_income: int, family_status: str = "single", dependents: int = 0
) -> dict:
    """Estimate the Furusato Nozei (hometown tax) donation limit in JPY.

    Args:
        annual_income: Annual gross income in JPY.
        family_status: "single", "married", or "married_with_children".
        dependents: Number of tax dependents.

    Returns:
        dict with estimated_limit, self_payment (always 2000), and explanation.
    """
    if annual_income <= 0:
        return {"estimated_limit": 0, "self_payment": 2000, "explanation": "No income reported."}

    resident_tax = annual_income * 0.10
    special_portion = resident_tax * 0.20

    factor = 1.0
    if family_status == "married":
        factor -= 0.05
    elif family_status == "married_with_children":
        factor -= 0.10
    factor -= dependents * 0.03

    estimated_limit = max(int(special_portion * factor), 0)
    return {
        "estimated_limit": estimated_limit,
        "self_payment": 2000,
        "explanation": (
            f"Based on annual income ¥{annual_income:,}, the estimated Furusato Nozei limit "
            f"is about ¥{estimated_limit:,}. You pay ¥2,000 out of pocket; the rest is "
            f"deducted from your taxes. This is an estimate only."
        ),
    }


def get_tax_deadlines() -> dict:
    """Return upcoming Japanese tax deadlines relative to today.

    Returns:
        dict with current_date, tax_year, and a sorted list of deadlines
        (each with deadline, description, days_remaining, urgent).
    """
    today = date.today()
    year = today.year
    filing_start = date(year, 2, 16)
    filing_end = date(year, 3, 15)
    if today > filing_end:
        filing_start = date(year + 1, 2, 16)
        filing_end = date(year + 1, 3, 15)
        tax_year = year
    else:
        tax_year = year - 1

    raw = [
        (filing_end, f"Income tax filing deadline for {tax_year} (確定申告期限)"),
        (filing_start, f"Tax filing period opens for {tax_year}"),
        (date(year, 6, 30), f"First resident tax (住民税) installment for {year}"),
        (date(year, 12, 31), f"Furusato Nozei donation deadline for {year}"),
    ]
    deadlines = []
    for d, desc in raw:
        days = (d - today).days
        if days >= 0:
            deadlines.append(
                {"deadline": str(d), "description": desc, "days_remaining": days, "urgent": days <= 30}
            )
    deadlines.sort(key=lambda x: x["days_remaining"])
    return {"current_date": str(today), "tax_year": tax_year, "deadlines": deadlines}


TAX_TOOLS = [
    tool(estimate_income_tax),
    tool(calculate_furusato_nozei_limit),
    tool(get_tax_deadlines),
]
