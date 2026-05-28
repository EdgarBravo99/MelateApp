from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


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
    def __init__(self) -> None:
        if not pyside_available():
            raise RuntimeError("PySide6 no esta instalado. Instala el extra desktop.")
