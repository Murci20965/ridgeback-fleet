"""The headline's rules. These need no database."""

from __future__ import annotations

from datetime import date

from dashboard import build_headline

KPIS = {"run_hours": 1052.73, "active_machines": 29, "fleet_size": 30, "impacts": 133}
BRANCHES = [{"branch": "Airport", "run_hours": 223.5}, {"branch": "Harbour", "run_hours": 301.4}]
DAILY = [
    {"event_date": date(2026, 9, 7), "impacts": 20},
    {"event_date": date(2026, 9, 8), "impacts": 33},
]


def test_week_view():
    assert build_headline(KPIS, BRANCHES, DAILY) == (
        "The fleet ran 1,052.7 hours across 29 of 30 machines. "
        "Harbour was busiest, and Tuesday had the most impacts."
    )


def test_day_view():
    kpis = {**KPIS, "run_hours": 197.3, "active_machines": 25, "impacts": 33}
    assert build_headline(kpis, BRANCHES, DAILY, day=date(2026, 9, 8)) == (
        "On Tue 8 Sep, the fleet ran 197.3 hours across 25 of 30 machines, with 33 impacts. "
        "Harbour was busiest."
    )


def test_filters_change_the_subject():
    assert build_headline(KPIS, BRANCHES, DAILY, machine_type="Forklift").startswith(
        "Forklifts ran"
    )
    assert build_headline(KPIS, [], DAILY, branch="Riverside", machine_type="PPT").startswith(
        "Riverside PPTs ran"
    )


def test_one_branch_doesnt_claim_to_be_busiest():
    headline = build_headline(KPIS, BRANCHES[:1], DAILY, branch="Airport")
    assert "busiest" not in headline
    assert headline.endswith("Tuesday had the most impacts.")


def test_tied_days_are_all_named():
    tied = [{**DAILY[0], "impacts": 33}, DAILY[1]]
    assert "Monday and Tuesday had the most impacts" in build_headline(KPIS, BRANCHES, tied)


def test_no_impacts_is_said_plainly():
    quiet = [{**row, "impacts": 0} for row in DAILY]
    assert "there were no impacts" in build_headline({**KPIS, "impacts": 0}, BRANCHES, quiet)
    day = build_headline({**KPIS, "impacts": 0}, BRANCHES, quiet, day=date(2026, 9, 7))
    assert "with no impacts." in day


def test_one_impact_is_singular():
    headline = build_headline({**KPIS, "impacts": 1}, BRANCHES, DAILY, day=date(2026, 9, 7))
    assert "with 1 impact." in headline


def test_no_activity():
    idle = {**KPIS, "run_hours": 0, "active_machines": 0}
    assert build_headline(idle, [], []) == "No machines ran this week."
    assert build_headline(idle, [], [], day=date(2026, 9, 13)) == "On Sun 13 Sep, no machines ran."


def test_a_single_machine_is_singular():
    kpis = {**KPIS, "fleet_size": 1, "active_machines": 1}
    assert "across 1 of 1 machine." in build_headline(kpis, BRANCHES, DAILY)
