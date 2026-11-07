"""The chat's tools. The model can only ask for these typed queries and can't write SQL,
so it can't touch anything else or invent a column. Pydantic validates every argument.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import psycopg
from pydantic import BaseModel, Field, ValidationError

import queries
from dashboard import file_day_label
from schemas import Branch, MachineType

EventType = Literal[
    "Power Up",
    "Driver Change",
    "Impact",
    "Harsh Braking",
    "Harsh Acceleration",
    "Speeding",
    "Excess Idle",
]
MAX_ROWS = 50
MAX_MATCHES = 10

NOT_RECORDED = [
    "battery or charge level",
    "location or GPS position",
    "load or weight carried",
    "maintenance or service history",
    "cost, fuel or energy use",
    "speed values (only that a speeding event happened)",
    "shift rosters or driver employment details",
    "hours per driver (shift-change rows overlap, so this can't be attributed reliably)",
]


class RunHoursArgs(BaseModel):
    """Run hours (motor running time) over a date range, highest first."""

    from_date: date
    to_date: date
    group_by: Literal["machine", "branch", "machine_type", "day"]
    machine_type: MachineType | None = None
    branch: Branch | None = None
    ref_no: str | None = Field(None, description="A full or partial machine reference number.")
    limit: int = Field(10, ge=1, le=MAX_ROWS)


class EventCountsArgs(BaseModel):
    """Counts of events over a date range, highest first. Routine updates aren't events."""

    from_date: date
    to_date: date
    group_by: Literal["driver", "machine", "branch", "machine_type", "event_type", "day"]
    event_types: list[EventType] | None = Field(None, description="Leave out for all events.")
    driver: str | None = Field(None, description="A driver's full or partial name.")
    machine_type: MachineType | None = None
    branch: Branch | None = None
    ref_no: str | None = Field(None, description="A full or partial machine reference number.")
    limit: int = Field(10, ge=1, le=MAX_ROWS)


class FleetArgs(BaseModel):
    """Every machine on the list with its type, branch and hours, including machines that
    never ran. Use this for how many machines exist or which machines were idle."""

    from_date: date
    to_date: date
    machine_type: MachineType | None = None
    branch: Branch | None = None


class DataCoverageArgs(BaseModel):
    """The dates the data covers, known data problems, and what the data doesn't record."""


def _outside_data(coverage: dict[str, Any] | None, from_date: date, to_date: date) -> dict | None:
    if coverage is None:
        return {"error": "no_data", "message": "No data has been loaded yet."}
    if to_date < coverage["first_date"] or from_date > coverage["last_date"]:
        return {
            "error": "outside_data",
            "message": "That range has no data.",
            "first_date": coverage["first_date"],
            "last_date": coverage["last_date"],
        }
    return None


def _resolve_machine(
    conn: psycopg.Connection, ref_no: str | None
) -> tuple[str | None, dict[str, Any] | None]:
    """Turn a partial reference into one machine, or an error for the model to relay.

    Several matches are never guessed between, because that could show the wrong machine.
    """
    if ref_no is None:
        return None, None
    matches = queries.find_machines(conn, ref_no)
    if len(matches) == 1:
        return matches[0], None
    if not matches:
        return None, {
            "error": "unknown_machine",
            "message": f"No machine on the list matches {ref_no}.",
        }
    return None, {
        "error": "ambiguous_machine",
        "message": f"{len(matches)} machines match {ref_no}. Ask which one is meant.",
        "matches": matches[:MAX_MATCHES],
        "total_matches": len(matches),
    }


def _run_hours(conn: psycopg.Connection, args: RunHoursArgs) -> dict[str, Any]:
    outside = _outside_data(queries.get_coverage(conn), args.from_date, args.to_date)
    if outside:
        return outside
    ref_no, problem = _resolve_machine(conn, args.ref_no)
    if problem:
        return problem
    args = args.model_copy(update={"ref_no": ref_no})
    rows = queries.get_run_hours(conn, **args.model_dump(exclude={"limit"}))
    return {"rows": rows[: args.limit], "total_groups": len(rows)}


def _event_counts(conn: psycopg.Connection, args: EventCountsArgs) -> dict[str, Any]:
    outside = _outside_data(queries.get_coverage(conn), args.from_date, args.to_date)
    if outside:
        return outside
    ref_no, problem = _resolve_machine(conn, args.ref_no)
    if problem:
        return problem
    args = args.model_copy(update={"ref_no": ref_no})
    rows = queries.get_event_counts(conn, **args.model_dump(exclude={"limit"}))
    result: dict[str, Any] = {}
    if args.group_by == "driver":
        unattributed = sum(r["events"] for r in rows if r["driver_name"] is None)
        rows = [r for r in rows if r["driver_name"] is not None]
        result["events_with_no_driver_logged_on"] = unattributed
    return {**result, "rows": rows[: args.limit], "total_groups": len(rows)}


def _fleet(conn: psycopg.Connection, args: FleetArgs) -> dict[str, Any]:
    outside = _outside_data(queries.get_coverage(conn), args.from_date, args.to_date)
    if outside:
        return outside
    rows = queries.get_fleet(conn, **args.model_dump())
    return {
        "machines": rows,
        "total": len(rows),
        "active": sum(r["active"] for r in rows),
    }


def _data_coverage(conn: psycopg.Connection, _: DataCoverageArgs) -> dict[str, Any]:
    coverage = queries.get_coverage(conn)
    if coverage is None:
        return {"error": "no_data", "message": "No data has been loaded yet."}
    exceptions = queries.get_exceptions(conn, coverage["first_date"], coverage["last_date"])
    return {
        **coverage,
        "not_recorded": NOT_RECORDED,
        "known_problems": {
            **exceptions,
            "problem_files": [
                {**f, "events_date": file_day_label(f["file_name"])}
                for f in exceptions["problem_files"]
            ],
        },
        "pipeline": queries.get_pipeline_status(conn),
    }


TOOLS = {
    "get_run_hours": (RunHoursArgs, _run_hours),
    "get_event_counts": (EventCountsArgs, _event_counts),
    "get_fleet": (FleetArgs, _fleet),
    "get_data_coverage": (DataCoverageArgs, _data_coverage),
}


def tool_definitions() -> list[dict[str, Any]]:
    """The tool list in the format OpenRouter expects."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": (model.__doc__ or "").strip(),
                "parameters": model.model_json_schema(),
            },
        }
        for name, (model, _) in TOOLS.items()
    ]


def run_tool(conn: psycopg.Connection, name: str, raw_args: dict[str, Any]) -> dict[str, Any]:
    """Validate and run one tool. Mistakes go back to the model as data, so it can correct them."""
    if name not in TOOLS:
        return {"error": "unknown_tool", "message": f"There's no tool called {name}."}
    model, handler = TOOLS[name]
    try:
        args = model.model_validate(raw_args)
    except ValidationError as exc:
        details = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
        return {"error": "invalid_arguments", "message": "; ".join(details)}
    return handler(conn, args)
