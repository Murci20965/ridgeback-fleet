"""Builds the single payload the dashboard renders."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import psycopg

import queries
from schemas import Dashboard


class DateOutsideData(ValueError):
    pass


def day_label(value: date) -> str:
    return f"{value:%a} {value.day} {value:%b}"


def file_event_day(file_name: str) -> date | None:
    """Events in a file are from the day before its delivery date. Bad names give None."""
    try:
        delivery = datetime.strptime(file_name[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return delivery - timedelta(days=1)


def file_day_label(file_name: str) -> str | None:
    day = file_event_day(file_name)
    return day_label(day) if day else None


def _concerns_range(file_name: str, from_date: date, to_date: date) -> bool:
    """A file with no readable date could affect any day, so it's always shown."""
    day = file_event_day(file_name)
    return day is None or from_date <= day <= to_date


def build_attention(
    exceptions: dict[str, list[dict[str, Any]]],
    inactive: list[dict[str, Any]],
    from_date: date,
    to_date: date,
) -> list[dict[str, str]]:
    """Turn the raw exceptions into a short list, critical items first.

    Each item carries the question its Ask button sends to the chat.
    """
    files_question = "Which files have problems, and which dates does the data cover?"
    items: list[dict[str, str]] = []
    for file in exceptions["problem_files"]:
        if not _concerns_range(file["file_name"], from_date, to_date):
            continue
        if file["outcome"] == "failed":
            items.append(
                {
                    "severity": "critical",
                    "kind": "file_failed",
                    "title": f"{file['file_name']} didn't load",
                    "detail": file["error"] or "The pipeline couldn't read this file.",
                    "question": files_question,
                }
            )
        else:
            items.append(
                {
                    "severity": "warning",
                    "kind": "file_partial",
                    "title": f"The file for {file_day_label(file['file_name'])} arrived cut off",
                    "detail": "Its last row is incomplete, so hours that day may read low.",
                    "question": files_question,
                }
            )
    for machine in exceptions["unknown_machines"]:
        items.append(
            {
                "severity": "critical",
                "kind": "unknown_machine",
                "title": f"{machine['ref_no']} isn't on the machine list",
                "detail": f"{machine['rows_held']} rows are held out of these figures.",
                "question": f"Why are rows for {machine['ref_no']} held out of the figures?",
            }
        )
    for reset in exceptions["meter_resets"]:
        day = day_label(reset["event_date"])
        items.append(
            {
                "severity": "warning",
                "kind": "meter_reset",
                "title": f"{reset['ref_no']} meter reset on {day}",
                "detail": f"It reset {reset['reset_count']} times. Check the telematics unit.",
                "question": f"How many hours did {reset['ref_no']} run on {day}?",
            }
        )
    for move in exceptions["branch_moves"]:
        items.append(
            {
                "severity": "warning",
                "kind": "branch_move",
                "title": f"{move['ref_no']} is reporting from {move['reported_branch']}",
                "detail": (
                    f"It's assigned to {move['assigned_branch']}. "
                    f"Seen {day_label(move['first_date'])} to {day_label(move['last_date'])}."
                ),
                "question": (
                    f"How many hours did {move['ref_no']} run at "
                    f"{move['reported_branch']} this week?"
                ),
            }
        )
    for machine in inactive:
        items.append(
            {
                "severity": "warning",
                "kind": "inactive",
                "title": f"{machine['ref_no']} didn't run this week",
                "detail": f"{machine['machine_type']} assigned to {machine['assigned_branch']}.",
                "question": "Which machines didn't run this week?",
            }
        )
    # The sort is stable, so items keep their order within each severity.
    return sorted(items, key=lambda item: item["severity"] != "critical")


def _join(names: list[str]) -> str:
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def build_headline(
    branches: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    machines: list[dict[str, Any]],
    day: date | None = None,
    branch: str | None = None,
) -> str:
    """Say the one thing the KPI tiles don't: what stands out in this view.

    It uses rules and no LLM, so it can't invent anything. The dashboard shows the branch,
    machine type and dates in a label above it, so this sentence doesn't repeat them.
    """
    active = [row for row in machines if row["active"]]
    if not active:
        return "No machines ran."

    most_hours = max(row["run_hours"] for row in active)
    top_machines = [row["ref_no"] for row in active if row["run_hours"] == most_hours]
    top_machine = f"{_join(top_machines)} ran the most hours."

    most_impacts = max((row["impacts"] for row in daily), default=0)
    peak_days = [f"{row['event_date']:%A}" for row in daily if row["impacts"] == most_impacts]
    has_impacts = most_impacts > 0

    if branch:
        if day or not has_impacts:
            return top_machine
        return f"{_join(peak_days)} had the most impacts."

    busiest = max(branches, key=lambda row: row["run_hours"])["branch"]
    if day:
        return f"{busiest} was busiest."
    if not has_impacts:
        return f"{busiest} was busiest, with no impacts."
    return f"{busiest} was busiest, and {_join(peak_days)} had the most impacts."


def build_dashboard(
    conn: psycopg.Connection,
    day: date | None = None,
    machine_type: str | None = None,
    branch: str | None = None,
) -> Dashboard:
    coverage = queries.get_coverage(conn)
    if coverage is None:
        return Dashboard(coverage=None)
    if day and not coverage["first_date"] <= day <= coverage["last_date"]:
        raise DateOutsideData(
            f"Data covers {coverage['first_date']} to {coverage['last_date']}."
        )

    from_date = day or coverage["week_start"]
    to_date = day or coverage["week_end"]
    filters = {"machine_type": machine_type, "branch": branch}

    machines = queries.get_fleet(conn, from_date, to_date, **filters)
    drivers = queries.get_driver_table(conn, from_date, to_date, **filters)
    exceptions = queries.get_exceptions(conn, from_date, to_date, **filters)
    # A machine idle on one day is normal, so only a whole idle week is flagged.
    inactive = [] if day else [m for m in machines if not m["active"]]

    kpis = {
        "run_hours": round(sum(m["run_hours"] for m in machines), 2),
        "active_machines": sum(m["active"] for m in machines),
        "fleet_size": len(machines),
        "impacts": sum(d["impacts"] for d in drivers),
        "harsh_events": sum(d["harsh"] for d in drivers),
        "idle_events": sum(d["idle"] for d in drivers),
        "unattributed_impacts": sum(d["impacts"] for d in drivers if d["driver_name"] is None),
    }
    branches = queries.get_branch_table(conn, from_date, to_date, **filters)
    daily = queries.get_daily_summary(
        conn, coverage["week_start"], coverage["week_end"], **filters
    )
    return Dashboard(
        coverage=coverage,
        from_date=from_date,
        to_date=to_date,
        headline=build_headline(branches, daily, machines, day, branch),
        kpis=kpis,
        attention=build_attention(exceptions, inactive, from_date, to_date),
        machines=machines,
        drivers=drivers,
        branches=branches,
        daily=daily,
        daily_branch_hours=queries.get_daily_branch_hours(
            conn, coverage["week_start"], coverage["week_end"], **filters
        ),
        pipeline=queries.get_pipeline_status(conn),
    )
