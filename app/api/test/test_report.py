"""Tests the weekly report with a scripted model, so they cost nothing."""

from __future__ import annotations

import json

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

import db
import main
from agent import unknown_references
from dashboard import build_dashboard
from llm import LLMError
from report import (
    build_facts,
    crowded_points,
    facts_checksum,
    has_several_sentences,
    problems_in,
    publish_report,
    write_commentary,
)
from schemas import Commentary

FACTS = {
    "kpis": {"run_hours": 1052.7, "impacts": 133},
    "top_machines": [{"ref_no": "FBA60251489088", "run_hours": 40.5}],
}
GOOD = {
    "summary": "The fleet ran 1052.7 hours with 133 impacts.",
    "highlights": ["FBA60251489088 ran 40.5 hours."],
    "checks": ["Review the impacts."],
}


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, messages, tools, tool_choice="auto"):
        self.calls.append({"messages": list(messages), "tool_choice": tool_choice})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return {"message": reply, "model": "scripted", "usage": {}}


def written(content):
    arguments = content if isinstance(content, str) else json.dumps(content)
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "1",
                "type": "function",
                "function": {"name": "write_report", "arguments": arguments},
            }
        ],
    }


class TestCommentary:
    def test_verified_commentary_is_returned(self):
        commentary, model = write_commentary(ScriptedLLM(written(GOOD)), FACTS)
        assert commentary.summary == GOOD["summary"]
        assert model == "scripted"

    def test_the_tool_call_is_forced(self):
        llm = ScriptedLLM(written(GOOD))
        write_commentary(llm, FACTS)
        assert llm.calls[0]["tool_choice"]["function"]["name"] == "write_report"

    def test_an_invented_figure_gets_a_retry(self):
        bad = {**GOOD, "summary": "The fleet ran 1200 hours."}
        llm = ScriptedLLM(written(bad), written(GOOD))
        commentary, _ = write_commentary(llm, FACTS)
        assert commentary.summary == GOOD["summary"]
        assert "1200" in llm.calls[1]["messages"][-1]["content"]

    def test_commentary_that_never_passes_is_dropped(self):
        bad = written({**GOOD, "summary": "The fleet ran 1200 hours."})
        assert write_commentary(ScriptedLLM(bad, bad, bad), FACTS) == (None, None)

    def test_an_invented_machine_is_caught(self):
        commentary = Commentary(**{**GOOD, "highlights": ["FBA11111111111 stood out."]})
        assert problems_in(commentary, FACTS) == ["FBA11111111111"]

    def test_invalid_output_gets_a_retry(self):
        llm = ScriptedLLM(written("not json"), written(GOOD))
        commentary, _ = write_commentary(llm, FACTS)
        assert commentary is not None

    def test_a_reply_without_the_tool_gets_a_retry(self):
        llm = ScriptedLLM({"role": "assistant", "content": "Here you go"}, written(GOOD))
        commentary, _ = write_commentary(llm, FACTS)
        assert commentary is not None
        assert llm.calls[1]["messages"][-1]["role"] == "user"

    def test_a_model_failure_gives_no_commentary(self):
        llm = ScriptedLLM(LLMError("busy"))
        assert write_commentary(llm, FACTS) == (None, None)


class TestOneItemPerPoint:
    # The check the live report actually produced on 8 Nov 2026.
    JOINED = (
        "Check P57083, which didn't run this week, and confirm whether it is still in use. "
        "Fri 11 Sep's file was cut off, so hours that day may read low."
    )

    def test_two_sentences_are_caught(self):
        assert has_several_sentences(self.JOINED)

    @pytest.mark.parametrize(
        "point",
        [
            "Review the impacts.",
            "Review the impacts",
            "FBA33639374813 logged the most run hours (61.06).",
            "Harbour recorded 301.4 run hours, the most of any branch.",
            "Fri 11 Sep's file was cut off, so hours that day may read low.",
            "Tue 8 Sep had the most impacts, with 33.",
            "  Check R88897's assigned branch.  ",
        ],
    )
    def test_one_sentence_passes(self, point):
        assert not has_several_sentences(point)

    def test_a_question_then_a_sentence_is_caught(self):
        assert has_several_sentences("Is P57083 still in use? It didn't run this week.")

    def test_crowded_points_lists_only_the_joined_ones(self):
        commentary = Commentary(**{**GOOD, "checks": ["Review the impacts.", self.JOINED]})
        assert crowded_points(commentary) == [self.JOINED]

    def test_a_crowded_point_gets_a_retry(self):
        crowded = {**GOOD, "checks": [self.JOINED]}
        llm = ScriptedLLM(written(crowded), written(GOOD))
        commentary, _ = write_commentary(llm, FACTS)
        assert commentary.checks == GOOD["checks"]
        assert "one sentence about one item" in llm.calls[1]["messages"][-1]["content"]


