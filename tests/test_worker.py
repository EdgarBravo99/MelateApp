from melate_app_lab.worker import QtTaskRunner, run_task_sync


def test_run_task_sync_returns_result_and_logs():
    result = run_task_sync(lambda value: value + 1, 2)

    assert result.ok is True
    assert result.result == 3
    assert "Listo." in result.logs


def test_qt_task_runner_has_clear_message_when_missing_pyside(monkeypatch):
    monkeypatch.setattr("melate_app_lab.worker.pyside_available", lambda: False)

    try:
        QtTaskRunner()
    except RuntimeError as exc:
        assert "PySide6" in str(exc)
    else:
        raise AssertionError("QtTaskRunner should require PySide6")
