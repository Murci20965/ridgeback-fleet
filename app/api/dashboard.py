"""Builds the single payload the dashboard renders."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import psycopg

import queries
from schemas import Dashboard


class DateOutsideData(ValueError):
    pass


def _day(value: date) -> str:
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
    return _day(day) if day else None


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
        day = _day(reset["event_date"])
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
                    f"Seen {_day(move['first_date'])} to {_day(move['last_date'])}."
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


def format_hours(hours: float) -> str:
    """One decimal, rounding halves up, as the dashboard's tiles do.

    Python's format() can round 52.25 down to 52.2, which would disagree with the tile's 52.3.
    """
    rounded = Decimal(str(hours)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{rounded:,}"


def _join(names: list[str]) -> str:
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _subject(machine_type: str | None, branch: str | None) -> str:
    """What the headline is about, such as 'the fleet' or 'Riverside forklifts'."""
    kind = {"Forklift": "forklifts", "Reach Truck": "reach trucks", "PPT": "PPTs"}.get(
        machine_type or ""
    )
    if branch:
        return f"{branch} {kind}" if kind else branch
    return kind or "the fleet"


def build_headline(
    kpis: dict[str, Any],
    branches: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    day: date | None = None,
    machine_type: str | None = None,
    branch: str | None = None,
) -> str:
    """Summarise the view in plain words, using rules and no LLM, so it can't invent anything."""
    subject = _subject(machine_type, branch)
    prefix = f"On {_day(day)}, " if day else ""
    opening = f"{prefix}{subject}"
    opening = opening[0].upper() + opening[1:]

    if kpis["active_machines"] == 0:
        return f"On {_day(day)}, no machines ran." if day else "No machines ran this week."

    machines = "machine" if kpis["fleet_size"] == 1 else "machines"
    hours = f"{format_hours(kpis['run_hours'])} {'hour' if kpis['run_hours'] == 1 else 'hours'}"
    first = (
        f"{opening} ran {hours} across {kpis['active_machines']} of "
        f"{kpis['fleet_size']} {machines}."
    )

    busiest = None
    if not branch and branches:
        busiest = max(branches, key=lambda row: row["run_hours"])["branch"]

    if day:
        impacts = kpis["impacts"]
        count = "no impacts" if impacts == 0 else f"{impacts} impact{'s' if impacts != 1 else ''}"
        # The count belongs to the whole view, so it must not read as the busiest branch's.
        with_count = f"{first[:-1]}, with {count}."
        return f"{with_count} {busiest} was busiest." if busiest else with_count

    most = max((row["impacts"] for row in daily), default=0)
    if most == 0:
        impact_part = "there were no impacts"
    else:
        peaks = [f"{row['event_date']:%A}" for row in daily if row["impacts"] == most]
        impact_part = f"{_join(peaks)} had the most impacts"
    if busiest:
        return f"{first} {busiest} was busiest, and {impact_part}."
    return f"{first} {impact_part[0].upper()}{impact_part[1:]}."


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
        headline=build_headline(kpis, branches, daily, day, machine_type, branch),
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
