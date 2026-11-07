"""Builds the single payload the dashboard renders."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import psycopg

import queries
from schemas import Dashboard


class DateOutsideData(ValueError):
    pass


def _day(value: date) -> str:
    return f"{value:%a} {value.day} {value:%b}"


def _delivery_day(file_name: str) -> str:
    """Events in a file are from the day before its delivery date."""
    delivery = datetime.strptime(file_name[:10], "%Y-%m-%d").date()
    return _day(date.fromordinal(delivery.toordinal() - 1))


def build_attention(
    exceptions: dict[str, list[dict[str, Any]]],
    inactive: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Turn the raw exceptions into a short list, most urgent first."""
    items: list[dict[str, str]] = []
    for file in exceptions["problem_files"]:
        if file["outcome"] == "failed":
            items.append(
                {
                    "severity": "critical",
                    "kind": "file_failed",
                    "title": f"{file['file_name']} didn't load",
                    "detail": file["error"] or "The pipeline couldn't read this file.",
                }
            )
        else:
            items.append(
                {
                    "severity": "warning",
                    "kind": "file_partial",
                    "title": f"The file for {_delivery_day(file['file_name'])} arrived cut off",
                    "detail": "Its last row is incomplete, so hours that day may read low.",
                }
            )
    for machine in exceptions["unknown_machines"]:
        items.append(
            {
                "severity": "critical",
                "kind": "unknown_machine",
                "title": f"{machine['ref_no']} isn't on the machine list",
                "detail": f"{machine['rows_held']} rows are held out of these figures.",
            }
        )
    for reset in exceptions["meter_resets"]:
        items.append(
            {
                "severity": "warning",
                "kind": "meter_reset",
                "title": f"{reset['ref_no']} meter reset on {_day(reset['event_date'])}",
                "detail": f"It reset {reset['reset_count']} times. Check the telematics unit.",
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
            }
        )
    for machine in inactive:
        items.append(
            {
                "severity": "warning",
                "kind": "inactive",
                "title": f"{machine['ref_no']} didn't run this week",
                "detail": f"{machine['machine_type']} assigned to {machine['assigned_branch']}.",
            }
        )
    return items


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
    return Dashboard(
        coverage=coverage,
        from_date=from_date,
        to_date=to_date,
        kpis=kpis,
        attention=build_attention(exceptions, inactive),
        machines=machines,
        drivers=drivers,
        branches=queries.get_branch_table(conn, from_date, to_date, **filters),
        daily_branch_hours=queries.get_daily_branch_hours(
            conn, coverage["week_start"], coverage["week_end"], **filters
        ),
        pipeline=queries.get_pipeline_status(conn),
    )
