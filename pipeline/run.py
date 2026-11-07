"""Load the daily telemetry files into Postgres (Task 2).

Usage:
    python run.py                  # load files not yet loaded, oldest first
    python run.py --force          # reprocess every file; the data ends up identical

Each file is loaded in its own transaction, so a bad file is logged as failed and the
remaining files still load. Exits 1 if any file failed, so the scheduler shows it red.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import psycopg

from clean import CleanResult, FileRejected, Rejection, clean_file, delivery_date_from_name

REPO_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = Path(__file__).resolve().parent / "sql"
DEFAULT_INCOMING = REPO_ROOT / "data" / "incoming"
DEFAULT_MACHINE_LIST = REPO_ROOT / "data" / "machine_list.csv"

# Any constant works. It stops a manual run and the scheduled run overlapping.
ADVISORY_LOCK_ID = 7040213

log = logging.getLogger("pipeline")


@dataclass(frozen=True)
class FileOutcome:
    file_name: str
    outcome: str
    rows_total: int = 0
    rows_loaded: int = 0
    rows_rejected: int = 0
    rows_duplicate: int = 0
    error: str | None = None


def log_event(message: str, **fields: object) -> None:
    """Write one JSON line, so run logs are easy to read and to search."""
    log.info(json.dumps({"event": message, **fields}, default=str))


def apply_schema(conn: psycopg.Connection) -> None:
    for path in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(path.read_text(encoding="utf-8"))


def sync_machine_list(conn: psycopg.Connection, path: Path) -> tuple[set[str], dict[str, str]]:
    """Copy the machine list into the database, and return it for the cleaning rules."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            {key: value.strip() for key, value in row.items()} for row in csv.DictReader(handle)
        ]
    with conn.transaction():
        for branch in sorted({row["BranchName"] for row in rows}):
            conn.execute(
                "INSERT INTO branches (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (branch,)
            )
        for row in rows:
            conn.execute(
                """
                INSERT INTO machines (ref_no, machine_type, assigned_branch_id)
                VALUES (%s, %s, (SELECT id FROM branches WHERE name = %s))
                ON CONFLICT (ref_no) DO UPDATE
                SET machine_type = EXCLUDED.machine_type,
                    assigned_branch_id = EXCLUDED.assigned_branch_id
                """,
                (row["RefNo."], row["MachineType"], row["BranchName"]),
            )
    machines = {row["RefNo."] for row in rows}
    branches = {row["BranchName"].lower(): row["BranchName"] for row in rows}
    return machines, branches


def already_loaded(conn: psycopg.Connection, file_name: str, checksum: str) -> bool:
    """True if the latest attempt on this file loaded this exact content."""
    latest = conn.execute(
        "SELECT checksum, outcome FROM ingest_runs WHERE file_name = %s ORDER BY id DESC LIMIT 1",
        (file_name,),
    ).fetchone()
    return latest is not None and latest[0] == checksum and latest[1] != "failed"


def load_events(conn: psycopg.Connection, file_name: str, result: CleanResult) -> list[Rejection]:
    """Insert this file's events. Returns rows another file had already delivered."""
    branch_ids = dict(conn.execute("SELECT name, id FROM branches").fetchall())
    drivers = {e.driver_key: e.driver_name for e in result.events if e.driver_key}

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO drivers (driver_key, display_name) VALUES (%s, %s)
            ON CONFLICT (driver_key) DO NOTHING
            """,
            list(drivers.items()),
        )
    driver_ids = dict(conn.execute("SELECT driver_key, id FROM drivers").fetchall())

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO telemetry_events (
                event_key, occurred_at, ref_no, reported_branch_id, event_type,
                run_seconds, driver_id, source_file, source_line
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_key) DO NOTHING
            """,
            [
                (
                    e.event_key,
                    e.occurred_at,
                    e.ref_no,
                    branch_ids[e.reported_branch],
                    e.event_type,
                    e.run_seconds,
                    driver_ids.get(e.driver_key),
                    file_name,
                    e.source_line,
                )
                for e in result.events
            ],
        )

    owners = dict(
        conn.execute(
            "SELECT event_key, source_file FROM telemetry_events WHERE event_key = ANY(%s)",
            ([e.event_key for e in result.events],),
        ).fetchall()
    )
    return [
        Rejection(e.source_line, "duplicate_across_files", owners[e.event_key], e.event_key)
        for e in result.events
        if owners[e.event_key] != file_name
    ]


