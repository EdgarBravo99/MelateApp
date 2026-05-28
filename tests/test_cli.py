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
