from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from . import desktop_controller as controller
from .theme import APP_QSS
from .worker import QtTaskRunner, run_task_sync

DEFAULT_RESULT = "2 18 22 38 51 52"
DEFAULT_PLAYED = "\n".join([
    "7 15 29 41 42 48",
    "7 16 18 23 29 39",
    "9 13 18 30 45 52",
    "7 15 20 30 36 53",
])


def launch_desktop() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
            QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
            QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit,
            QVBoxLayout, QWidget,
        )
    except Exception:
        print("PySide6 no esta instalado. Ejecuta: py -3 -m pip install -e .[desktop]")
        return 2

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = QMainWindow()
    window.setWindowTitle("MelateApp Local Intelligence Lab")
    window.resize(1280, 820)

    qt_runner = QtTaskRunner()
    last_html_report: dict[str, str | None] = {"path": None}

    root = QWidget()
    root_layout = QHBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)

    sidebar = QFrame()
    sidebar.setObjectName("Sidebar")
    sidebar.setFixedWidth(220)
    side_layout = QVBoxLayout(sidebar)
    side_title = QLabel("MelateApp\nLocal Lab")
    side_title.setObjectName("SidebarTitle")
    side_layout.addWidget(side_title)

    stack = QStackedWidget()
    sidebar_buttons: list[QPushButton] = []

    def set_active(index: int) -> None:
        stack.setCurrentIndex(index)
        for idx, button in enumerate(sidebar_buttons):
            button.setProperty("active", "true" if idx == index else "false")
            button.style().unpolish(button)
            button.style().polish(button)

    def sidebar_button(label: str, index: int) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("SidebarButton")
        button.clicked.connect(lambda _checked=False, idx=index: set_active(idx))
        sidebar_buttons.append(button)
        side_layout.addWidget(button)
        return button

    def title(text: str, subtitle: str) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 10)
        head = QLabel(text)
        head.setObjectName("PageTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("PageSubtitle")
        layout.addWidget(head)
        layout.addWidget(sub)
        return box

    def card(label: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        section = QLabel(label)
        section.setObjectName("SectionTitle")
        layout.addWidget(section)
        return frame, layout

    def fill_table(table: QTableWidget, rows: list[dict[str, object]], columns: list[str]) -> None:
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, column in enumerate(columns):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(row.get(column, ""))))
        table.resizeColumnsToContents()

    # Nuevo analisis
    analysis_page = QWidget()
    analysis_layout = QVBoxLayout(analysis_page)
    analysis_layout.addWidget(title("Nuevo analisis", "Revision local, memoria SQLite y reportes exportables."))

    draw_input = QLineEdit(str(controller.suggest_next_draw_from_memory()))
    result_input = QLineEdit(DEFAULT_RESULT)
    played_input = QTextEdit(DEFAULT_PLAYED)
    tickets_table = QTableWidget()
    tickets_table.setMinimumHeight(120)

    data_card, data_layout = card("Datos del sorteo")
    data_grid = QGridLayout()
    suggest_btn = QPushButton("Sugerir siguiente")
    data_grid.addWidget(QLabel("Sorteo"), 0, 0)
    data_grid.addWidget(draw_input, 0, 1)
    data_grid.addWidget(suggest_btn, 0, 2)
    data_grid.addWidget(QLabel("Resultado"), 1, 0)
    data_grid.addWidget(result_input, 1, 1, 1, 2)
    data_layout.addLayout(data_grid)

    tickets_card, tickets_layout = card("Boletos jugados")
    tickets_layout.addWidget(played_input)
    tickets_layout.addWidget(tickets_table)

    metric_card, metric_layout = card("Metricas")
    metrics = QGridLayout()
    metric_labels: dict[str, QLabel] = {}
    for index, name in enumerate(["Capturados", "No capturados", "Suma", "Banda", "Firma", "Anclas", "Alertas"]):
        item = QLabel(f"{name}\n-")
        item.setObjectName("MetricCard")
        metric_labels[name] = item
        metrics.addWidget(item, index // 4, index % 4)
    metric_layout.addLayout(metrics)

    action_card, action_layout = card("Acciones")
    button_row = QHBoxLayout()
    progress = QProgressBar()
    progress.setRange(0, 1)
    progress.setValue(0)
    console = QPlainTextEdit()
    console.setObjectName("ActivityConsole")
    console.setReadOnly(True)
    console.setMinimumHeight(130)

    def log(message: str) -> None:
        console.appendPlainText(message)

    def update_ticket_table() -> None:
        try:
            tickets = controller.parse_played_tickets_flexible(played_input.toPlainText())
            rows = [{"Boleto": chr(65 + idx), "Numeros": " ".join(map(str, ticket))} for idx, ticket in enumerate(tickets)]
            fill_table(tickets_table, rows, ["Boleto", "Numeros"])
        except Exception as exc:
            fill_table(tickets_table, [{"Boleto": "Error", "Numeros": str(exc)}], ["Boleto", "Numeros"])

    def handle_payload(payload: object) -> None:
        log(json.dumps(payload, ensure_ascii=False, indent=2))
        if not isinstance(payload, dict):
            return
        if payload.get("html_path"):
            last_html_report["path"] = str(payload["html_path"])
            refresh_reports()
        if payload.get("suggested_next_draw"):
            draw_input.setText(str(payload["suggested_next_draw"]))
            refresh_history()
        components = payload.get("components") if isinstance(payload.get("components"), dict) else {}
        trace = components.get("trace") if components else payload
        postmortem = components.get("postmortem") if components else payload
        stress = components.get("stress_review") if components else payload
        if isinstance(postmortem, dict):
            metric_labels["Capturados"].setText(f"Capturados\n{postmortem.get('captured_numbers', '-')}")
            metric_labels["No capturados"].setText(f"No capturados\n{postmortem.get('missed_numbers', '-')}")
        if isinstance(trace, dict):
            metric_labels["Suma"].setText(f"Suma\n{trace.get('sum', '-')}")
            metric_labels["Banda"].setText(f"Banda\n{trace.get('sum_band', '-')}")
            metric_labels["Firma"].setText(f"Firma\n{trace.get('block_signature', '-')}")
        if isinstance(stress, dict):
            metric_labels["Anclas"].setText(f"Anclas\n{stress.get('anchor_concentration', {}).get('repeated_numbers', '-')}")
            metric_labels["Alertas"].setText(f"Alertas\n{len(stress.get('review_alerts_es', []))}")

    def finish(ok: bool = True) -> None:
        progress.setRange(0, 1)
        progress.setValue(1 if ok else 0)

    def run_action(name: str, fn: Callable[[], object], threaded: bool = False) -> None:
        progress.setRange(0, 0)
        log(f"Ejecutando {name}...")
        if threaded:
            qt_runner.run(fn, on_log=log, on_result=handle_payload, on_error=lambda msg: QMessageBox.warning(window, "MelateApp", msg), on_finished=lambda: finish(True))
            return
        result = run_task_sync(fn, log=log)
        finish(result.ok)
        if not result.ok:
            QMessageBox.warning(window, "MelateApp", result.error or "Error")
            return
        handle_payload(result.result)

    def open_last_html_report() -> object:
        path = last_html_report["path"] or str(Path("outputs") / f"postmortem_{int(draw_input.text())}.html")
        return controller.open_report(path)

    def choose_import_file() -> object:
        path, _ = QFileDialog.getOpenFileName(window, "Importar historial", str(Path("data") / "samples"), "History files (*.csv *.json)")
        return {"message": "Importacion cancelada."} if not path else controller.import_history_file(path)

    actions = [
        ("Trace", lambda: controller.run_trace(int(draw_input.text()), result_input.text()), False),
        ("Postmortem", lambda: controller.run_postmortem(int(draw_input.text()), result_input.text(), played_input.toPlainText()), False),
        ("Stress Review", lambda: controller.run_stress(result_input.text(), played_input.toPlainText()), True),
        ("Brain Review", lambda: controller.run_brain(int(draw_input.text()), result_input.text(), played_input.toPlainText()), True),
        ("Remember", lambda: controller.run_remember(int(draw_input.text()), result_input.text(), played_input.toPlainText()), False),
        ("Generate Report", lambda: controller.run_report(int(draw_input.text()), result_input.text(), played_input.toPlainText()), False),
        ("Open HTML Report", open_last_html_report, False),
        ("Import History", choose_import_file, True),
    ]
    for label, fn, threaded in actions:
        button = QPushButton(label)
        button.clicked.connect(lambda _checked=False, label=label, fn=fn, threaded=threaded: run_action(label, fn, threaded))
        button_row.addWidget(button)
    action_layout.addLayout(button_row)
    action_layout.addWidget(progress)
    action_layout.addWidget(console)

    suggest_btn.clicked.connect(lambda: draw_input.setText(str(controller.suggest_next_draw_from_memory())))
    played_input.textChanged.connect(update_ticket_table)
    analysis_layout.addWidget(data_card)
    analysis_layout.addWidget(tickets_card)
    analysis_layout.addWidget(metric_card)
    analysis_layout.addWidget(action_card)

    # Historial
    history_page = QWidget()
    history_layout = QVBoxLayout(history_page)
    history_layout.addWidget(title("Historial", "Carga resultados locales y revisa el siguiente sorteo sugerido."))
    history_stats, history_stats_layout = card("Estado del historial")
    latest_label = QLabel("Ultimo sorteo: -")
    next_label = QLabel("Siguiente sugerido: -")
    count_label = QLabel("Sorteos cargados: 0")
    history_stats_layout.addWidget(latest_label)
    history_stats_layout.addWidget(next_label)
    history_stats_layout.addWidget(count_label)
    history_buttons = QHBoxLayout()
    import_btn = QPushButton("Importar CSV / resultados.csv")
    reload_btn = QPushButton("Recargar")
    history_buttons.addWidget(import_btn)
    history_buttons.addWidget(reload_btn)
    history_table = QTableWidget()
    history_layout.addWidget(history_stats)
    history_layout.addLayout(history_buttons)
    history_layout.addWidget(history_table)

    def refresh_history() -> None:
        rows = controller.load_history_table()
        display_rows = [
            {"game": row["game"], "draw": row["draw"], "date": row["date"], "numbers": " ".join(map(str, row["numbers"])), "sum": row["sum"], "sum_band": row["sum_band"], "block_signature": row["block_signature"]}
            for row in rows
        ]
        fill_table(history_table, display_rows, ["game", "draw", "date", "numbers", "sum", "sum_band", "block_signature"])
        latest = rows[-1] if rows else None
        latest_label.setText(f"Ultimo sorteo: {latest['draw'] if latest else '-'}")
        next_label.setText(f"Siguiente sugerido: {controller.suggest_next_draw_from_memory()}")
        count_label.setText(f"Sorteos cargados: {len(rows)}")

    import_btn.clicked.connect(lambda: run_action("Import History", choose_import_file, True))
    reload_btn.clicked.connect(refresh_history)

    # Reportes
    reports_page = QWidget()
    reports_layout = QVBoxLayout(reports_page)
    reports_layout.addWidget(title("Reportes", "Archivos HTML, JSON y CSV generados localmente."))
    reports_table = QTableWidget()
    reports_buttons = QHBoxLayout()
    open_selected_btn = QPushButton("Abrir seleccionado")
    open_folder_btn = QPushButton("Abrir carpeta outputs")
    refresh_reports_btn = QPushButton("Recargar reportes")
    for button in [open_selected_btn, open_folder_btn, refresh_reports_btn]:
        reports_buttons.addWidget(button)
    reports_layout.addLayout(reports_buttons)
    reports_layout.addWidget(reports_table)

    def refresh_reports() -> None:
        fill_table(reports_table, controller.list_report_files(), ["name", "type", "path", "modified"])

    def open_selected_report() -> None:
        row = reports_table.currentRow()
        if row < 0:
            QMessageBox.information(window, "MelateApp", "Selecciona un reporte.")
            return
        path_item = reports_table.item(row, 2)
        if path_item:
            controller.open_report(path_item.text())

    open_selected_btn.clicked.connect(open_selected_report)
    open_folder_btn.clicked.connect(lambda: controller.open_outputs_folder())
    refresh_reports_btn.clicked.connect(refresh_reports)

    # Configuracion
    config_page = QWidget()
    config_layout = QVBoxLayout(config_page)
    config_layout.addWidget(title("Configuracion", "Rutas locales, modo de revision y utilidades."))
    config_card, config_card_layout = card("Estado local")
    config_card_layout.addWidget(QLabel(f"Memoria local: {controller.DEFAULT_DB_PATH}" if hasattr(controller, "DEFAULT_DB_PATH") else "Memoria local: data/melate_app_memory.sqlite"))
    config_card_layout.addWidget(QLabel("Outputs: outputs/"))
    config_card_layout.addWidget(QLabel("Modo: review_default"))
    config_layout.addWidget(config_card)

    for page in [analysis_page, history_page, reports_page, config_page]:
        stack.addWidget(page)
    for idx, label in enumerate(["Nuevo analisis", "Historial", "Reportes", "Configuracion"]):
        sidebar_button(label, idx)
    side_layout.addStretch(1)

    root_layout.addWidget(sidebar)
    root_layout.addWidget(stack)
    window.setCentralWidget(root)
    set_active(0)
    update_ticket_table()
    refresh_history()
    refresh_reports()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(launch_desktop())