def process_file(
    conn: psycopg.Connection,
    path: Path,
    machines: set[str],
    branches: dict[str, str],
    force: bool,
) -> FileOutcome | None:
    """Load one file and log the attempt. Returns None if it was already loaded."""
    started_at = datetime.now(UTC)
    checksum = None
    try:
        content = path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        if not force and already_loaded(conn, path.name, checksum):
            log_event("file_skipped", file=path.name, reason="already loaded")
            return None
        result = clean_file(path.name, content.decode("utf-8-sig"), machines, branches)

        with conn.transaction():
            # Replacing the file's rows gives one code path for first loads and reloads.
            conn.execute("DELETE FROM rejected_rows WHERE source_file = %s", (path.name,))
            conn.execute("DELETE FROM telemetry_events WHERE source_file = %s", (path.name,))
            across_files = load_events(conn, path.name, result)
            rejections = [*result.rejections, *across_files]
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO rejected_rows (source_file, line_no, reason, detail, raw)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [(path.name, r.line_no, r.reason, r.detail, r.raw) for r in rejections],
                )
            duplicates = sum(r.reason.startswith("duplicate") for r in rejections)
            outcome = FileOutcome(
                file_name=path.name,
                outcome="partial" if result.is_partial else "success",
                rows_total=result.total_rows,
                rows_loaded=result.total_rows - len(rejections),
                rows_rejected=len(rejections) - duplicates,
                rows_duplicate=duplicates,
            )
            record_run(conn, outcome, checksum, started_at)
    except (OSError, UnicodeDecodeError, FileRejected, psycopg.Error, ValueError) as exc:
        outcome = FileOutcome(file_name=path.name, outcome="failed", error=str(exc))
        record_run(conn, outcome, checksum, started_at)
    log_event("file_processed", **outcome.__dict__)
    return outcome


def record_run(
    conn: psycopg.Connection, outcome: FileOutcome, checksum: str | None, started_at: datetime
) -> None:
    conn.execute(
        """
        INSERT INTO ingest_runs (
            file_name, checksum, started_at, outcome, rows_total,
            rows_loaded, rows_rejected, rows_duplicate, error
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            outcome.file_name,
            checksum,
            started_at,
            outcome.outcome,
            outcome.rows_total,
            outcome.rows_loaded,
            outcome.rows_rejected,
            outcome.rows_duplicate,
            outcome.error,
        ),
    )


def delivery_order(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Split paths into (valid names, oldest first) and names that can't be dated."""
    dated: list[tuple[date, Path]] = []
    invalid: list[Path] = []
    for path in paths:
        try:
            dated.append((delivery_date_from_name(path.name), path))
        except FileRejected:
            invalid.append(path)
    dated.sort(key=lambda item: item[0])
    return [path for _, path in dated], invalid


def missing_deliveries(paths: list[Path]) -> list[date]:
    """Dates with no file between the first and last delivery."""
    dates = sorted(delivery_date_from_name(path.name) for path in paths)
    if not dates:
        return []
    present = set(dates)
    span = (dates[-1] - dates[0]).days
    every_day = (dates[0] + timedelta(days=offset) for offset in range(span + 1))
    return [day for day in every_day if day not in present]


def run(
    dsn: str, incoming: Path, machine_list: Path, force: bool = False
) -> list[FileOutcome] | None:
    """Process every file. Returns the outcomes, or None if another run holds the lock."""
    with psycopg.connect(dsn, autocommit=True) as conn:
        locked = conn.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK_ID,)).fetchone()[0]
        if not locked:
            log_event("run_skipped", reason="another run is in progress")
            return None
        with conn.transaction():
            apply_schema(conn)
        machines, branches = sync_machine_list(conn, machine_list)

        paths, invalid = delivery_order(list(incoming.glob("*.csv")))
        gaps = missing_deliveries(paths)
        if gaps:
            log_event("deliveries_missing", dates=gaps)

        outcomes: list[FileOutcome] = []
        for path in invalid:
            outcome = FileOutcome(path.name, "failed", error="unexpected file name")
            record_run(conn, outcome, None, datetime.now(UTC))
            log_event("file_processed", **outcome.__dict__)
            outcomes.append(outcome)
        for path in paths:
            outcome = process_file(conn, path, machines, branches, force)
            if outcome:
                outcomes.append(outcome)
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description="Load daily telemetry files into Postgres.")
    parser.add_argument("--incoming", type=Path, default=DEFAULT_INCOMING)
    parser.add_argument("--machine-list", type=Path, default=DEFAULT_MACHINE_LIST)
    parser.add_argument("--force", action="store_true", help="reprocess files already loaded")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        log_event("run_failed", error="DATABASE_URL is not set")
        return 2

    outcomes = run(dsn, args.incoming, args.machine_list, args.force)
    if outcomes is None:
        return 0
    failed = [o.file_name for o in outcomes if o.outcome == "failed"]
    log_event("run_finished", processed=len(outcomes), failed=failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
