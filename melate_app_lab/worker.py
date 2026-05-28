from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


"""Worker primitives.

`run_task_sync` is the lightweight synchronous worker base used by tests and
non-UI callers. `QtTaskRunner` wraps the same callable contract in a QThread
when PySide6 is installed so desktop tasks do not block the UI.
"""


@dataclass
class WorkerResult:
    ok: bool
    result: Any = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)


def run_task_sync(
    task: Callable[..., Any],
    *args: Any,
    log: Callable[[str], None] | None = None,
    **kwargs: Any,
) -> WorkerResult:
    logs: list[str] = []

    def emit(message: str) -> None:
        logs.append(message)
        if log:
            log(message)

    try:
        emit("Ejecutando revision...")
        result = task(*args, **kwargs)
        emit("Listo.")
        return WorkerResult(ok=True, result=result, logs=logs)
    except Exception as exc:  # pragma: no cover - exercised by callers as text path
        emit(f"Error: {exc}")
        return WorkerResult(ok=False, error=str(exc), logs=logs)


def pyside_available() -> bool:
    try:
        import PySide6  # noqa: F401
    except Exception:
        return False
    return True


class QtTaskRunner:
    """Run callables on a QThread and report logs/results through callbacks."""

    def __init__(self) -> None:
        if not pyside_available():
            raise RuntimeError("PySide6 no esta instalado. Instala el extra desktop.")
        self._threads: list[Any] = []
        self._workers: list[Any] = []

    def run(
        self,
        task: Callable[..., Any],
        *args: Any,
        on_log: Callable[[str], None] | None = None,
        on_result: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> Any:
        from PySide6.QtCore import QObject, QThread, Signal

        class TaskObject(QObject):
            log = Signal(str)
            result = Signal(object)
            error = Signal(str)
            finished = Signal()

            def execute(self) -> None:
                import traceback
                try:
                    self.log.emit("Ejecutando revision...")
                    payload = task(*args, **kwargs)
                    self.result.emit(payload)
                    self.log.emit("Listo.")
                except Exception as exc:  # pragma: no cover - Qt path
                    error_msg = f"{exc}\n{traceback.format_exc()}"
                    self.error.emit(error_msg)
                    self.log.emit(f"Error inesperado: {exc}")
                finally:
                    self.finished.emit()

        thread = QThread()
        worker = TaskObject()
        worker.moveToThread(thread)
        if on_log:
            worker.log.connect(on_log)
        if on_result:
            worker.result.connect(on_result)
        if on_error:
            worker.error.connect(on_error)
        if on_finished:
            worker.finished.connect(on_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        thread.started.connect(worker.execute)
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()
        return thread
