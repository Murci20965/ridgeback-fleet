"""Tests the agent loop and its guard with a scripted model, so they cost nothing."""

from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

import db
import main
from agent import UNVERIFIED_ANSWER, answer_question, unsupported_numbers
from dashboard import file_day_label
from llm import LLMError
from tools import run_tool, tool_definitions

TUESDAY = {"from_date": "2026-09-08", "to_date": "2026-09-08"}


class ScriptedLLM:
    """Replays a fixed list of replies and records what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, messages, tools):
        self.calls.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return {"message": reply, "model": "scripted", "usage": {"total_tokens": 10}}


def text(content):
    return {"role": "assistant", "content": content}


def call(name, **args):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "1",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ],
    }


def ask(llm, question="Which forklift ran the most hours on Tuesday?", history=()):
    with db.connect() as conn:
        return list(answer_question(conn, llm, question, list(history)))


class TestGuard:
    @pytest.mark.parametrize(
        "answer", ["It ran 12.05 hours.", "About 12.1 hours.", "About 12 hours."]
    )
    def test_supported_and_rounded_figures_pass(self, answer):
        assert unsupported_numbers(answer, [{"run_hours": 12.05}]) == []

    @pytest.mark.parametrize("answer", ["It ran 13 hours.", "It ran 12.5 hours."])
    def test_unsupported_figures_are_caught(self, answer):
        assert unsupported_numbers(answer, [{"run_hours": 12.05}]) != []

    def test_machine_references_are_not_figures(self):
        assert unsupported_numbers("P57083 and FBA60251489088 were idle.", [{}]) == []

    def test_thousands_separator(self):
        assert unsupported_numbers("That's 1,052.7 hours.", [{"run_hours": 1052.73}]) == []

    def test_spelled_out_figures_are_checked(self):
        assert unsupported_numbers("Five impacts had no driver.", [{"events": 5}]) == []
        assert unsupported_numbers("Seven impacts had no driver.", [{"events": 5}]) == ["Seven"]

    def test_dates_count_as_evidence(self):
        assert unsupported_numbers("On Tue 8 Sep.", [{"day": date(2026, 9, 8)}]) == []


class TestTools:
    def test_definitions_are_well_formed(self, database):
        names = {t["function"]["name"] for t in tool_definitions()}
        assert names == {"get_run_hours", "get_event_counts", "get_fleet", "get_data_coverage"}

    def test_top_forklift(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn,
                "get_run_hours",
                {**TUESDAY, "group_by": "machine", "machine_type": "Forklift"},
            )
        assert output["rows"][0]["ref_no"] == "FBA60251489088"
        assert output["rows"][0]["run_hours"] == 12.05

    def test_driver_ranking_reports_unattributed(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn,
                "get_event_counts",
                {
                    "from_date": "2026-09-07",
                    "to_date": "2026-09-13",
                    "group_by": "driver",
                    "event_types": ["Impact"],
                },
            )
        assert output["rows"][0] == {"driver_name": "Ashwin Daniels", "events": 10}
        assert output["events_with_no_driver_logged_on"] == 5

    def test_partial_driver_name_is_literal(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn,
                "get_event_counts",
                {
                    "from_date": "2026-09-07",
                    "to_date": "2026-09-13",
                    "group_by": "event_type",
                    "driver": "%",
                },
            )
        assert output["rows"] == []

    def test_partial_reference_finds_one_machine(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn, "get_run_hours", {**TUESDAY, "group_by": "machine", "ref_no": "4813"}
            )
        assert output["rows"][0]["ref_no"] == "FBA33639374813"

    def test_partial_reference_ignores_case_and_works_for_events(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn, "get_event_counts", {**TUESDAY, "group_by": "machine", "ref_no": "fba3363"}
            )
        assert output["rows"][0]["ref_no"] == "FBA33639374813"

    def test_several_matches_are_never_guessed(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn, "get_run_hours", {**TUESDAY, "group_by": "machine", "ref_no": "R8"}
            )
        assert output["error"] == "ambiguous_machine"
        assert set(output["matches"]) == {"R80275", "R88897"}
        assert "rows" not in output

    def test_no_match_is_reported(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn, "get_run_hours", {**TUESDAY, "group_by": "machine", "ref_no": "ZZZ"}
            )
        assert output["error"] == "unknown_machine"

    def test_percent_sign_is_not_a_wildcard(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn, "get_run_hours", {**TUESDAY, "group_by": "machine", "ref_no": "%"}
            )
        assert output["error"] == "unknown_machine"

    def test_range_outside_data_says_so(self, database):
        with db.connect() as conn:
            output = run_tool(
                conn,
                "get_run_hours",
                {"from_date": "2026-01-01", "to_date": "2026-01-31", "group_by": "machine"},
            )
        assert output["error"] == "outside_data"
        assert output["last_date"] == date(2026, 9, 13)

    @pytest.mark.parametrize(
        ("name", "args"),
        [
            ("get_run_hours", {"from_date": "bad", "to_date": "2026-09-08", "group_by": "machine"}),
            ("get_run_hours", {**TUESDAY, "group_by": "ref_no; DROP TABLE machines"}),
            ("get_event_counts", {**TUESDAY, "group_by": "driver", "event_types": ["Battery"]}),
            ("delete_everything", {}),
        ],
    )
    def test_bad_arguments_come_back_as_errors(self, database, name, args):
        with db.connect() as conn:
            assert "error" in run_tool(conn, name, args)


def test_file_with_a_bad_name_has_no_day():
    assert file_day_label("notes.csv") is None
    assert file_day_label("2026-09-12_DailyTelemetryData.csv") == "Fri 11 Sep"


class TestLoop:
    def test_answer_from_a_tool_result(self, database):
        llm = ScriptedLLM(
            call("get_run_hours", **TUESDAY, group_by="machine", machine_type="Forklift"),
            text("FBA60251489088 ran the most: 12.05 hours on Tue 8 Sep."),
        )
        events = ask(llm)
        assert [e["type"] for e in events] == ["status", "answer"]
        assert events[-1]["verified"] is True
        assert events[-1]["trace"][0]["tool"] == "get_run_hours"
        assert llm.calls[1][-1]["role"] == "tool"

    def test_made_up_figure_gets_one_retry_then_is_withheld(self, database):
        llm = ScriptedLLM(text("It ran 99.5 hours."), text("It ran 99.5 hours."))
        final = ask(llm)[-1]
        assert final["text"] == UNVERIFIED_ANSWER
        assert final["verified"] is False
        assert len(llm.calls) == 2

    def test_retry_can_recover(self, database):
        llm = ScriptedLLM(
            text("It ran 99.5 hours."),
            call("get_run_hours", **TUESDAY, group_by="machine", machine_type="Forklift"),
            text("FBA60251489088 ran 12.05 hours on Tue 8 Sep."),
        )
        assert ask(llm)[-1]["verified"] is True

    def test_decline_passes_without_tools(self, database):
        llm = ScriptedLLM(text("The data doesn't record battery level."))
        final = ask(llm, "What's the battery level on P10942?")[-1]
        assert final["verified"] is True
        assert "battery" in final["text"]

    def test_tool_loop_stops(self, database):
        llm = ScriptedLLM(*[call("get_data_coverage") for _ in range(10)])
        assert ask(llm)[-1]["type"] == "error"

    def test_invalid_json_arguments_are_handled(self, database):
        bad = call("get_run_hours")
        bad["tool_calls"][0]["function"]["arguments"] = "{not json"
        llm = ScriptedLLM(bad, text("Sorry, I couldn't get that."))
        events = ask(llm)
        assert events[-1]["type"] == "answer"
        assert events[-1]["trace"][0]["error"] == "invalid_arguments"

    def test_llm_failure_gives_a_friendly_error(self, database):
        llm = ScriptedLLM(LLMError("The assistant is busy. Try again in a minute.", "status 429"))
        assert ask(llm)[-1] == {
            "type": "error",
            "message": "The assistant is busy. Try again in a minute.",
        }


class TestRoute:
    def test_question_length_is_limited(self, database):
        client = TestClient(main.app)
        response = client.post("/api/v1/chat", json={"question": "x" * 501})
        assert response.status_code == 422

    def test_missing_key_gives_a_friendly_error(self, database, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        client = TestClient(main.app)
        response = client.post("/api/v1/chat", json={"question": "Hello"})
        assert response.status_code == 200
        event = json.loads(response.text.strip().splitlines()[-1])
        assert event["type"] == "error"
        assert "OPENROUTER" not in event["message"]

    def test_rate_limit(self, database, monkeypatch):
        monkeypatch.setattr(main, "limiter", main.RateLimiter(1, 60))
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        client = TestClient(main.app)
        assert client.post("/api/v1/chat", json={"question": "Hi"}).status_code == 200
        assert client.post("/api/v1/chat", json={"question": "Hi"}).status_code == 429
