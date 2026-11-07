from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

import db
import main

client = TestClient(main.app)


def get(**params):
    response = client.get("/api/v1/dashboard", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_week_view_matches_independent_figures(database):
    data = get()
    assert data["from_date"] == "2026-09-07"
    assert data["to_date"] == "2026-09-13"
    kpis = data["kpis"]
    assert round(kpis["run_hours"], 1) == 1052.7
    assert (kpis["active_machines"], kpis["fleet_size"]) == (29, 30)
    assert kpis["impacts"] == 133
    assert kpis["harsh_events"] == 598
    assert kpis["idle_events"] == 210
    assert kpis["unattributed_impacts"] == 5


def test_tuesday_top_forklift(database):
    top = get(day="2026-09-08", machine_type="Forklift")["machines"][0]
    assert (top["ref_no"], top["run_hours"]) == ("FBA60251489088", 12.05)


def test_top_driver_is_first_and_unattributed_is_kept(database):
    drivers = get()["drivers"]
    assert drivers[0]["driver_name"] == "Ashwin Daniels"
    assert drivers[0]["impacts"] == 10
    assert any(d["driver_name"] is None and d["impacts"] == 5 for d in drivers)


def test_attention_lists_each_exception(database):
    kinds = {item["kind"]: item["title"] for item in get()["attention"]}
    assert "P57083" in kinds["inactive"]
    assert "FBA37633406217" in kinds["unknown_machine"]
    assert "FBA33639374813" in kinds["meter_reset"]
    assert "R88897" in kinds["branch_move"]
    assert "Fri 11 Sep" in kinds["file_partial"]


def test_idle_machines_are_only_flagged_for_the_week(database):
    assert all(item["kind"] != "inactive" for item in get(day="2026-09-13")["attention"])


def test_branch_filter_narrows_figures(database):
    data = get(branch="Riverside")
    assert {b["branch"] for b in data["branches"]} == {"Riverside"}
    assert {d["branch"] for d in data["daily_branch_hours"]} == {"Riverside"}
    assert any(m["ref_no"] == "R88897" for m in data["machines"])


def test_branch_hours_add_up_to_the_fleet(database):
    data = get()
    assert sum(b["run_hours"] for b in data["branches"]) == pytest.approx(
        data["kpis"]["run_hours"], abs=0.5
    )


def test_pipeline_status_reconciles(database):
    pipeline = get()["pipeline"]
    assert pipeline["rows_total"] == 5176
    assert pipeline["rows_loaded"] == 5072
    assert pipeline["files_partial"] == 1


def test_date_outside_data_is_rejected(database):
    response = client.get("/api/v1/dashboard", params={"day": "2020-01-01"})
    assert response.status_code == 422


def test_unknown_filter_is_rejected(database):
    assert client.get("/api/v1/dashboard", params={"branch": "Mars"}).status_code == 422


def test_connection_is_read_only(database):
    with db.connect() as conn, pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conn.execute("DELETE FROM ingest_runs")


def kinds(**params):
    return [item["kind"] for item in get(**params)["attention"]]


def test_critical_items_come_first(database):
    severities = [item["severity"] for item in get()["attention"]]
    assert severities == sorted(severities, key=lambda severity: severity != "critical")
    assert severities[0] == "critical"


def test_every_attention_item_has_a_question(database):
    assert all(item["question"].endswith("?") for item in get()["attention"])


def test_cut_off_file_only_shows_for_its_own_day(database):
    assert "file_partial" in kinds(day="2026-09-11")
    assert "file_partial" not in kinds(day="2026-09-13")


def test_unknown_machine_follows_day_branch_and_type(database):
    assert "unknown_machine" in kinds(day="2026-09-13", branch="Airport")
    assert "unknown_machine" not in kinds(branch="Riverside")
    assert "unknown_machine" not in kinds(day="2026-09-07")
    assert "unknown_machine" not in kinds(machine_type="PPT")


def test_held_rows_are_counted_in_the_detail(database):
    item = next(i for i in get()["attention"] if i["kind"] == "unknown_machine")
    assert item["detail"].startswith("21 rows")


def test_headline_matches_independent_figures(database):
    assert get()["headline"] == "Harbour was busiest, and Tuesday had the most impacts."


def test_daily_summary_matches_independent_figures(database):
    daily = {row["event_date"]: row for row in get()["daily"]}
    assert len(daily) == 7
    assert daily["2026-09-08"]["run_hours"] == 197.3
    assert daily["2026-09-08"]["impacts"] == 33
    assert daily["2026-09-09"]["harsh_events"] == 127
    assert daily["2026-09-10"]["active_machines"] == 29
    assert sum(row["impacts"] for row in daily.values()) == 133
