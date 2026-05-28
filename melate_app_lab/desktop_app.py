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
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import (
            QApplication,
            QAbstractItemView,
            QButtonGroup,
            QFrame,
            QFileDialog,
            QGridLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QProgressBar,
            QPushButton,
            QSizePolicy,
            QStackedWidget,
            QTableWidget,
            QTableWidgetItem,
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
    window.resize(1240, 800)

    root = QWidget()
    root.setObjectName("AppRoot")
    root_layout = QHBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    sidebar = QFrame()
    sidebar.setObjectName("Sidebar")
    sidebar.setFixedWidth(232)
    sidebar_layout = QVBoxLayout(sidebar)
    sidebar_layout.setContentsMargins(18, 22, 18, 18)
    sidebar_layout.setSpacing(8)

    brand = QLabel("MelateApp\nLab")
    brand.setObjectName("SidebarBrand")
    sidebar_layout.addWidget(brand)

    nav_group = QButtonGroup(window)
    nav_group.setExclusive(True)
    nav_buttons: list[QPushButton] = []

    main = QWidget()
    main.setObjectName("MainSurface")
    main_layout = QVBoxLayout(main)
    main_layout.setContentsMargins(28, 24, 28, 24)
    main_layout.setSpacing(16)

    header_title = QLabel("Nuevo analisis")
    header_title.setObjectName("PageTitle")
    header_subtitle = QLabel("Ejecuta revisiones locales, guarda memoria y genera reportes sin salir del escritorio.")
    header_subtitle.setObjectName("PageSubtitle")
    main_layout.addWidget(header_title)
    main_layout.addWidget(header_subtitle)

    stack = QStackedWidget()
    stack.setObjectName("ContentStack")
    main_layout.addWidget(stack, 1)

    draw_input = QLineEdit()
    result_input = QLineEdit(DEFAULT_RESULT)
    played_input = QTextEdit(DEFAULT_PLAYED)
    console = QPlainTextEdit()
    console.setObjectName("ActivityConsole")
    console.setReadOnly(True)
    progress = QProgressBar()
    progress.setRange(0, 1)
    progress.setValue(0)
    progress.setTextVisible(False)
    qt_runner = QtTaskRunner()
    last_html_report: dict[str, str | None] = {"path": None}

    history_table = QTableWidget(0, 6)
    history_table.setObjectName("DataTable")
    history_table.setHorizontalHeaderLabels(["Sorteo", "Fecha", "Numeros", "Suma", "Banda", "Firma"])
    history_table.verticalHeader().setVisible(False)
    history_table.setAlternatingRowColors(True)
    history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    reports_table = QTableWidget(0, 4)
    reports_table.setObjectName("DataTable")
    reports_table.setHorizontalHeaderLabels(["Sorteo", "JSON", "HTML", "CSV"])
    reports_table.verticalHeader().setVisible(False)
    reports_table.setAlternatingRowColors(True)
    reports_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    reports_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    tickets_table = QTableWidget(0, 6)
    tickets_table.setObjectName("DataTable")
    tickets_table.setHorizontalHeaderLabels(["N1", "N2", "N3", "N4", "N5", "N6"])
    tickets_table.verticalHeader().setVisible(False)
    tickets_table.setAlternatingRowColors(True)
    tickets_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tickets_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tickets_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def log(message: str) -> None:
        console.appendPlainText(message)

    def table_item(value: object) -> QTableWidgetItem:
        item = QTableWidgetItem("" if value is None else str(value))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def selected_report_path(kind: str = "html") -> str | None:
        row = reports_table.currentRow()
        if row < 0:
            return last_html_report["path"] if kind == "html" else None
        column = {"json": 1, "html": 2, "csv": 3}[kind]
        item = reports_table.item(row, column)
        return item.text() if item and item.text() else None

    def refresh_history_table() -> dict[str, object]:
        from .historical_store import load_draw_history

        records = load_draw_history(DEFAULT_DB_PATH)
        history_table.setRowCount(len(records))
        for row, record in enumerate(records):
            numbers = record.get("numbers", [])
            if isinstance(numbers, (list, tuple)):
                numbers_text = " ".join(str(number) for number in numbers)
            else:
                numbers_text = str(numbers)
            values = [
                record.get("draw", ""),
                record.get("date", ""),
                numbers_text,
                record.get("sum", ""),
                record.get("sum_band", ""),
                record.get("block_signature", ""),
            ]
            for column, value in enumerate(values):
                history_table.setItem(row, column, table_item(value))
        
        # Update info cards
        if records:
            ultimo_sorteo = max(int(record.get('draw', 0)) for record in records)
            history_cards["Ultimo sorteo"].setText(f"Ultimo sorteo\n{ultimo_sorteo}")
            history_cards["Sorteos cargados"].setText(f"Sorteos cargados\n{len(records)}")
            next_draw = controller.suggest_next_draw_from_memory(DEFAULT_DB_PATH)
            sug_draw = next_draw.get('next_draw', '-')
            history_cards["Siguiente sugerido"].setText(f"Siguiente sugerido\n{sug_draw}")
        else:
            history_cards["Ultimo sorteo"].setText("Ultimo sorteo\n-")
            history_cards["Sorteos cargados"].setText("Sorteos cargados\n0")
            history_cards["Siguiente sugerido"].setText("Siguiente sugerido\n-")

        return {"history_count": len(records), "memory_path": str(DEFAULT_DB_PATH)}

    def refresh_reports_table() -> dict[str, object]:
        output_dir = Path("outputs")
        stems = sorted({path.stem for path in output_dir.glob("postmortem_*.*")})
        reports_table.setRowCount(len(stems))
        for row, stem in enumerate(stems):
            draw = stem.replace("postmortem_", "")
            paths = {
                "json": output_dir / f"{stem}.json",
                "html": output_dir / f"{stem}.html",
                "csv": output_dir / f"{stem}.csv",
            }
            # format mod time
            values = [
                draw,
                str(paths["json"]) if paths["json"].exists() else "",
                str(paths["html"]) if paths["html"].exists() else "",
                str(paths["csv"]) if paths["csv"].exists() else "",
            ]
            for column, value in enumerate(values):
                reports_table.setItem(row, column, table_item(value))
        return {"reports_count": len(stems), "outputs_path": str(output_dir)}

    def handle_payload(payload: object) -> None:
        log(json.dumps(payload, ensure_ascii=False, indent=2))
        if not isinstance(payload, dict):
            return

        if payload.get("html_path"):
            last_html_report["path"] = str(payload["html_path"])
            refresh_reports_table()
        if payload.get("history_count") is not None or payload.get("imported") is not None:
            refresh_history_table()
            
            # Auto-update the next suggested draw if we are on the analysis page
            if payload.get("suggested_next_draw"):
                draw_input.setText(str(payload["suggested_next_draw"]))

        components = payload.get("components")
        component_payload = components if isinstance(components, dict) else {}
        trace = component_payload.get("trace") if component_payload else payload
        postmortem = component_payload.get("postmortem") if component_payload else payload
        stress = component_payload.get("stress_review") if component_payload else payload
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
        if payload.get("llm_provider"):
            prov = payload["llm_provider"]
            if prov in ("disabled", "local_stub"):
                metric_labels["Analista"].setText(f"Analista\nLocal")
            else:
                metric_labels["Analista"].setText(f"Analista\n{prov}")

    def finish_action(ok: bool = True) -> None:
        progress.setRange(0, 1)
        progress.setValue(1 if ok else 0)
        
        # Re-enable action buttons
        for btn in action_buttons:
            btn.setEnabled(True)

    def handle_error(message: str) -> None:
        log(f"Error: {message}")
        # Don't show QMessageBox from here, it can cause nested event loop issues during thread teardown
        # Instead, just log to the console to ensure QBackingStore issues are avoided.
        finish_action(False)

    def run_action(name: str, fn: Callable[[], object], threaded: bool = False) -> None:
        # Disable buttons to prevent double-clicks
        for btn in action_buttons:
            btn.setEnabled(False)
            
        progress.setRange(0, 0)
        log(f"Ejecutando {name}...")
        
        action_state = {"error": False}
        
        def _on_error(msg: str) -> None:
            action_state["error"] = True
            handle_error(msg)
            
        def _on_finished() -> None:
            finish_action(not action_state["error"])

        if threaded:
            qt_runner.run(
                fn,
                on_log=log,
                on_result=handle_payload,
                on_error=_on_error,
                on_finished=_on_finished,
            )
            return

        # Use QTimer for sync calls to allow the progress bar to go into indeterminate mode visually
        def execute_sync():
            worker_result = run_task_sync(fn, log=log)
            if not worker_result.ok:
                _on_error(worker_result.error or "Error")
            else:
                handle_payload(worker_result.result)
            _on_finished()
                
        QTimer.singleShot(50, execute_sync)
        
    def update_tickets_table() -> None:
        text = played_input.toPlainText()
        try:
            tickets = controller.parse_played_tickets_flexible(text)
            tickets_table.setRowCount(len(tickets))
            for row, ticket in enumerate(tickets):
                for col, num in enumerate(ticket):
                    tickets_table.setItem(row, col, table_item(num))
        except ValueError as e:
            # Just log it, don't crash or show dialog
            log(f"Boletos invalidos: {e}")

    played_input.textChanged.connect(update_tickets_table)

    def open_last_html_report() -> object:
        path = selected_report_path("html") or last_html_report["path"] or str(
            Path("outputs") / f"postmortem_{int(draw_input.text() or 0)}.html"
        )
        return controller.open_report(path)

    def open_selected_json_report() -> object:
        path = selected_report_path("json")
        if not path:
            raise FileNotFoundError("Selecciona un reporte JSON en la tabla.")
        return controller.open_report(path)

    def import_resultados_csv_dialog() -> object:
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            window,
            "Importar resultados.csv",
            str(Path("data") / "samples"),
            "CSV files (*.csv)",
        )
        if not file_path:
            return {"imported": 0, "message": "Importacion cancelada."}
            
        from .resultados_importer import import_resultados_csv_to_memory
        return import_resultados_csv_to_memory(file_path, DEFAULT_DB_PATH)

    def suggest_next() -> None:
        try:
            res = controller.suggest_next_draw_from_memory(DEFAULT_DB_PATH)
            draw_input.setText(str(res.get("next_draw", 4218)))
        except Exception as e:
            log(f"Error sugiriendo sorteo: {e}")

    def make_page() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        return page, layout

    action_buttons = []

    # ANALYSIS PAGE
    analysis_page, analysis_layout = make_page()
    form_panel = QFrame()
    form_panel.setObjectName("Panel")
    form_layout = QGridLayout(form_panel)
    form_layout.setContentsMargins(18, 18, 18, 18)
    form_layout.setHorizontalSpacing(16)
    form_layout.setVerticalSpacing(12)
    
    draw_box = QHBoxLayout()
    draw_box.addWidget(draw_input)
    suggest_btn = QPushButton("Sugerir siguiente")
    suggest_btn.clicked.connect(suggest_next)
    draw_box.addWidget(suggest_btn)
    
    form_layout.addWidget(QLabel("Sorteo"), 0, 0)
    form_layout.addLayout(draw_box, 0, 1)
    form_layout.addWidget(QLabel("Resultado"), 1, 0)
    form_layout.addWidget(result_input, 1, 1)
    form_layout.addWidget(QLabel("Boletos jugados\n(multilinea o separados por espacio)"), 2, 0, alignment=Qt.AlignTop)
    
    tickets_splitter = QVBoxLayout()
    tickets_splitter.addWidget(played_input)
    tickets_splitter.addWidget(QLabel("Boletos parseados:"))
    tickets_splitter.addWidget(tickets_table)
    
    form_layout.addLayout(tickets_splitter, 2, 1)
    form_layout.setColumnStretch(1, 1)
    analysis_layout.addWidget(form_panel)

    metrics = QGridLayout()
    metrics.setSpacing(12)
    metric_labels = {}
    for index, name in enumerate(["Capturados", "No capturados", "Suma", "Banda", "Firma", "Anclas", "Alertas", "Analista"]):
        card = QLabel(f"{name}\n-")
        card.setObjectName("MetricCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        metric_labels[name] = card
        metrics.addWidget(card, index // 4, index % 4)
    analysis_layout.addLayout(metrics)

    button_panel = QFrame()
    button_panel.setObjectName("Panel")
    button_row = QHBoxLayout(button_panel)
    button_row.setContentsMargins(14, 14, 14, 14)
    button_row.setSpacing(10)
    actions = [
        ("Trace", lambda: controller.run_trace(int(draw_input.text() or 0), result_input.text()), False),
        (
            "Postmortem",
            lambda: controller.run_postmortem(int(draw_input.text() or 0), result_input.text(), played_input.toPlainText()),
            False,
        ),
        ("Stress Review", lambda: controller.run_stress(result_input.text(), played_input.toPlainText()), True),
        (
            "Brain Review",
            lambda: controller.run_brain(int(draw_input.text() or 0), result_input.text(), played_input.toPlainText()),
            True,
        ),
        (
            "Remember",
            lambda: controller.run_remember(int(draw_input.text() or 0), result_input.text(), played_input.toPlainText()),
            False,
        ),
        (
            "Generate Report",
            lambda: controller.run_report(int(draw_input.text() or 0), result_input.text(), played_input.toPlainText()),
            False,
        ),
    ]
    for label, fn, threaded in actions:
        button = QPushButton(label)
        button.clicked.connect(lambda _checked=False, label=label, fn=fn, threaded=threaded: run_action(label, fn, threaded))
        button_row.addWidget(button)
        action_buttons.append(button)
    analysis_layout.addWidget(button_panel)
    analysis_layout.addWidget(progress)
    analysis_layout.addWidget(QLabel("Consola interna"))
    analysis_layout.addWidget(console, 1)

    # HISTORY PAGE
    history_page, history_layout = make_page()
    history_cards_layout = QHBoxLayout()
    history_cards_layout.setSpacing(12)
    history_cards = {}
    for name in ["Ultimo sorteo", "Siguiente sugerido", "Sorteos cargados"]:
        card = QLabel(f"{name}\n-")
        card.setObjectName("MetricCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        history_cards[name] = card
        history_cards_layout.addWidget(card)
    history_layout.addLayout(history_cards_layout)
        
    history_actions = QHBoxLayout()
    import_res_button = QPushButton("Importar resultados.csv")
    refresh_history_button = QPushButton("Actualizar tabla")
    summarize_history_button = QPushButton("Resumen historico")
    
    import_res_button.clicked.connect(lambda: run_action("Importar resultados", import_resultados_csv_dialog, True))
    refresh_history_button.clicked.connect(lambda: run_action("Actualizar historial", refresh_history_table, False))
    summarize_history_button.clicked.connect(
        lambda: run_action("Resumen historico", lambda: controller.run_history_summary(DEFAULT_DB_PATH), False)
    )
    history_actions.addWidget(import_res_button)
    history_actions.addWidget(refresh_history_button)
    history_actions.addWidget(summarize_history_button)
    history_actions.addStretch(1)
    
    action_buttons.extend([import_res_button, refresh_history_button, summarize_history_button])
    
    history_layout.addLayout(history_actions)
    history_layout.addWidget(history_table, 1)

    # REPORTS PAGE
    reports_page, reports_layout = make_page()
    reports_actions = QHBoxLayout()
    refresh_reports_button = QPushButton("Actualizar tabla")
    open_folder_button = QPushButton("Abrir outputs")
    open_html_button = QPushButton("Abrir HTML")
    open_json_button = QPushButton("Abrir JSON")
    
    refresh_reports_button.clicked.connect(lambda: run_action("Actualizar reportes", refresh_reports_table, False))
    open_folder_button.clicked.connect(lambda: run_action("Abrir carpeta", controller.open_outputs_folder, False))
    open_html_button.clicked.connect(lambda: run_action("Abrir HTML", open_last_html_report, False))
    open_json_button.clicked.connect(lambda: run_action("Abrir JSON", open_selected_json_report, False))
    
    reports_actions.addWidget(refresh_reports_button)
    reports_actions.addWidget(open_folder_button)
    reports_actions.addWidget(open_html_button)
    reports_actions.addWidget(open_json_button)
    reports_actions.addStretch(1)
    
    action_buttons.extend([refresh_reports_button, open_folder_button, open_html_button, open_json_button])
    
    reports_layout.addLayout(reports_actions)
    reports_layout.addWidget(reports_table, 1)

    # SETTINGS PAGE
    settings_page, settings_layout = make_page()
    settings_panel = QFrame()
    settings_panel.setObjectName("Panel")
    settings_grid = QGridLayout(settings_panel)
    settings_grid.setContentsMargins(18, 18, 18, 18)
    settings_grid.setHorizontalSpacing(16)
    settings_grid.setVerticalSpacing(12)
    settings_grid.addWidget(QLabel("Memoria local"), 0, 0)
    settings_grid.addWidget(QLabel(str(DEFAULT_DB_PATH)), 0, 1)
    settings_grid.addWidget(QLabel("Carpeta de reportes"), 1, 0)
    settings_grid.addWidget(QLabel(str(Path("outputs").resolve())), 1, 1)
    settings_grid.addWidget(QLabel("Modo de revision"), 2, 0)
    settings_grid.addWidget(QLabel("review_default (Guardrails activos)"), 2, 1)
    
    from .llm_provider import get_llm_config
    llm_cfg = get_llm_config()
    settings_grid.addWidget(QLabel("Estado LLM"), 3, 0)
    settings_grid.addWidget(QLabel(llm_cfg["provider"]), 3, 1)
    settings_grid.addWidget(QLabel("Modelo LLM"), 4, 0)
    settings_grid.addWidget(QLabel(llm_cfg["model"]), 4, 1)
    settings_grid.addWidget(QLabel("Base URL LLM"), 5, 0)
    settings_grid.addWidget(QLabel(llm_cfg["base_url"] or "-"), 5, 1)
    
    init_memory_button = QPushButton("Inicializar memoria")
    validate_config_button = QPushButton("Guardrail Scan")
    build_info_button = QPushButton("Build Info")
    test_llm_button = QPushButton("Test analista LLM")
    
    init_memory_button.clicked.connect(
        lambda: run_action("Inicializar memoria", lambda: controller.initialize_memory(DEFAULT_DB_PATH), False)
    )
    validate_config_button.clicked.connect(
        lambda: run_action("Guardrail scan", lambda: controller.run_guardrail_scan(), False)
    )
    build_info_button.clicked.connect(
        lambda: run_action("Build info", lambda: controller.get_build_info(), False)
    )
    test_llm_button.clicked.connect(
        lambda: run_action("Test LLM", lambda: controller.test_llm_connection(), True)
    )
    
    action_row = QHBoxLayout()
    action_row.addWidget(init_memory_button)
    action_row.addWidget(validate_config_button)
    action_row.addWidget(build_info_button)
    action_row.addWidget(test_llm_button)
    action_row.addStretch()
    
    action_buttons.extend([init_memory_button, validate_config_button, build_info_button, test_llm_button])
    
    settings_grid.addLayout(action_row, 6, 0, 1, 2)
    settings_grid.setColumnStretch(1, 1)
    settings_layout.addWidget(settings_panel)
    settings_layout.addStretch(1)

    pages = [
        ("Nuevo analisis", "Ejecuta revisiones locales, guarda memoria y genera reportes sin salir del escritorio.", analysis_page),
        ("Historial", "Importa sorteos previos y revisa la memoria local en tabla.", history_page),
        ("Reportes", "Consulta archivos exportados y abre reportes generados.", reports_page),
        ("Configuracion", "Rutas y tareas operativas para el laboratorio local.", settings_page),
    ]

    def show_page(index: int) -> None:
        title, subtitle, _page = pages[index]
        header_title.setText(title)
        header_subtitle.setText(subtitle)
        stack.setCurrentIndex(index)
        if title == "Historial":
            run_action("Actualizar historial", refresh_history_table, False)
        elif title == "Reportes":
            run_action("Actualizar reportes", refresh_reports_table, False)

    for index, (label, _subtitle, page) in enumerate(pages):
        nav_button = QPushButton(label)
        nav_button.setObjectName("SidebarButton")
        nav_button.setCheckable(True)
        nav_button.clicked.connect(lambda _checked=False, index=index: show_page(index))
        nav_group.addButton(nav_button, index)
        nav_buttons.append(nav_button)
        sidebar_layout.addWidget(nav_button)
        stack.addWidget(page)

    sidebar_layout.addStretch(1)
    nav_buttons[0].setChecked(True)
    refresh_reports_table()
    update_tickets_table()
    
    # Init next draw
    suggest_next()

    root_layout.addWidget(sidebar)
    root_layout.addWidget(main, 1)
    window.setCentralWidget(root)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(launch_desktop())

