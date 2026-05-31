from typer.testing import CliRunner

from melate_app_lab.cli import app


def test_postmortem_accepts_single_played_option_with_multiple_values():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "postmortem",
            "--draw",
            "4218",
            "--result",
            "2 18 22 38 51 52",
            "--played",
            "7 15 29 41 42 48",
            "7 16 18 23 29 39",
            "9 13 18 30 45 52",
            "7 15 20 30 36 53",
        ],
    )

    assert result.exit_code == 0
    assert '"captured_numbers"' in result.output
    assert "18" in result.output
    assert "52" in result.output


def test_build_info_command_returns_packaging_metadata():
    runner = CliRunner()
    result = runner.invoke(app, ["build-info"])

    assert result.exit_code == 0
    assert '"dist_path"' in result.output
    assert "PyInstaller" in result.output


def test_guardrail_scan_command_runs():
    runner = CliRunner()
    result = runner.invoke(app, ["guardrail-scan"])

    assert result.exit_code == 0
    assert '"violations": []' in result.output


def test_review_all_command_runs(tmp_path, monkeypatch):
    import melate_app_lab.cli as cli
    from melate_app_lab.historical_store import import_draws_to_memory

    db_path = tmp_path / "data" / "memory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cli, "DEFAULT_DB_PATH", db_path)

    import melate_app_lab.desktop_controller as controller
    monkeypatch.setattr(controller, "open_report", lambda path: {"opened": str(path)})

    dummy_history = [
        {"draw": 100, "numbers": [1, 2, 3, 4, 5, 6], "sum": 21, "sum_band": "low_band", "block_signature": "6-0-0-0-0", "block_presence_signature": "1-0-0-0-0", "game": "revancha", "date": "2026-05-29"},
        {"draw": 101, "numbers": [1, 2, 3, 4, 5, 7], "sum": 22, "sum_band": "low_band", "block_signature": "6-0-0-0-0", "block_presence_signature": "1-0-0-0-0", "game": "revancha", "date": "2026-05-29"},
    ]
    import_draws_to_memory(dummy_history, db_path)

    runner = CliRunner()
    result = runner.invoke(app, ["review-all", "--count", "5", "--game", "revancha"])
    assert result.exit_code == 0
    assert '"portfolio_id"' in result.output
    assert '"next_draw": 102' in result.output


def test_workflow_loop_command_runs(tmp_path, monkeypatch):
    import melate_app_lab.cli as cli
    from melate_app_lab.historical_store import import_draws_to_memory

    db_path = tmp_path / "data" / "memory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cli, "DEFAULT_DB_PATH", db_path)

    dummy_history = [
        {"draw": 100, "numbers": [1, 2, 3, 4, 5, 6], "sum": 21, "sum_band": "low_band", "block_signature": "6-0-0-0-0", "block_presence_signature": "1-0-0-0-0", "game": "revancha", "date": "2026-05-29"},
        {"draw": 101, "numbers": [1, 2, 3, 4, 5, 7], "sum": 22, "sum_band": "low_band", "block_signature": "6-0-0-0-0", "block_presence_signature": "1-0-0-0-0", "game": "revancha", "date": "2026-05-29"},
    ]
    import_draws_to_memory(dummy_history, db_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "workflow-loop",
            "--draw",
            "102",
            "--game",
            "revancha",
            "--pool-size",
            "10",
            "--seed",
            "42",
            "--played",
            "0 2",
            "--result",
            "1 2 3 4 5 8",
        ],
    )
    assert result.exit_code == 0
    assert "portfolio_id" in result.output
    assert "coverage" in result.output
    assert "played_count" in result.output
    assert "evaluation" in result.output


def test_backtest_cli_options(tmp_path, monkeypatch):
    import melate_app_lab.cli as cli
    from melate_app_lab.historical_store import import_draws_to_memory

    db_path = tmp_path / "data" / "memory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli, "DEFAULT_DB_PATH", db_path)

    dummy_history = []
    for draw in range(1, 45):
        dummy_history.append({
            "draw": draw,
            "numbers": [1, 2, 3, 4, 5, 6],
            "sum": 21,
            "sum_band": "low_band",
            "block_signature": "6-0-0-0-0",
            "block_presence_signature": "1-0-0-0-0",
            "game": "revancha",
            "date": "2026-05-29"
        })
    import_draws_to_memory(dummy_history, db_path)

    import melate_app_lab.desktop_controller as controller
    monkeypatch.setattr(controller, "open_report", lambda path: None)

    called_args = {}
    import melate_app_lab.backtest_lab as backtest_lab
    def mock_run_backtest(*args, **kwargs):
        called_args.update(kwargs)
        return {
            "game": kwargs.get("game"),
            "draws_evaluated": 1,
            "metrics": {},
            "results": [],
            "manifest": {"commit_sha": "dummy", "branch": "dummy"},
        }
    monkeypatch.setattr(backtest_lab, "run_backtest", mock_run_backtest)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "backtest",
            "--limit", "5",
            "--game", "revancha",
            "--pool-size", "10",
            "--use-optimizer",
            "--use-feedback-profile",
        ],
    )
    assert result.exit_code == 0
    assert called_args["use_optimizer"] is True
    assert called_args["use_feedback_profile"] is True
    assert called_args["db_path"] == db_path

    help_result = runner.invoke(app, ["backtest", "--help"])
    assert help_result.exit_code == 0
    assert "optimizer" in help_result.output
    assert "feedback" in help_result.output


