from melate_app_lab.desktop_controller import parse_multiline_tickets, run_brain, run_report


RESULT = "2 18 22 38 51 52"
PLAYED_TEXT = "\n".join(
    [
        "7 15 29 41 42 48",
        "7 16 18 23 29 39",
        "9 13 18 30 45 52",
        "7 15 20 30 36 53",
    ]
)


def test_parse_multiline_tickets_parses_four_tickets():
    tickets = parse_multiline_tickets(PLAYED_TEXT)

    assert len(tickets) == 4
    assert tickets[2] == [9, 13, 18, 30, 45, 52]


def test_run_brain_works_without_ui():
    review = run_brain(4218, RESULT, PLAYED_TEXT)

    assert review["components"]["postmortem"]["captured_numbers"] == [18, 52]


def test_run_report_returns_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_report(4218, RESULT, PLAYED_TEXT)

    assert result["json_path"].endswith("postmortem_4218.json")
    assert result["html_path"].endswith("postmortem_4218.html")
    assert result["csv_path"].endswith("postmortem_4218.csv")
