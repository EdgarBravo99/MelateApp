from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from . import desktop_controller as controller
from .memory import DEFAULT_DB_PATH
from .theme import APP_QSS
from .worker import QtTaskRunner, run_task_sync


DEFAULT_RESULT = "2 18 22 38 51 52"
DEFAULT_PLAYED = "\n".join(
    [
        "7 15 29 41 42 48",
        "7 16 18 23 29 39",
        "9 13 18 30 45 52",
        "7 15 20 30 36 53",
    ]
)


def launch_desktop() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QProgressBar,
            QPushButton,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except Exception:
        print("PySide6 no esta instalado. Ejecuta: py -3 -m pip install -e .[desktop]")
        return 2

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    window = QMainWindow()
    window.setWindowTitle("MelateApp Local Intelligence Lab")
    window.resize(1180, 760)

    root = QWidget()
    root_layout = QHBoxLayout(root)

    sidebar = QFrame()
    sidebar.setObjectName("Sidebar")
    sidebar.setFixedWidth(180)
    sidebar_layout = QVBoxLayout(sidebar)
    for label in ["Nuevo analisis", "Historial", "Reportes", "Configuracion"]:
        sidebar_layout.addWidget(QPushButton(label))
    sidebar_layout.addStretch(1)

    main = QWidget()
    main_layout = QVBoxLayout(main)
    tabs = QTabWidget()
    analysis = QWidget()
    analysis_layout = QVBoxLayout(analysis)

    draw_input = QLineEdit("4218")
    result_input = QLineEdit(DEFAULT_RESULT)
    played_input = QTextEdit(DEFAULT_PLAYED)
    console = QPlainTextEdit()
    console.setObjectName("ActivityConsole")
    console.setReadOnly(True)
    progress = QProgressBar()
    progress.setRange(0, 1)
    progress.setValue(0)
    qt_runner = QtTaskRunner()
    last_html_report: dict[str, str | None] = {"path": None}

    form = QGridLayout()
    form.addWidget(QLabel("Sorteo"), 0, 0)
    form.addWidget(draw_input, 0, 1)
    form.addWidget(QLabel("Resultado"), 1, 0)
    form.addWidget(result_input, 1, 1)
    form.addWidget(QLabel("Boletos jugados"), 2, 0, alignment=Qt.AlignTop)
    form.addWidget(played_input, 2, 1)
    analysis_layout.addLayout(form)

    metrics = QGridLayout()
    metric_labels = {}
    for index, name in enumerate(["Capturados", "No capturados", "Suma", "Banda", "Firma", "Anclas", "Alertas"]):
        card = QLabel(f"{name}\n-")
        card.setObjectName("MetricCard")
        metric_labels[name] = card
        metrics.addWidget(card, index // 4, index % 4)
    analysis_layout.addLayout(metrics)

    button_row = QHBoxLayout()

    def log(message: str) -> None:
        console.appendPlainText(message)

    def handle_payload(payload: object) -> None:
        log(json.dumps(payload, ensure_ascii=False, indent=2))
        if isinstance(payload, dict):
            if payload.get("html_path"):
                last_html_report["path"] = str(payload["html_path"])
            trace = payload.get("components", {}).get("trace") if isinstance(payload.get("components"), dict) else payload
            postmortem = payload.get("components", {}).get("postmortem") if isinstance(payload.get("components"), dict) else payload
            stress = payload.get("components", {}).get("stress_review") if isinstance(payload.get("components"), dict) else payload
            if isinstance(postmortem, dict):
                metric_labels["Capturados"].setText(f"Capturados\n{postmortem.get('captured_numbers', '-')}")
                metric_labels["No capturados"].setText(f"No capturados\n{postmortem.get('missed_numbers', '-')}")
            if isinstance(trace, dict):
                metric_labels["Suma"].setText(f"Suma\n{trace.get('sum', '-')}")
                metric_labels["Banda"].setText(f"Banda\n{trace.get('sum_band', '-')}")
                metric_labels["Firma"].setText(f"Firma\n{trace.get('block_signature', '-')}")
            if isinstance(stress, dict):
                metric_labels["Anclas"].setText(
                    f"Anclas\n{stress.get('anchor_concentration', {}).get('repeated_numbers', '-')}"
                )
                metric_labels["Alertas"].setText(f"Alertas\n{len(stress.get('review_alerts_es', []))}")

    def finish_action(ok: bool = True) -> None:
        progress.setRange(0, 1)
        progress.setValue(1 if ok else 0)

    def run_action(name: str, fn: Callable[[], object], threaded: bool = False) -> None:
        progress.setRange(0, 0)
        log(f"Ejecutando {name}...")
        if threaded:
            qt_runner.run(
                fn,
                on_log=log,
                on_result=handle_payload,
                on_error=lambda message: QMessageBox.warning(window, "MelateApp", message),
                on_finished=lambda: finish_action(True),
            )
            return

        worker_result = run_task_sync(fn, log=log)
        finish_action(worker_result.ok)
        if not worker_result.ok:
            QMessageBox.warning(window, "MelateApp", worker_result.error or "Error")
            return
        handle_payload(worker_result.result)

    def open_last_html_report() -> object:
        path = last_html_report["path"] or str(Path("outputs") / f"postmortem_{int(draw_input.text())}.html")
        return controller.open_report(path)

    def import_history_dialog() -> object:
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            window,
            "Import History",
            str(Path("data") / "samples"),
            "History files (*.csv *.json)",
        )
        if not file_path:
            return {"imported": 0, "message": "Importacion cancelada."}
        from .historical_store import import_draws_to_memory, load_draw_history
        from .importers import parse_draw_csv, parse_draw_json

        path = Path(file_path)
        records = parse_draw_json(path) if path.suffix.lower() == ".json" else parse_draw_csv(path)
        import_draws_to_memory(records, DEFAULT_DB_PATH)
        history = load_draw_history(DEFAULT_DB_PATH)
        return {"imported": len(records), "history_count": len(history), "memory_path": str(DEFAULT_DB_PATH)}

    actions = [
        ("Trace", lambda: controller.run_trace(int(draw_input.text()), result_input.text()), False),
        ("Postmortem", lambda: controller.run_postmortem(int(draw_input.text()), result_input.text(), played_input.toPlainText()), False),
        ("Stress Review", lambda: controller.run_stress(result_input.text(), played_input.toPlainText()), True),
        ("Brain Review", lambda: controller.run_brain(int(draw_input.text()), result_input.text(), played_input.toPlainText()), True),
        ("Remember", lambda: controller.run_remember(int(draw_input.text()), result_input.text(), played_input.toPlainText()), False),
        ("Generate Report", lambda: controller.run_report(int(draw_input.text()), result_input.text(), played_input.toPlainText()), False),
        ("Open HTML Report", open_last_html_report, False),
        ("Import History", import_history_dialog, True),
    ]
    for label, fn, threaded in actions:
        button = QPushButton(label)
        button.clicked.connect(lambda _checked=False, label=label, fn=fn, threaded=threaded: run_action(label, fn, threaded))
        button_row.addWidget(button)
    analysis_layout.addLayout(button_row)
    analysis_layout.addWidget(progress)
    analysis_layout.addWidget(QLabel("Consola interna"))
    analysis_layout.addWidget(console)

    tabs.addTab(analysis, "Nuevo analisis")
    tabs.addTab(QLabel("Historial local disponible desde import-history."), "Historial")
    tabs.addTab(QLabel("Reportes exportados en outputs/."), "Reportes")
    tabs.addTab(QLabel("Todo se ejecuta localmente en modo review_default."), "Configuracion")
    main_layout.addWidget(tabs)
    root_layout.addWidget(sidebar)
    root_layout.addWidget(main)
    window.setCentralWidget(root)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(launch_desktop())
