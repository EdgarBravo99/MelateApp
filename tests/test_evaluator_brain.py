from melate_app_lab.evaluator_brain import brain_review
from melate_app_lab.guardrails import validate_output_json


RESULT = [2, 18, 22, 38, 51, 52]
PLAYED = [
    [7, 15, 29, 41, 42, 48],
    [7, 16, 18, 23, 29, 39],
    [9, 13, 18, 30, 45, 52],
    [7, 15, 20, 30, 36, 53],
]


def test_brain_review_integrates_components_and_guardrails():
    review = brain_review(4218, RESULT, PLAYED)

    assert "18" in review["what_worked_es"]
    assert "52" in review["what_worked_es"]
    assert "2, 22, 38, 51" in review["what_was_missed_es"]
    assert {"trace", "postmortem", "graph", "stress_review"} <= set(review["components"])
    assert validate_output_json(review) == review
