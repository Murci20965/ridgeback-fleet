"""Turns tool results into a chart and a dashboard link for a chat answer.

Code builds these directly from the tool results and the LLM never touches them, so a chart
can't show an invented figure.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from dashboard import day_label

MAX_CHART_ROWS = 8

GROUP_LABELS = {
    "machine": ("ref_no", "machine"),
    "branch": ("reported_branch", "branch"),
    "machine_type": ("machine_type", "machine type"),
    "driver": ("driver_name", "driver"),
    "event_type": ("event_type", "event type"),
    "day": ("event_date", "day"),
}
MEASURES = {"get_run_hours": ("run_hours", "Run hours"), "get_event_counts": ("events", "Events")}


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _range_label(args: dict[str, Any]) -> str | None:
    start, end = _as_date(args.get("from_date")), _as_date(args.get("to_date"))
    if start is None or end is None:
        return None
    if start == end:
        return day_label(start)
    return f"{start.day} {start:%b} to {end.day} {end:%b}"


def _measure_name(tool: str, args: dict[str, Any]) -> str:
    event_types = args.get("event_types") or []
    if tool == "get_event_counts" and len(event_types) == 1:
        return f"{event_types[0]} events" if event_types[0] != "Impact" else "Impacts"
    return MEASURES[tool][1]


def chart_for(calls: list[dict[str, Any]]) -> dict[str, Any] | None:
    """A ranked bar chart of the latest tool result with at least 2 rows to compare."""
    for call in reversed(calls):
        tool, args, output = call["tool"], call["args"], call["output"]
        rows = output.get("rows") or []
        if tool not in MEASURES or output.get("error") or len(rows) < 2:
            continue
        label_key, group_name = GROUP_LABELS[args["group_by"]]
        value_key = MEASURES[tool][0]
        points = []
        for row in rows[:MAX_CHART_ROWS]:
            value = row[value_key]
            label = row[label_key]
            points.append(
                {
                    "label": day_label(label) if isinstance(label, date) else str(label),
                    "value": value,
                    "display": f"{value:.2f}" if value_key == "run_hours" else str(value),
                }
            )
        scope = _range_label(args)
        title = f"{_measure_name(tool, args)} by {group_name}"
        return {"title": f"{title}, {scope}" if scope else title, "points": points}
    return None


def dashboard_link_for(
    calls: list[dict[str, Any]], coverage: dict[str, Any] | None
) -> dict[str, str | None] | None:
    """The dashboard view matching the latest answer, if it has filters that can show it."""
    if coverage is None:
        return None
    for call in reversed(calls):
        tool, args, output = call["tool"], call["args"], call["output"]
        if tool not in {*MEASURES, "get_fleet"} or output.get("error"):
            continue
        # The dashboard has no machine or driver filter, so it couldn't show this answer.
        if args.get("ref_no") or args.get("driver"):
            return None
        start, end = _as_date(args.get("from_date")), _as_date(args.get("to_date"))
        is_whole_week = start == coverage["week_start"] and end == coverage["week_end"]
        if start is None or (start != end and not is_whole_week):
            return None

        branch = args.get("branch")
        rows = output.get("rows") or []
        if not branch and args.get("group_by") == "branch" and rows:
            branch = rows[0]["reported_branch"]
        day = start if start == end else None
        machine_type = args.get("machine_type")
        if not (day or branch or machine_type):
            return None

        parts = [branch, machine_type, day_label(day) if day else None]
        return {
            "label": f"Filter the dashboard: {', '.join(part for part in parts if part)}",
            "day": day.isoformat() if day else None,
            "branch": branch,
            "type": machine_type,
        }
    return None