class TestReferences:
    def test_known_references_pass(self):
        assert unknown_references("P57083 stopped.", [{"ref_no": "P57083"}]) == []

    def test_unknown_references_are_caught(self):
        assert unknown_references("P99999 stopped.", [{"ref_no": "P57083"}]) == ["P99999"]

    def test_ordinary_text_is_not_a_reference(self):
        assert unknown_references("In Q4 the SAST time was 04:00.", [{}]) == []


class TestChecksum:
    def test_the_last_run_time_does_not_change_it(self):
        one = {"kpis": {"impacts": 1}, "pipeline": {"files": 7, "last_run_at": "a"}}
        two = {"kpis": {"impacts": 1}, "pipeline": {"files": 7, "last_run_at": "b"}}
        assert facts_checksum(one) == facts_checksum(two)

    def test_a_changed_figure_changes_it(self):
        assert facts_checksum({"kpis": {"impacts": 1}}) != facts_checksum({"kpis": {"impacts": 2}})


@pytest.fixture
def writable(database):
    with psycopg.connect(database, row_factory=dict_row, autocommit=True) as conn:
        conn.execute("DELETE FROM weekly_reports")
        yield conn
        conn.execute("DELETE FROM weekly_reports")


def commentary_for(conn):
    facts = build_facts(build_dashboard(conn))
    return written(
        {
            "summary": f"The fleet had {facts.kpis.impacts} impacts.",
            "highlights": [f"{facts.top_machines[0].ref_no} ran the most hours."],
            "checks": ["Review the impacts with no driver."],
        }
    )


class TestFacts:
    def test_figures_match_the_dashboard(self, writable):
        dashboard = build_dashboard(writable)
        facts = build_facts(dashboard)
        assert facts.kpis == dashboard.kpis
        assert facts.branches == dashboard.branches
        assert facts.days_with_data == 7

    def test_known_results(self, writable):
        facts = build_facts(build_dashboard(writable))
        assert facts.kpis.impacts == 133
        assert facts.top_drivers[0].driver_name == "Ashwin Daniels"
        assert facts.top_drivers[0].impacts == 10
        assert [machine.ref_no for machine in facts.inactive_machines] == ["P57083"]
        assert all(driver.driver_name for driver in facts.top_drivers)


class TestPublish:
    def test_publishes_once_per_week(self, writable):
        reply = commentary_for(writable)
        assert publish_report(writable, ScriptedLLM(reply)) == "published"
        assert publish_report(writable, ScriptedLLM()) == "unchanged"
        count = writable.execute("SELECT COUNT(*) AS n FROM weekly_reports").fetchone()["n"]
        assert count == 1

    def test_force_writes_the_commentary_again(self, writable):
        reply = commentary_for(writable)
        publish_report(writable, ScriptedLLM(reply))
        assert publish_report(writable, ScriptedLLM(reply), force=True) == "published"

    def test_a_model_failure_still_publishes_the_figures(self, writable):
        outcome = publish_report(writable, ScriptedLLM(LLMError("busy")))
        assert outcome == "published_without_commentary"
        row = writable.execute("SELECT facts, commentary FROM weekly_reports").fetchone()
        assert row["commentary"] is None
        assert row["facts"]["kpis"]["impacts"] == 133

    def test_missing_commentary_is_tried_again(self, writable):
        publish_report(writable, ScriptedLLM(LLMError("busy")))
        assert publish_report(writable, ScriptedLLM(commentary_for(writable))) == "published"


class TestRoute:
    def test_returns_the_latest_report(self, writable):
        publish_report(writable, ScriptedLLM(commentary_for(writable)))
        response = TestClient(main.app).get("/api/v1/reports/latest")
        assert response.status_code == 200
        body = response.json()
        assert body["week_start"] == "2026-09-07"
        assert body["facts"]["kpis"]["impacts"] == 133
        assert body["commentary"]["checks"]
        assert body["model"] == "scripted"

    def test_no_report_returns_404(self, writable):
        assert TestClient(main.app).get("/api/v1/reports/latest").status_code == 404

    def test_the_api_connection_cannot_write_reports(self, writable):
        with db.connect() as conn, pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute("DELETE FROM weekly_reports")
