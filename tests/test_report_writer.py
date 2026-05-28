import json

from melate_app_lab.evaluator_brain import brain_review
from melate_app_lab.guardrails import validate_text
from melate_app_lab.report_writer import write_html_report, write_json_report


RESULT = [2, 18, 22, 38, 51, 52]
PLAYED = [
    [7, 15, 29, 41, 42, 48],
    [7, 16, 18, 23, 29, 39],
    [9, 13, 18, 30, 45, 52],
    [7, 15, 20, 30, 36, 53],
]


def test_write_reports(tmp_path):
    report = brain_review(4218, RESULT, PLAYED)
    json_path = tmp_path / "postmortem_4218.json"
    html_path = tmp_path / "postmortem_4218.html"

    write_json_report(report, json_path)
    write_html_report(report, html_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["draw"] == 4218
    html = html_path.read_text(encoding="utf-8")
    assert "Sorteo 4218" in html
    assert "18" in html
    assert "52" in html
    assert validate_text(html) == html
