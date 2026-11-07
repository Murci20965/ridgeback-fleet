"""The stress test's grading has to be right, or its published numbers mean nothing."""

from stress_test import CASES, Case, grade

CASE = Case("Group", "Question?", must_contain=(r"\bcan't\b",), fabrication=(r"\d+ hours",))


def test_a_good_answer_passes():
    assert grade(CASE, "I can't say.") == "Pass"


def test_fabrication_outranks_a_good_phrase():
    assert grade(CASE, "I can't say, but it was 5 hours.") == "Fabricated"


def test_a_missing_phrase_is_weak():
    assert grade(CASE, "No idea.") == "Weak"


def test_every_question_is_unique():
    assert len({case.question for case in CASES}) == len(CASES)
