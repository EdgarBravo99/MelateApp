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
        from PySide6.QtCore import QObject, QThread, Signal, Slot

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

        class SignalReceiver(QObject):
            def __init__(
                self,
                log_fn: Callable[[str], None] | None,
                result_fn: Callable[[Any], None] | None,
                error_fn: Callable[[str], None] | None,
                finished_fn: Callable[[], None] | None,
            ) -> None:
                super().__init__()
                self.log_fn = log_fn
                self.result_fn = result_fn
                self.error_fn = error_fn
                self.finished_fn = finished_fn

            @Slot(str)
            def handle_log(self, msg: str) -> None:
                if self.log_fn:
                    self.log_fn(msg)

            @Slot(object)
            def handle_result(self, payload: Any) -> None:
                if self.result_fn:
                    self.result_fn(payload)

            @Slot(str)
            def handle_error(self, msg: str) -> None:
                if self.error_fn:
                    self.error_fn(msg)

            @Slot()
            def handle_finished(self) -> None:
                if self.finished_fn:
                    self.finished_fn()

        thread = QThread()
        worker = TaskObject()
        receiver = SignalReceiver(on_log, on_result, on_error, on_finished)

        worker.moveToThread(thread)

        worker.log.connect(receiver.handle_log)
        worker.result.connect(receiver.handle_result)
        worker.error.connect(receiver.handle_error)
        worker.finished.connect(receiver.handle_finished)
        worker.finished.connect(thread.quit)

        def cleanup() -> None:
            worker.deleteLater()
            receiver.deleteLater()
            thread.deleteLater()
            if worker in self._workers:
                self._workers.remove(worker)
            if receiver in self._workers:
                self._workers.remove(receiver)
            if thread in self._threads:
                self._threads.remove(thread)

        thread.finished.connect(cleanup)
        thread.started.connect(worker.execute)
        self._threads.append(thread)
        self._workers.append(worker)
        self._workers.append(receiver)
        thread.start()
        return thread
