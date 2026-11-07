"""Integration tests against a real Postgres. Set TEST_DATABASE_URL to run them.

The database named there is wiped, so never point this at anything you care about.
"""

from __future__ import annotations

import os
import shutil
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from clean import run_seconds_for_day
from run import ADVISORY_LOCK_ID, DEFAULT_INCOMING, DEFAULT_MACHINE_LIST, run

DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="TEST_DATABASE_URL is not set")
FIXTURES = Path(__file__).parent / "fixtures"
TUESDAY = date(2026, 9, 8)


def reset_database() -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


def query(sql: str, *params: object) -> list[tuple]:
    with psycopg.connect(DSN) as conn:
        return conn.execute(sql, params).fetchall()


def snapshot() -> dict[str, list[tuple]]:
    """Everything that must not change when a file is loaded again."""
    return {
        "events": query("SELECT * FROM telemetry_events ORDER BY event_key"),
        "rejected": query("SELECT * FROM rejected_rows ORDER BY source_file, line_no, reason"),
        "hours": query("SELECT * FROM v_machine_daily_hours ORDER BY event_date, ref_no"),
    }


@pytest.fixture(scope="module")
def loaded():
    reset_database()
    outcomes = run(DSN, DEFAULT_INCOMING, DEFAULT_MACHINE_LIST)
    return outcomes


class TestSevenFiles:
    def test_every_file_loads_in_date_order(self, loaded):
        names = [o.file_name for o in loaded]
        assert names == sorted(names)
        assert len(names) == 7
        assert {o.file_name: o.outcome for o in loaded}[
            "2026-09-12_DailyTelemetryData.csv"
        ] == "partial"
        assert [o.outcome for o in loaded].count("success") == 6

    def test_every_raw_row_reconciles(self, loaded):
        assert sum(o.rows_total for o in loaded) == 5176
        assert sum(o.rows_loaded for o in loaded) == 5072
        assert sum(o.rows_duplicate for o in loaded) == 81
        assert sum(o.rows_rejected for o in loaded) == 23
        assert query("SELECT COUNT(*) FROM telemetry_events") == [(5072,)]

    def test_rejections_are_stored_with_reasons(self, loaded):
        rows = dict(query("SELECT reason, COUNT(*) FROM rejected_rows GROUP BY reason"))
        assert rows == {
            "duplicate_in_file": 73,
            "duplicate_across_files": 8,
            "unknown_machine": 21,
            "repeated_header": 1,
            "malformed_row": 1,
        }

    def test_each_run_is_logged(self, loaded):
        rows = query(
            "SELECT file_name, outcome, rows_total, rows_loaded FROM ingest_runs ORDER BY id"
        )
        assert len(rows) == 7
        assert all(row[3] > 0 for row in rows)


class TestAnswers:
    def test_top_forklift_on_tuesday(self, loaded):
        assert query(
            """
            SELECT ref_no, run_hours FROM v_machine_daily_hours
            WHERE event_date = %s AND machine_type = 'Forklift'
            ORDER BY run_seconds DESC LIMIT 1
            """,
            TUESDAY,
        ) == [("FBA60251489088", Decimal("12.05"))]

    def test_top_driver_for_impacts(self, loaded):
        assert query(
            """
            SELECT driver_name, SUM(events)::int FROM v_driver_events
            WHERE event_type = 'Impact' AND driver_name IS NOT NULL
            GROUP BY driver_name ORDER BY 2 DESC, 1 LIMIT 1
            """
        ) == [("Ashwin Daniels", 10)]

    def test_fleet_totals(self, loaded):
        [(seconds, machines)] = query(
            "SELECT SUM(run_seconds), COUNT(DISTINCT ref_no) FROM v_machine_daily_hours"
        )
        assert round(float(seconds) / 3600, 1) == 1052.7
        assert machines == 29
        assert query(
            "SELECT SUM(events)::int FROM v_driver_events WHERE event_type = 'Impact'"
        ) == [(133,)]

    def test_routine_updates_are_not_events(self, loaded):
        assert query("SELECT COUNT(*) FROM v_driver_events WHERE event_type LIKE 'Unit%%'") == [
            (0,)
        ]

    def test_meter_resets_are_detected(self, loaded):
        assert query(
            """
            SELECT ref_no, event_date, reset_count FROM v_machine_daily_hours
            WHERE reset_count > 0
            """
        ) == [("FBA33639374813", TUESDAY, 2)]

    def test_moved_machine_keeps_both_branches(self, loaded):
        assert query(
            """
            SELECT DISTINCT assigned_branch, reported_branch FROM v_machine_daily_hours
            WHERE ref_no = 'R88897' ORDER BY 2
            """
        ) == [("Northgate", "Northgate"), ("Northgate", "Riverside")]

    def test_branch_view_matches_machine_view(self, loaded):
        assert query("SELECT ROUND(SUM(run_hours), 0) FROM v_branch_daily") == [(Decimal("1053"),)]

    def test_sql_hours_match_python_rule(self, loaded):
        readings = defaultdict(list)
        for ref, day, seconds in query(
            """
            SELECT ref_no, event_date, run_seconds FROM telemetry_events
            ORDER BY ref_no, event_date, occurred_at, run_seconds
            """
        ):
            readings[(ref, day)].append(seconds)
        expected = {key: run_seconds_for_day(values) for key, values in readings.items()}
        actual = {
            (ref, day): seconds
            for ref, day, seconds in query(
                "SELECT ref_no, event_date, run_seconds FROM v_machine_daily_hours"
            )
        }
        assert actual == expected


