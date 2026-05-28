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


def test_parse_played_tickets_flexible_accepts_multiline():
    tickets = parse_played_tickets_flexible(PLAYED_TEXT)

    assert len(tickets) == 4
    assert tickets[0] == [7, 15, 29, 41, 42, 48]


def test_parse_played_tickets_flexible_accepts_24_numbers_on_one_line():
    tickets = parse_played_tickets_flexible(PLAYED_TEXT.replace("\n", " "))

    assert len(tickets) == 4
    assert tickets[3] == [7, 15, 20, 30, 36, 53]


def test_parse_played_tickets_flexible_accepts_commas_and_labels():
    tickets = parse_played_tickets_flexible("A: 7,15,29,41,42,48 B: 9,13,18,30,45,52")

    assert tickets == [[7, 15, 29, 41, 42, 48], [9, 13, 18, 30, 45, 52]]


def test_parse_played_tickets_flexible_reports_leftover_numbers():
    try:
        parse_played_tickets_flexible("1 2 3 4 5 6 7")
    except ValueError as exc:
        assert "sobran" in str(exc).casefold()
    else:
        raise AssertionError("Expected ValueError")


def test_parse_played_tickets_flexible_reports_duplicates():
    try:
        parse_played_tickets_flexible("1 2 3 4 5 5")
    except ValueError as exc:
        assert "duplicados" in str(exc).casefold()
    else:
        raise AssertionError("Expected ValueError")


def test_parse_played_tickets_flexible_reports_out_of_range():
    try:
        parse_played_tickets_flexible("1 2 3 4 5 57")
    except ValueError as exc:
        assert "fuera de rango" in str(exc).casefold()
    else:
        raise AssertionError("Expected ValueError")


def test_run_brain_works_without_ui():
    review = run_brain(4218, RESULT, PLAYED_TEXT)

    assert review["components"]["postmortem"]["captured_numbers"] == [18, 52]


def test_run_report_returns_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_report(4218, RESULT, PLAYED_TEXT)

    assert result["json_path"].endswith("postmortem_4218.json")
    assert result["html_path"].endswith("postmortem_4218.html")
    assert result["csv_path"].endswith("postmortem_4218.csv")


def test_history_import_table_and_next_draw(tmp_path):
    history_path = tmp_path / "history.csv"
    history_path.write_text(
        "game,draw,date,numbers\nrevancha,4218,2026-05-26,\"2 18 22 38 51 52\"\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "memory.sqlite"

    result = import_history_file(history_path, db_path)
    table = load_history_table(db_path)
    suggestion = suggest_next_draw_from_memory(db_path)

    assert result["imported"] == 1
    assert table[0]["draw"] == 4218
    assert suggestion["next_draw"] == 4219
    assert suggestion["review_default"]["mode"] == "review_default"


def test_list_report_files_detects_html_json_csv(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    for extension in ("html", "json", "csv"):
        (outputs / f"postmortem_4218.{extension}").write_text("x", encoding="utf-8")

    reports = list_report_files(outputs)

    assert [report["extension"] for report in reports] == ["csv", "html", "json"]
