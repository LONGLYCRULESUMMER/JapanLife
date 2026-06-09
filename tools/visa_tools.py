from __future__ import annotations

from langchain_core.tools import tool


def check_permanent_residency_eligibility(
    years_in_japan: int, years_on_work_visa: int, highly_skilled: bool = False
) -> dict:
    """Roughly check eligibility for Japanese permanent residency (永住).

    General rule: 10 continuous years in Japan, at least 5 on a work visa.
    Highly Skilled Professionals may qualify after 1-3 years.

    Args:
        years_in_japan: Total continuous years residing in Japan.
        years_on_work_visa: Years held on a work visa.
        highly_skilled: Whether the applicant holds Highly Skilled Professional status.

    Returns:
        dict with eligible (bool), reason, and years_short (0 if eligible).
    """
    if highly_skilled and years_in_japan >= 1:
        return {"eligible": True, "reason": "Highly Skilled Professional fast track (1-3 years).", "years_short": 0}

    meets_total = years_in_japan >= 10
    meets_work = years_on_work_visa >= 5
    if meets_total and meets_work:
        return {"eligible": True, "reason": "Meets the standard 10-year requirement.", "years_short": 0}

    years_short = max(10 - years_in_japan, 0)
    reason = "Needs 10 continuous years (>= 5 on a work visa)."
    if meets_total and not meets_work:
        reason = "Has 10 years total but fewer than 5 years on a work visa."
    return {"eligible": False, "reason": reason, "years_short": years_short}


def visa_renewal_checklist() -> dict:
    """Return the documents and timing for a residence-status renewal (在留期間更新).

    Returns:
        dict with documents (list), apply_window_months_before_expiry, and processing_time.
    """
    return {
        "documents": [
            "Application for extension of period of stay",
            "Passport and residence card (在留カード)",
            "ID photo (4cm x 3cm)",
            "Certificate of employment / enrollment",
            "Proof of tax payment (納税証明書)",
        ],
        "apply_window_months_before_expiry": 3,
        "processing_time": "2 weeks to 1 month",
        "note": "Apply at the Immigration Bureau (入管) before your current status expires.",
    }


VISA_TOOLS = [
    tool(check_permanent_residency_eligibility),
    tool(visa_renewal_checklist),
]
