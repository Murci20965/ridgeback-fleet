"""Charts and dashboard links come from tool results alone, so these need no database or model."""

from __future__ import annotations

from datetime import date

from presentation import chart_for, dashboard_link_for

COVERAGE = {"week_start": date(2026, 9, 7), "week_end": date(2026, 9, 13)}
WEEK = {"from_date": "2026-09-07", "to_date": "2026-09-13"}
TUESDAY = {"from_date": "2026-09-08", "to_date": "2026-09-08"}


def hours_call(args, rows):
    return {"tool": "get_run_hours", "args": args, "output": {"rows": rows}}


MACHINES = [{"ref_no": "A1", "run_hours": 12.05}, {"ref_no": "B2", "run_hours": 11.3}]


class TestChart:
    def test_builds_from_tool_rows(self):
        chart = chart_for([hours_call({**TUESDAY, "group_by": "machine"}, MACHINES)])
        assert chart["title"] == "Run hours by machine, Tue 8 Sep"
        assert chart["points"][0] == {"label": "A1", "value": 12.05, "display": "12.05"}

    def test_one_row_gets_no_chart(self):
        assert chart_for([hours_call({**TUESDAY, "group_by": "machine"}, MACHINES[:1])]) is None

    def test_a_tool_error_gets_no_chart(self):
        call = {"tool": "get_run_hours", "args": TUESDAY, "output": {"error": "outside_data"}}
        assert chart_for([call]) is None

    def test_the_latest_comparable_result_is_used(self):
        older = hours_call({**TUESDAY, "group_by": "machine"}, MACHINES)
        newer = {
            "tool": "get_event_counts",
            "args": {**WEEK, "group_by": "driver", "event_types": ["Impact"]},
            "output": {
                "rows": [
                    {"driver_name": "Ashwin Daniels", "events": 10},
                    {"driver_name": "Mpho Molefe", "events": 7},
                ]
            },
        }
        chart = chart_for([older, newer])
        assert chart["title"] == "Impacts by driver, 7 Sep to 13 Sep"
        assert chart["points"][1]["display"] == "7"

    def test_days_get_readable_labels(self):
        rows = [
            {"event_date": date(2026, 9, 7), "run_hours": 197.1},
            {"event_date": date(2026, 9, 8), "run_hours": 197.3},
        ]
        chart = chart_for([hours_call({**WEEK, "group_by": "day"}, rows)])
        assert chart["points"][0]["label"] == "Mon 7 Sep"

    def test_long_results_are_capped(self):
        rows = [{"ref_no": f"M{i}", "run_hours": float(i)} for i in range(20)]
        chart = chart_for([hours_call({**WEEK, "group_by": "machine"}, rows)])
        assert len(chart["points"]) == 8


class TestDashboardLink:
    def test_day_and_type_become_filters(self):
        call = hours_call({**TUESDAY, "group_by": "machine", "machine_type": "Forklift"}, MACHINES)
        link = dashboard_link_for([call], COVERAGE)
        assert link == {
            "label": "Filter the dashboard: Forklift, Tue 8 Sep",
            "day": "2026-09-08",
            "branch": None,
            "type": "Forklift",
        }

    def test_the_busiest_branch_is_offered(self):
        rows = [{"reported_branch": "Harbour", "run_hours": 301.4}]
        link = dashboard_link_for([hours_call({**WEEK, "group_by": "branch"}, rows)], COVERAGE)
        assert link["branch"] == "Harbour"
        assert link["day"] is None

    def test_the_whole_fleet_week_needs_no_link(self):
        call = hours_call({**WEEK, "group_by": "machine"}, MACHINES)
        assert dashboard_link_for([call], COVERAGE) is None

    def test_a_range_the_dashboard_cannot_show_gets_no_link(self):
        args = {"from_date": "2026-09-08", "to_date": "2026-09-09", "branch": "Harbour"}
        assert dashboard_link_for([hours_call({**args, "group_by": "day"}, [])], COVERAGE) is None

    def test_a_machine_question_gets_no_link(self):
        call = hours_call({**TUESDAY, "group_by": "machine", "ref_no": "A1"}, MACHINES)
        assert dashboard_link_for([call], COVERAGE) is None

    def test_a_tool_error_gets_no_link(self):
        call = {"tool": "get_run_hours", "args": TUESDAY, "output": {"error": "outside_data"}}
        assert dashboard_link_for([call], COVERAGE) is None
