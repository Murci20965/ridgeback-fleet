"""All reporting queries. The dashboard and the chat tools both call these functions,
so a figure on screen and a figure in a chat answer always come from the same SQL.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import psycopg
from psycopg import sql

HOURS_GROUPS = {
    "machine": ("ref_no", "machine_type", "assigned_branch"),
    "branch": ("reported_branch",),
    "machine_type": ("machine_type",),
    "day": ("event_date",),
}
EVENT_GROUPS = {
    "driver": ("driver_name",),
    "machine": ("ref_no", "machine_type"),
    "branch": ("reported_branch",),
    "machine_type": ("machine_type",),
    "event_type": ("event_type",),
    "day": ("event_date",),
}

HARSH_EVENTS = ("Harsh Braking", "Harsh Acceleration", "Speeding")


def _plain(row: dict[str, Any]) -> dict[str, Any]:
    """Decimal isn't JSON-friendly, and these values are display figures."""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}


def _rows(conn: psycopg.Connection, query: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [_plain(row) for row in conn.execute(query, params).fetchall()]


def _like(text: str | None) -> str | None:
    """Turn a partial name into a safe ILIKE pattern, treating % and _ as literal."""
    if not text:
        return None
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def get_coverage(conn: psycopg.Connection) -> dict[str, Any] | None:
    """The dates the data covers, and the latest Monday-to-Sunday week."""
    row = conn.execute(
        """
        SELECT MIN(event_date) AS first_date, MAX(event_date) AS last_date,
               COUNT(DISTINCT event_date)::int AS days_with_data
        FROM telemetry_events
        """
    ).fetchone()
    if row["last_date"] is None:
        return None
    week_start = row["last_date"] - timedelta(days=row["last_date"].weekday())
    return {**row, "week_start": week_start, "week_end": week_start + timedelta(days=6)}


def find_machines(conn: psycopg.Connection, fragment: str) -> list[str]:
    """Machines whose reference contains the fragment, ignoring case."""
    rows = conn.execute(
        "SELECT ref_no FROM machines WHERE ref_no ILIKE %s ORDER BY ref_no", (_like(fragment),)
    ).fetchall()
    return [row["ref_no"] for row in rows]


def count_held_rows(conn: psycopg.Connection, fragment: str) -> int:
    """Rows held out because their machine, matching the fragment, isn't on the machine list."""
    return conn.execute(
        """
        SELECT COUNT(*)::int AS held
        FROM rejected_rows
        WHERE reason = 'unknown_machine' AND detail ILIKE %s
        """,
        (_like(fragment),),
    ).fetchone()["held"]


def get_run_hours(
    conn: psycopg.Connection,
    from_date: date,
    to_date: date,
    group_by: str,
    machine_type: str | None = None,
    branch: str | None = None,
    ref_no: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Run hours grouped one way, highest first. group_by comes from an allow-list."""
    columns = sql.SQL(", ").join(map(sql.Identifier, HOURS_GROUPS[group_by]))
    order = "event_date" if group_by == "day" else "run_seconds DESC, 1"
    query = sql.SQL(
        """
        SELECT {columns},
               SUM(run_seconds)::bigint AS run_seconds,
               ROUND(SUM(run_seconds) / 3600.0, 2) AS run_hours,
               COUNT(DISTINCT ref_no)::int AS machines,
               COUNT(DISTINCT event_date)::int AS days_active
        FROM v_machine_daily_hours
        WHERE event_date BETWEEN %(from_date)s AND %(to_date)s
          AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
          AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
          AND (%(ref_no)s::text IS NULL OR ref_no = %(ref_no)s)
        GROUP BY {columns}
        ORDER BY {order}
        LIMIT %(limit)s
        """
    ).format(columns=columns, order=sql.SQL(order))
    params = {
        "from_date": from_date,
        "to_date": to_date,
        "machine_type": machine_type,
        "branch": branch,
        "ref_no": ref_no,
        "limit": limit,
    }
    return _rows(conn, query, params)


def get_event_counts(
    conn: psycopg.Connection,
    from_date: date,
    to_date: date,
    group_by: str,
    event_types: list[str] | None = None,
    driver: str | None = None,
    machine_type: str | None = None,
    branch: str | None = None,
    ref_no: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Event counts grouped one way, highest first. Routine updates never appear.

    When grouped by driver, events with no driver logged on come back with a null
    driver_name, so callers can report them as unattributed.
    """
    columns = sql.SQL(", ").join(map(sql.Identifier, EVENT_GROUPS[group_by]))
    order = "event_date" if group_by == "day" else "events DESC, 1"
    query = sql.SQL(
        """
        SELECT {columns}, SUM(events)::int AS events
        FROM v_driver_events
        WHERE event_date BETWEEN %(from_date)s AND %(to_date)s
          AND (%(event_types)s::text[] IS NULL OR event_type = ANY(%(event_types)s))
          AND (%(driver)s::text IS NULL OR driver_name ILIKE %(driver)s)
          AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
          AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
          AND (%(ref_no)s::text IS NULL OR ref_no = %(ref_no)s)
        GROUP BY {columns}
        ORDER BY {order}
        LIMIT %(limit)s
        """
    ).format(columns=columns, order=sql.SQL(order))
    params = {
        "from_date": from_date,
        "to_date": to_date,
        "event_types": event_types,
        "driver": _like(driver),
        "machine_type": machine_type,
        "branch": branch,
        "ref_no": ref_no,
        "limit": limit,
    }
    return _rows(conn, query, params)


def get_fleet(
    conn: psycopg.Connection,
    from_date: date,
    to_date: date,
    machine_type: str | None = None,
    branch: str | None = None,
) -> list[dict[str, Any]]:
    """Every machine on the list, including those that never ran in the range.

    A machine matches a branch if it's assigned there or reported from there.
    """
    return _rows(
        conn,
        """
        WITH hours AS (
            SELECT ref_no, SUM(run_seconds) AS run_seconds,
                   ARRAY_AGG(DISTINCT reported_branch) AS reported_branches
            FROM v_machine_daily_hours
            WHERE event_date BETWEEN %(from_date)s AND %(to_date)s
              AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
            GROUP BY ref_no
        )
        SELECT m.ref_no, m.machine_type, b.name AS assigned_branch,
               ROUND(COALESCE(h.run_seconds, 0) / 3600.0, 2) AS run_hours,
               COALESCE(h.reported_branches, ARRAY[]::text[]) AS reported_branches,
               h.ref_no IS NOT NULL AS active
        FROM machines m
        JOIN branches b ON b.id = m.assigned_branch_id
        LEFT JOIN hours h ON h.ref_no = m.ref_no
        WHERE (%(machine_type)s::text IS NULL OR m.machine_type = %(machine_type)s)
          AND (%(branch)s::text IS NULL OR b.name = %(branch)s OR h.ref_no IS NOT NULL)
        ORDER BY run_hours DESC, m.ref_no
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "machine_type": machine_type,
            "branch": branch,
        },
    )


def get_driver_table(
    conn: psycopg.Connection,
    from_date: date,
    to_date: date,
    machine_type: str | None = None,
    branch: str | None = None,
) -> list[dict[str, Any]]:
    """One row per driver with safety events, worst first. Includes the unattributed row."""
    return _rows(
        conn,
        """
        SELECT driver_name,
               COALESCE(SUM(events) FILTER (WHERE event_type = 'Impact'), 0)::int AS impacts,
               COALESCE(SUM(events) FILTER (WHERE event_type = ANY(%(harsh)s)), 0)::int AS harsh,
               COALESCE(SUM(events) FILTER (WHERE category = 'idle'), 0)::int AS idle,
               COALESCE(SUM(events) FILTER (WHERE category = 'safety'), 0)::int AS safety_total
        FROM v_driver_events
        WHERE event_date BETWEEN %(from_date)s AND %(to_date)s
          AND category IN ('safety', 'idle')
          AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
          AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
        GROUP BY driver_name
        ORDER BY impacts DESC, safety_total DESC, driver_name NULLS LAST
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "machine_type": machine_type,
            "branch": branch,
            "harsh": list(HARSH_EVENTS),
        },
    )


def get_branch_table(
    conn: psycopg.Connection,
    from_date: date,
    to_date: date,
    machine_type: str | None = None,
    branch: str | None = None,
) -> list[dict[str, Any]]:
    """One row per branch: hours, active machines, impacts and harsh events."""
    return _rows(
        conn,
        """
        WITH hours AS (
            SELECT reported_branch AS branch, ROUND(SUM(run_seconds) / 3600.0, 2) AS run_hours,
                   COUNT(DISTINCT ref_no)::int AS active_machines
            FROM v_machine_daily_hours
            WHERE event_date BETWEEN %(from_date)s AND %(to_date)s
              AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
            GROUP BY reported_branch
        ),
        events AS (
            SELECT reported_branch AS branch,
                   COALESCE(SUM(events) FILTER (WHERE event_type = 'Impact'), 0)::int AS impacts,
                   COALESCE(SUM(events) FILTER (WHERE event_type = ANY(%(harsh)s)), 0)::int AS harsh
            FROM v_driver_events
            WHERE event_date BETWEEN %(from_date)s AND %(to_date)s
              AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
            GROUP BY reported_branch
        )
        SELECT h.branch, h.run_hours, h.active_machines,
               COALESCE(e.impacts, 0) AS impacts, COALESCE(e.harsh, 0) AS harsh
        FROM hours h
        LEFT JOIN events e USING (branch)
        WHERE %(branch)s::text IS NULL OR h.branch = %(branch)s
        ORDER BY h.run_hours DESC
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "machine_type": machine_type,
            "branch": branch,
            "harsh": list(HARSH_EVENTS),
        },
    )


def get_daily_summary(
    conn: psycopg.Connection,
    week_start: date,
    week_end: date,
    machine_type: str | None = None,
    branch: str | None = None,
) -> list[dict[str, Any]]:
    """One row per day with data: hours, active machines, impacts and harsh events."""
    return _rows(
        conn,
        """
        WITH hours AS (
            SELECT event_date, ROUND(SUM(run_seconds) / 3600.0, 2) AS run_hours,
                   COUNT(DISTINCT ref_no)::int AS active_machines
            FROM v_machine_daily_hours
            WHERE event_date BETWEEN %(week_start)s AND %(week_end)s
              AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
              AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
            GROUP BY event_date
        ),
        events AS (
            SELECT event_date,
                   COALESCE(SUM(events) FILTER (WHERE event_type = 'Impact'), 0)::int AS impacts,
                   COALESCE(
                       SUM(events) FILTER (WHERE event_type = ANY(%(harsh)s)), 0
                   )::int AS harsh_events
            FROM v_driver_events
            WHERE event_date BETWEEN %(week_start)s AND %(week_end)s
              AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
              AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
            GROUP BY event_date
        )
        SELECT h.event_date, h.run_hours, h.active_machines,
               COALESCE(e.impacts, 0) AS impacts, COALESCE(e.harsh_events, 0) AS harsh_events
        FROM hours h
        LEFT JOIN events e USING (event_date)
        ORDER BY h.event_date
        """,
        {
            "week_start": week_start,
            "week_end": week_end,
            "machine_type": machine_type,
            "branch": branch,
            "harsh": list(HARSH_EVENTS),
        },
    )


def get_daily_branch_hours(
    conn: psycopg.Connection,
    week_start: date,
    week_end: date,
    machine_type: str | None = None,
    branch: str | None = None,
) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT event_date, reported_branch AS branch,
               ROUND(SUM(run_seconds) / 3600.0, 2) AS run_hours
        FROM v_machine_daily_hours
        WHERE event_date BETWEEN %(week_start)s AND %(week_end)s
          AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
          AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
        GROUP BY event_date, reported_branch
        ORDER BY event_date, reported_branch
        """,
        {
            "week_start": week_start,
            "week_end": week_end,
            "machine_type": machine_type,
            "branch": branch,
        },
    )


def get_exceptions(
    conn: psycopg.Connection,
    from_date: date,
    to_date: date,
    machine_type: str | None = None,
    branch: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """The raw facts behind the 'needs attention' list and the chat's caveats.

    A held row isn't on the machine list, so its type is unknown and it's left out of
    machine type views. Its day comes from its file, and its branch from the raw row.
    """
    filters = {
        "from_date": from_date,
        "to_date": to_date,
        "machine_type": machine_type,
        "branch": branch,
    }
    machine_filter = """
        event_date BETWEEN %(from_date)s AND %(to_date)s
        AND (%(machine_type)s::text IS NULL OR machine_type = %(machine_type)s)
        AND (%(branch)s::text IS NULL OR reported_branch = %(branch)s)
    """
    return {
        "branch_moves": _rows(
            conn,
            f"""
            SELECT ref_no, assigned_branch, reported_branch, MIN(event_date) AS first_date,
                   MAX(event_date) AS last_date
            FROM v_machine_daily_hours
            WHERE reported_branch <> assigned_branch AND {machine_filter}
            GROUP BY ref_no, assigned_branch, reported_branch
            ORDER BY ref_no
            """,
            filters,
        ),
        "meter_resets": _rows(
            conn,
            f"""
            SELECT ref_no, event_date, reset_count
            FROM v_machine_daily_hours
            WHERE reset_count > 0 AND {machine_filter}
            ORDER BY event_date, ref_no
            """,
            filters,
        ),
        "unknown_machines": _rows(
            conn,
            """
            SELECT detail AS ref_no, COUNT(*)::int AS rows_held
            FROM rejected_rows
            WHERE reason = 'unknown_machine'
              AND LEFT(source_file, 10)::date - 1 BETWEEN %(from_date)s AND %(to_date)s
              AND (%(branch)s::text IS NULL OR raw ILIKE '%%' || %(branch)s || '%%')
              AND %(machine_type)s::text IS NULL
            GROUP BY detail
            ORDER BY detail
            """,
            filters,
        ),
        "problem_files": _rows(
            conn,
            """
            SELECT file_name, outcome, error
            FROM (
                SELECT DISTINCT ON (file_name) file_name, outcome, error
                FROM ingest_runs
                ORDER BY file_name, id DESC
            ) latest
            WHERE outcome <> 'success'
            ORDER BY file_name
            """,
            {},
        ),
    }


def get_latest_report(conn: psycopg.Connection) -> dict[str, Any] | None:
    """The newest weekly report, or None before the first one is published."""
    return conn.execute(
        """
        SELECT week_start, week_end, generated_at, facts, commentary,
               commentary_model AS model
        FROM weekly_reports
        ORDER BY week_start DESC
        LIMIT 1
        """
    ).fetchone()


def get_pipeline_status(conn: psycopg.Connection) -> dict[str, Any] | None:
    """Totals from the latest attempt on each file."""
    row = conn.execute(
        """
        SELECT MAX(finished_at) AS last_run_at,
               COUNT(*)::int AS files,
               COUNT(*) FILTER (WHERE outcome = 'failed')::int AS files_failed,
               COUNT(*) FILTER (WHERE outcome = 'partial')::int AS files_partial,
               COALESCE(SUM(rows_total), 0)::int AS rows_total,
               COALESCE(SUM(rows_loaded), 0)::int AS rows_loaded,
               COALESCE(SUM(rows_rejected), 0)::int AS rows_rejected,
               COALESCE(SUM(rows_duplicate), 0)::int AS rows_duplicate
        FROM (
            SELECT DISTINCT ON (file_name) *
            FROM ingest_runs
            ORDER BY file_name, id DESC
        ) latest
        """
    ).fetchone()
    return row if row["files"] else None
