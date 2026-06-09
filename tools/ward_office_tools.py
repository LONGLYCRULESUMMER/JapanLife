from __future__ import annotations

from datetime import date, timedelta

from langchain_core.tools import tool


def moving_in_checklist(from_within_japan: bool = True) -> dict:
    """Return documents and the deadline for the moving-in notification (転入届).

    Args:
        from_within_japan: True if moving from another Japanese municipality
            (requires a moving-out certificate), False if arriving from abroad.

    Returns:
        dict with documents (list), deadline_days (14), and triggers (downstream procedures).
    """
    documents = ["Residence card (在留カード)", "Personal seal (印鑑) if available"]
    if from_within_japan:
        documents.insert(1, "Moving-out certificate (転出証明書) from your previous city")
    return {
        "documents": documents,
        "deadline_days": 14,
        "triggers": [
            "National Health Insurance (国民健康保険) enrollment if not on employer insurance",
            "National Pension (国民年金)",
            "Resident tax (住民税) basis",
            "Update the address on your residence card (and notify Immigration)",
        ],
        "note": "Submit 転入届 at the ward/city office within 14 days of moving.",
    }


def days_until_move_in_deadline(move_in_date: str, today: str | None = None) -> dict:
    """Compute days remaining in the 14-day moving-in notification window.

    Args:
        move_in_date: Move-in date as 'YYYY-MM-DD'.
        today: Optional 'YYYY-MM-DD' for the reference date (defaults to the real today).

    Returns:
        dict with deadline (YYYY-MM-DD), days_remaining (int), and overdue (bool).
    """
    move = date.fromisoformat(move_in_date)
    now = date.fromisoformat(today) if today else date.today()
    deadline = move + timedelta(days=14)
    days_remaining = (deadline - now).days
    return {
        "move_in_date": move_in_date,
        "deadline": str(deadline),
        "days_remaining": days_remaining,
        "overdue": days_remaining < 0,
    }


WARD_OFFICE_TOOLS = [
    tool(moving_in_checklist),
    tool(days_until_move_in_deadline),
]
