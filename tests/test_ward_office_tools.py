from tools.ward_office_tools import (
    WARD_OFFICE_TOOLS,
    days_until_move_in_deadline,
    moving_in_checklist,
)


def test_checklist_from_within_japan_requires_transfer_cert():
    r = moving_in_checklist(from_within_japan=True)
    assert any("転出証明書" in d for d in r["documents"])
    assert r["deadline_days"] == 14


def test_checklist_from_abroad_no_transfer_cert():
    r = moving_in_checklist(from_within_japan=False)
    assert not any("転出証明書" in d for d in r["documents"])


def test_days_until_deadline_counts_from_move_date():
    r = days_until_move_in_deadline("2025-01-01", today="2025-01-05")
    assert r["deadline"] == "2025-01-15"
    assert r["days_remaining"] == 10
    assert r["overdue"] is False


def test_days_until_deadline_overdue():
    r = days_until_move_in_deadline("2025-01-01", today="2025-01-20")
    assert r["overdue"] is True


def test_ward_office_tools_exported():
    names = {t.name for t in WARD_OFFICE_TOOLS}
    assert names == {"moving_in_checklist", "days_until_move_in_deadline"}


def test_days_until_deadline_invalid_date_returns_error():
    r = days_until_move_in_deadline("not-a-date")
    assert "error" in r
