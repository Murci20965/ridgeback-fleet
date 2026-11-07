"""The headline's rules. These need no database."""

from __future__ import annotations

from datetime import date

from dashboard import build_headline

BRANCHES = [{"branch": "Airport", "run_hours": 223.5}, {"branch": "Harbour", "run_hours": 301.4}]
DAILY = [
    {"event_date": date(2026, 9, 7), "impacts": 20},
    {"event_date": date(2026, 9, 8), "impacts": 33},
]
MACHINES = [
    {"ref_no": "R1", "run_hours": 12.5, "active": True},
    {"ref_no": "R2", "run_hours": 3.0, "active": True},
    {"ref_no": "R3", "run_hours": 0.0, "active": False},
]
TUESDAY = date(2026, 9, 8)


def test_week_view():
    assert build_headline(BRANCHES, DAILY, MACHINES) == (
        "Harbour was busiest, and Tuesday had the most impacts."
    )


def test_day_view():
    assert build_headline(BRANCHES, DAILY, MACHINES, day=TUESDAY) == "Harbour was busiest."


def test_one_branch_for_the_week_gives_the_peak_day():
    assert build_headline(BRANCHES[:1], DAILY, MACHINES, branch="Airport") == (
        "Tuesday had the most impacts."
    )


def test_one_branch_on_one_day_gives_the_top_machine():
    assert build_headline(BRANCHES[:1], DAILY, MACHINES, day=TUESDAY, branch="Airport") == (
        "R1 ran the most hours."
    )


def test_tied_days_are_all_named():
    tied = [{**DAILY[0], "impacts": 33}, DAILY[1]]
    assert build_headline(BRANCHES[:1], tied, MACHINES, branch="Airport") == (
        "Monday and Tuesday had the most impacts."
    )


def test_tied_machines_are_all_named():
    tied = [{**MACHINES[0]}, {**MACHINES[1], "run_hours": 12.5}]
    assert build_headline(BRANCHES, DAILY, tied, day=TUESDAY, branch="Airport") == (
        "R1 and R2 ran the most hours."
    )


def test_no_impacts_is_said_plainly():
    quiet = [{**row, "impacts": 0} for row in DAILY]
    assert build_headline(BRANCHES, quiet, MACHINES) == "Harbour was busiest, with no impacts."
    assert build_headline(BRANCHES, quiet, MACHINES, branch="Airport") == "R1 ran the most hours."


def test_no_activity():
    idle = [{**MACHINES[2]}]
    assert build_headline([], [], idle) == "No machines ran."
    assert build_headline([], [], idle, day=TUESDAY, branch="Airport") == "No machines ran."
