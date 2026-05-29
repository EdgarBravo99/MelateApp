from melate_app_lab.desktop_controller import (
    import_history_file,
    list_report_files,
    load_history_table,
    parse_multiline_tickets,
    parse_played_tickets_flexible,
    run_brain,
    run_report,
    run_stress,
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
        assert "separados por" in str(exc).casefold()
    else:
        raise AssertionError("Expected ValueError")


def test_parse_played_tickets_flexible_reports_duplicates():
    try:
        parse_played_tickets_flexible("1 2 3 4 5 5")
    except ValueError as exc:
        assert "separados por" in str(exc).casefold()
    else:
        raise AssertionError("Expected ValueError")


def test_parse_played_tickets_flexible_reports_out_of_range():
    try:
        parse_played_tickets_flexible("1 2 3 4 5 57")
    except ValueError as exc:
        assert "separados por" in str(exc).casefold()
    else:
        raise AssertionError("Expected ValueError")


def test_parse_played_tickets_flexible_rejects_glued_numbers():
    try:
        parse_played_tickets_flexible("71529414248")
    except ValueError as exc:
        assert "separados por" in str(exc).casefold()
    else:
        raise AssertionError("Expected ValueError")


def test_run_brain_works_without_ui():
    review = run_brain(4218, RESULT, PLAYED_TEXT)

    assert review["components"]["postmortem"]["captured_numbers"] == [18, 52]


def test_run_stress_works_without_ui():
    review = run_stress(RESULT, PLAYED_TEXT)
    assert "played_coverage" in review


def test_run_stress_invalid_input_raises_value_error():
    import pytest
    with pytest.raises(ValueError):
        run_stress("invalid", PLAYED_TEXT)
        
    with pytest.raises(ValueError):
        run_stress(RESULT, "only 5 numbers here 1 2 3 4")


def test_run_brain_invalid_input_raises_value_error():
    import pytest
    with pytest.raises(ValueError):
        run_brain(4218, "invalid", PLAYED_TEXT)


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


def test_suggest_next_draw_from_memory_empty_db(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    suggestion = suggest_next_draw_from_memory(db_path)
    assert suggestion["next_draw"] == 4218


def test_list_report_files_detects_html_json_csv(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    for extension in ("html", "json", "csv"):
        (outputs / f"postmortem_4218.{extension}").write_text("x", encoding="utf-8")

    reports = list_report_files(outputs)

    assert [report["extension"] for report in reports] == ["csv", "html", "json"]


def test_run_revision_completa_and_db_handlers(tmp_path, monkeypatch):
    import melate_app_lab.desktop_controller as controller
    from melate_app_lab.historical_store import import_draws_to_memory

    db_path = tmp_path / "data" / "memory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    opened_paths = []
    def mock_open_report(path):
        opened_paths.append(path)
        return {"opened": str(path)}
    monkeypatch.setattr(controller, "open_report", mock_open_report)

    dummy_history = [
        {"draw": 100, "numbers": [1, 2, 3, 4, 5, 6], "sum": 21, "sum_band": "low_band", "block_signature": "6-0-0-0-0", "block_presence_signature": "1-0-0-0-0", "game": "revancha", "date": "2026-05-29"},
        {"draw": 101, "numbers": [1, 2, 3, 4, 5, 7], "sum": 22, "sum_band": "low_band", "block_signature": "6-0-0-0-0", "block_presence_signature": "1-0-0-0-0", "game": "revancha", "date": "2026-05-29"},
    ]
    import_draws_to_memory(dummy_history, db_path)

    res = controller.run_revision_completa(db_path, count=5, game="revancha", notes="Test complete revision notes")

    assert res["portfolio_id"] > 0
    assert "portfolio_report" in res["portfolio_report_path"]
    assert "historical_graph" in res["graph_html_path"]
    assert res["next_draw"] == 102
    assert res["history_count"] == 2
    assert len(opened_paths) == 2

    ports = controller.load_portfolios_list(db_path)
    assert len(ports) == 1
    assert ports[0]["id"] == res["portfolio_id"]
    assert ports[0]["draw"] == 102
    assert ports[0]["notes"] == "Test complete revision notes"

    cands = controller.load_portfolio_candidates(db_path, res["portfolio_id"])
    assert len(cands) == 5
    assert cands[0]["portfolio_id"] == res["portfolio_id"]

    cand_id = cands[0]["id"]
    controller.change_candidate_state(db_path, cand_id, "Favorito")
    cands_updated = controller.load_portfolio_candidates(db_path, res["portfolio_id"])
    assert cands_updated[0]["state"] == "Favorito"

    controller.save_candidate_review(db_path, cand_id, result_numbers=[1, 2, 3, 4, 5, 6], hits_count=6)
    cands_reviewed = controller.load_portfolio_candidates(db_path, res["portfolio_id"])
    assert cands_reviewed[0]["state"] == "Revisado"
    assert cands_reviewed[0]["result_numbers"] == [1, 2, 3, 4, 5, 6]
    assert cands_reviewed[0]["hits_count"] == 6

    # Import draw 102 into history to evaluate portfolio retrospectively
    import_draws_to_memory([
        {"draw": 102, "numbers": [1, 2, 3, 10, 20, 30], "sum": 66, "sum_band": "mid_band", "block_signature": "3-1-1-1-0", "block_presence_signature": "1-1-1-1-0", "game": "revancha", "date": "2026-05-30"}
    ], db_path)

    eval_res = controller.evaluate_portfolio_against_history(db_path, res["portfolio_id"])
    assert eval_res["evaluated"] == 5
    assert eval_res["draw"] == 102
    assert eval_res["result_numbers"] == [1, 2, 3, 10, 20, 30]

    cands_reviewed_hist = controller.load_portfolio_candidates(db_path, res["portfolio_id"])
    for c in cands_reviewed_hist:
        assert c["state"] == "Revisado"
        assert c["result_numbers"] == [1, 2, 3, 10, 20, 30]


