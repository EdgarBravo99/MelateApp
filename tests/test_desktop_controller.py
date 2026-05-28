from melate_app_lab.desktop_controller import (
    import_history_file,
    list_report_files,
    load_history_table,
    parse_multiline_tickets,
    parse_played_tickets_flexible,
    run_brain,
    run_report,
    suggest_next_draw_from_memory,
)

RESULT = "2 18 22 38 51 52"
PLAYED_TEXT = "\n".join(["7 15 29 41 42 48", "7 16 18 23 29 39", "9 13 18 30 45 52", "7 15 20 30 36 53"])


def test_parse_multiline_tickets_parses_four_tickets():
    tickets = parse_multiline_tickets(PLAYED_TEXT)
    assert len(tickets) == 4
    assert tickets[2] == [9, 13, 18, 30, 45, 52]


def test_parse_played_tickets_flexible_accepts_one_line_groups():
    text = "7 15 29 41 42 48 7 16 18 23 29 39 9 13 18 30 45 52 7 15 20 30 36 53"
    tickets = parse_played_tickets_flexible(text)
    assert len(tickets) == 4
    assert tickets[-1] == [7, 15, 20, 30, 36, 53]


def test_parse_played_tickets_flexible_accepts_labels():
    tickets = parse_played_tickets_flexible("A: 7 15 29 41 42 48\nB: 7 16 18 23 29 39")
    assert tickets == [[7, 15, 29, 41, 42, 48], [7, 16, 18, 23, 29, 39]]


def test_suggest_next_draw_from_memory_after_import(tmp_path):
    csv_path = tmp_path / "resultados.csv"
    db_path = tmp_path / "data" / "memory.sqlite"
    csv_path.write_text("draw,date,numbers\n4218,2026-05-27,2 18 22 38 51 52\n", encoding="utf-8")
    result = import_history_file(csv_path, db_path=db_path)
    assert result["suggested_next_draw"] == 4219
    assert suggest_next_draw_from_memory(db_path) == 4219
    assert load_history_table(db_path)[0]["draw"] == 4218


def test_run_brain_works_without_ui():
    review = run_brain(4218, RESULT, PLAYED_TEXT)
    assert review["components"]["postmortem"]["captured_numbers"] == [18, 52]


def test_run_report_returns_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_report(4218, RESULT, PLAYED_TEXT)
    assert result["json_path"].endswith("postmortem_4218.json")
    assert result["html_path"].endswith("postmortem_4218.html")
    assert result["csv_path"].endswith("postmortem_4218.csv")
    assert {item["type"] for item in list_report_files(tmp_path / "outputs")} == {"csv", "html", "json"}