class TestReruns:
    def test_second_run_skips_everything(self, loaded):
        before = snapshot()
        runs_before = query("SELECT COUNT(*) FROM ingest_runs")
        assert run(DSN, DEFAULT_INCOMING, DEFAULT_MACHINE_LIST) == []
        assert snapshot() == before
        assert query("SELECT COUNT(*) FROM ingest_runs") == runs_before

    def test_forced_reload_gives_identical_data(self, loaded):
        before = snapshot()
        outcomes = run(DSN, DEFAULT_INCOMING, DEFAULT_MACHINE_LIST, force=True)
        assert len(outcomes) == 7
        assert snapshot() == before

    def test_second_run_is_skipped_while_one_is_in_progress(self, loaded):
        with psycopg.connect(DSN, autocommit=True) as holder:
            holder.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_ID,))
            assert run(DSN, DEFAULT_INCOMING, DEFAULT_MACHINE_LIST) is None
            holder.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))


class TestBadFiles:
    @pytest.fixture
    def incoming(self, tmp_path):
        reset_database()
        for name in ("2026-09-08", "2026-09-10"):
            file_name = f"{name}_DailyTelemetryData.csv"
            shutil.copy(DEFAULT_INCOMING / file_name, tmp_path / file_name)
        return tmp_path

    def outcomes_by_file(self, incoming):
        return {o.file_name: o for o in run(DSN, incoming, DEFAULT_MACHINE_LIST)}

    def test_missing_column_fails_only_that_file(self, incoming):
        bad = "2026-09-09_DailyTelemetryData.csv"
        shutil.copy(FIXTURES / "missing_column.csv", incoming / bad)
        outcomes = self.outcomes_by_file(incoming)
        assert outcomes[bad].outcome == "failed"
        assert "run_seconds" in outcomes[bad].error
        assert outcomes["2026-09-10_DailyTelemetryData.csv"].outcome == "success"
        assert query("SELECT COUNT(*) FROM telemetry_events WHERE source_file = %s", bad) == [(0,)]
        assert query("SELECT outcome FROM ingest_runs WHERE file_name = %s", bad) == [("failed",)]

    @pytest.mark.parametrize(
        ("content", "message"), [(b"", "empty"), (b"\xff\xfe\x00bad", "utf-8")]
    )
    def test_empty_or_corrupt_file_fails_only_that_file(self, incoming, content, message):
        bad = "2026-09-09_DailyTelemetryData.csv"
        (incoming / bad).write_bytes(content)
        outcomes = self.outcomes_by_file(incoming)
        assert outcomes[bad].outcome == "failed"
        assert message in outcomes[bad].error
        assert outcomes["2026-09-10_DailyTelemetryData.csv"].outcome == "success"

    def test_failed_file_is_retried_once_corrected(self, incoming):
        bad = "2026-09-09_DailyTelemetryData.csv"
        (incoming / bad).write_bytes(b"")
        self.outcomes_by_file(incoming)
        shutil.copy(DEFAULT_INCOMING / bad, incoming / bad)
        assert run(DSN, incoming, DEFAULT_MACHINE_LIST)[0].outcome == "success"

    def test_unexpected_file_name_is_logged_and_others_load(self, incoming):
        (incoming / "notes.csv").write_text("hello", encoding="utf-8")
        outcomes = self.outcomes_by_file(incoming)
        assert outcomes["notes.csv"].outcome == "failed"
        assert outcomes["2026-09-08_DailyTelemetryData.csv"].outcome == "success"
