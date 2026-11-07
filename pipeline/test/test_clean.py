"""Unit tests for each cleaning rule, plus a reconciliation over the real files."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pytest

from clean import (
    FileRejected,
    RowRejected,
    clean_file,
    delivery_date_from_name,
    make_event_key,
    map_columns,
    parse_branch,
    parse_driver,
    parse_timestamp,
    run_seconds_for_day,
    split_into_segments,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
INCOMING = REPO_ROOT / "data" / "incoming"
BRANCHES = {name.lower(): name for name in ("Airport", "Harbour", "Northgate", "Riverside")}
MACHINES = {"R1", "FBA2"}
HEADER = "DateAndTime,RefNo.,BranchName,TxFlagStrings,RunHours,DriverName,DriverSurname\n"
FILE_NAME = "2026-09-08_DailyTelemetryData.csv"
DELIVERY = date(2026, 9, 8)


def clean(body: str, header: str = HEADER):
    return clean_file(FILE_NAME, header + body, MACHINES, BRANCHES)


def reasons(result) -> list[str]:
    return [r.reason for r in result.rejections]


class TestDates:
    def test_delivery_date_comes_from_file_name(self):
        assert delivery_date_from_name(FILE_NAME) == DELIVERY

    def test_unexpected_file_name_rejects_the_file(self):
        with pytest.raises(FileRejected):
            delivery_date_from_name("telemetry.csv")

    def test_iso_timestamp(self):
        assert parse_timestamp("2026-09-07T06:02:30", DELIVERY) == datetime(2026, 9, 7, 6, 2, 30)

    def test_slash_format_is_day_first(self):
        parsed = parse_timestamp("10/09/2026 14:19:53", date(2026, 9, 11))
        assert parsed == datetime(2026, 9, 10, 14, 19, 53)

    def test_late_row_keeps_its_own_date(self):
        parsed = parse_timestamp("2026-09-07T21:21:24", date(2026, 9, 9))
        assert parsed.date() == date(2026, 9, 7)

    @pytest.mark.parametrize("value", ["2026-09-08T01:00:00", "2026-08-01T01:00:00"])
    def test_outside_delivery_window_is_rejected(self, value):
        with pytest.raises(RowRejected) as caught:
            parse_timestamp(value, DELIVERY)
        assert caught.value.reason == "timestamp_out_of_range"

    @pytest.mark.parametrize("value", ["", "yesterday", "2026-13-01T00:00:00"])
    def test_unreadable_timestamp_is_rejected(self, value):
        with pytest.raises(RowRejected) as caught:
            parse_timestamp(value, DELIVERY)
        assert caught.value.reason == "invalid_timestamp"


class TestNormalising:
    @pytest.mark.parametrize(
        "raw", ["Ridgeback Harbour", "RIDGEBACK HARBOUR", "Ridgeback  Harbour ", "Harbour"]
    )
    def test_branch_variants(self, raw):
        assert parse_branch(raw, BRANCHES) == "Harbour"

    def test_unknown_branch_is_rejected(self):
        with pytest.raises(RowRejected) as caught:
            parse_branch("Ridgeback Mars", BRANCHES)
        assert caught.value.reason == "unknown_branch"

    @pytest.mark.parametrize(
        ("name", "surname"), [("ASHWIN", "DANIELS"), ("Ashwin ", "Daniels"), ("ashwin", " daniels")]
    )
    def test_driver_variants_share_one_identity(self, name, surname):
        assert parse_driver(name, surname) == ("ashwin daniels", "Ashwin Daniels")

    def test_blank_driver_stays_blank(self):
        assert parse_driver(" ", "") == (None, None)

    def test_columns_are_mapped_by_name_in_any_order(self):
        header = [
            "Branch Name",
            "Ref No",
            "DateAndTime",
            "TxFlagStrings",
            "RunHours",
            "DriverName",
            "DriverSurname",
        ]
        mapping = map_columns(header)
        assert mapping["branch"] == 0
        assert mapping["ref_no"] == 1

    def test_missing_column_rejects_the_file(self):
        with pytest.raises(FileRejected, match="run_seconds"):
            map_columns(["DateAndTime", "RefNo.", "BranchName", "TxFlagStrings"])


class TestRows:
    GOOD = "2026-09-07T06:00:00,R1,Ridgeback Airport,Impact,100,Amahle,Radebe\n"

    def test_good_row_is_loaded(self):
        result = clean(self.GOOD)
        assert result.rejections == []
        event = result.events[0]
        assert (event.ref_no, event.reported_branch, event.event_type) == (
            "R1",
            "Airport",
            "Impact",
        )
        assert event.event_date == date(2026, 9, 7)
        assert event.source_line == 2

    def test_spaces_around_machine_are_trimmed(self):
        result = clean("2026-09-07T06:00:00, R1 ,Ridgeback Airport,Impact,100,A,B\n")
        assert result.events[0].ref_no == "R1"

    def test_reordered_columns_give_the_same_event(self):
        header = "Branch Name,Ref No,DateAndTime,TxFlagStrings,RunHours,DriverName,DriverSurname\n"
        moved = clean(
            "Ridgeback  Airport ,R1,2026-09-07T06:00:00,Impact,100,Amahle,Radebe\n", header
        )
        assert moved.events[0].event_key == clean(self.GOOD).events[0].event_key

    def test_blank_driver_on_impact_is_kept_without_a_driver(self):
        result = clean("2026-09-07T06:00:00,R1,Ridgeback Airport,Impact,100,,\n")
        assert result.events[0].driver_key is None

    @pytest.mark.parametrize(
        ("row", "reason"),
        [
            ("2026-09-07T06:00:00,Z9,Ridgeback Airport,Impact,100,A,B\n", "unknown_machine"),
            ("2026-09-07T06:00:00, ,Ridgeback Airport,Impact,100,A,B\n", "missing_machine"),
            ("2026-09-07T06:00:00,R1,Ridgeback Airport,Explosion,100,A,B\n", "unknown_event_type"),
            ("2026-09-07T06:00:00,R1,Ridgeback Airport,Impact,abc,A,B\n", "invalid_run_hours"),
            ("2026-09-07T06:00:00,R1,Ridgeback Airport,Impact,-5,A,B\n", "invalid_run_hours"),
            ("2026-09-07T06:00:00,R1,Ridgeback Mars,Impact,100,A,B\n", "unknown_branch"),
        ],
    )
    def test_bad_row_gets_its_reason(self, row, reason):
        result = clean(self.GOOD + row)
        assert reasons(result) == [reason]
        assert len(result.events) == 1

    def test_repeated_header_is_rejected(self):
        assert reasons(clean(self.GOOD + HEADER)) == ["repeated_header"]

    def test_truncated_row_is_rejected_and_flags_partial(self):
        result = clean(self.GOOD + "2026-09-07T13:07:22,R1,Ridgeback Harbo")
        assert reasons(result) == ["malformed_row"]
        assert result.is_partial

    def test_duplicate_in_file_is_rejected_once(self):
        result = clean(self.GOOD + self.GOOD)
        assert reasons(result) == ["duplicate_in_file"]
        assert len(result.events) == 1

    def test_event_key_ignores_which_file_it_came_from(self):
        when = datetime(2026, 9, 7, 6)
        assert make_event_key(when, "R1", "Impact", 1, None) == make_event_key(
            when, "R1", "Impact", 1, None
        )
        assert make_event_key(when, "R1", "Impact", 1, None) != make_event_key(
            when, "R1", "Impact", 2, None
        )


class TestWholeFiles:
    def test_empty_file_is_rejected(self):
        with pytest.raises(FileRejected):
            clean_file(FILE_NAME, "", MACHINES, BRANCHES)

    def test_file_with_no_usable_rows_is_rejected(self):
        with pytest.raises(FileRejected, match="usable"):
            clean("nonsense,R1,Ridgeback Airport,Impact,1,A,B\n")


class TestRunHours:
    def test_plain_day(self):
        assert split_into_segments([100, 200, 300]) == [[100, 200, 300]]
        assert run_seconds_for_day([100, 200, 300]) == 200

    def test_no_readings(self):
        assert split_into_segments([]) == []
        assert run_seconds_for_day([]) == 0

    def test_late_reading_is_not_a_reset(self):
        readings = [31280201, 31281508, 31280631, 31281508, 31282380]
        assert len(split_into_segments(readings)) == 1
        assert run_seconds_for_day(readings) == 31282380 - 31280201

    def test_reset_starts_a_new_segment(self):
        assert split_into_segments([19831467, 19831721, 2715, 4250]) == [
            [19831467, 19831721],
            [2715, 4250],
        ]

    def test_two_resets_in_a_day(self):
        readings = [19831000, 19831721, 2715, 23171, 3165, 6081]
        assert run_seconds_for_day(readings) == 721 + (23171 - 2715) + (6081 - 3165)

    def test_fall_of_exactly_the_threshold_is_not_a_reset(self):
        assert len(split_into_segments([5000, 1400])) == 1


class TestRealFiles:
    """The figures below come from a separate profile of the raw files."""

    @pytest.fixture
    def cleaned(self):
        with (REPO_ROOT / "data" / "machine_list.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        machines = {row["RefNo."].strip() for row in rows}
        branches = {row["BranchName"].strip().lower(): row["BranchName"].strip() for row in rows}
        return {
            path.name: clean_file(path.name, path.read_text(encoding="utf-8"), machines, branches)
            for path in sorted(INCOMING.glob("*.csv"))
        }

    def test_every_raw_row_is_accounted_for(self, cleaned):
        assert sum(r.total_rows for r in cleaned.values()) == 5176
        for result in cleaned.values():
            assert result.total_rows == len(result.events) + len(result.rejections)

    def test_rejection_reasons(self, cleaned):
        counts = Counter(reason for r in cleaned.values() for reason in reasons(r))
        assert counts == Counter(
            {
                "duplicate_in_file": 73,
                "unknown_machine": 21,
                "repeated_header": 1,
                "malformed_row": 1,
            }
        )

    def test_unique_events_across_files(self, cleaned):
        keys = {event.event_key for r in cleaned.values() for event in r.events}
        assert len(keys) == 5072

    def test_only_the_truncated_file_is_partial(self, cleaned):
        assert [name for name, r in cleaned.items() if r.is_partial] == [
            "2026-09-12_DailyTelemetryData.csv"
        ]

    def test_late_rows_keep_their_real_date(self, cleaned):
        dates = Counter(e.event_date for e in cleaned["2026-09-09_DailyTelemetryData.csv"].events)
        assert dates[date(2026, 9, 7)] == 11

    def test_impacts_after_deduplicating(self, cleaned):
        unique = {e.event_key: e for r in cleaned.values() for e in r.events}
        impacts = [e for e in unique.values() if e.event_type == "Impact"]
        assert len(impacts) == 133
        assert Counter(e.driver_name for e in impacts).most_common(1)[0] == ("Ashwin Daniels", 10)

    def test_top_forklift_on_tuesday(self, cleaned):
        unique = {e.event_key: e for r in cleaned.values() for e in r.events}
        forklifts = {e.ref_no for e in unique.values() if e.ref_no.startswith("FBA")}
        hours = {}
        for ref in forklifts:
            day = [
                e for e in unique.values() if e.ref_no == ref and e.event_date == date(2026, 9, 8)
            ]
            day.sort(key=lambda e: (e.occurred_at, e.run_seconds))
            hours[ref] = run_seconds_for_day(e.run_seconds for e in day) / 3600
        top = max(hours, key=hours.get)
        assert top == "FBA60251489088"
        assert round(hours[top], 2) == 12.05
