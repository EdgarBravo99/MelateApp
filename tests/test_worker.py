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


def test_qt_task_runner_catches_exceptions_and_emits_traceback():
    import pytest
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication
    import time
    
    app = QCoreApplication.instance() or QCoreApplication([])
    runner = QtTaskRunner()
    
    error_emitted = []
    finished = []
    
    def crash():
        raise ValueError("Simulated crash")
        
    def on_error(msg):
        error_emitted.append(msg)
        
    def on_finished():
        finished.append(True)
        app.quit()
        
    runner.run(crash, on_error=on_error, on_finished=on_finished)
    
    # Spin the event loop to let thread run and signals process
    start_time = time.time()
    while not finished and time.time() - start_time < 2:
        app.processEvents()
        time.sleep(0.01)
        
    assert len(error_emitted) == 1
    assert "Simulated crash" in error_emitted[0]
    assert "Traceback" in error_emitted[0]
