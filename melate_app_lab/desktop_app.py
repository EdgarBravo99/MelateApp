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
            QCheckBox,
            QComboBox,
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

    class MainWindow(QMainWindow):
        def closeEvent(self, event) -> None:
            try:
                log("Cerrando aplicacion y deteniendo hilos...")
                qt_runner.stop_all()
            except Exception:
                pass
            event.accept()

    window = MainWindow()
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

        if payload.get("report_text") and "candidates" in payload:
            candidates_output.setPlainText(payload["report_text"])

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

    def run_action(
        name: str,
        fn: Callable[[], object],
        threaded: bool = False,
        on_done: Callable[[Any], None] | None = None,
        on_log_cb: Callable[[str], None] | None = None,
    ) -> None:
        # Disable buttons to prevent double-clicks
        for btn in action_buttons:
            btn.setEnabled(False)
            
        progress.setRange(0, 0)
        log(f"Ejecutando {name}...")
        
        action_state = {"error": False}
        
        def _on_error(msg: str) -> None:
            action_state["error"] = True
            handle_error(msg)
            if on_log_cb:
                on_log_cb(f"Error: {msg}")
            
        def _on_finished() -> None:
            finish_action(not action_state["error"])

        def _on_log(msg: str) -> None:
            log(msg)
            if on_log_cb:
                on_log_cb(msg)

        def _on_result(res: Any) -> None:
            if on_done:
                try:
                    on_done(res)
                except Exception as e:
                    _on_error(str(e))
            else:
                handle_payload(res)

        if threaded:
            qt_runner.run(
                fn,
                on_log=_on_log,
                on_result=_on_result,
                on_error=_on_error,
                on_finished=_on_finished,
            )
            return

        # Use QTimer for sync calls to allow the progress bar to go into indeterminate mode visually
        def execute_sync():
            worker_result = run_task_sync(fn, log=_on_log)
            if not worker_result.ok:
                _on_error(worker_result.error or "Error")
            else:
                _on_result(worker_result.result)
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

    def start_import_csv_workflow() -> None:
        """Open file dialog in UI thread, then run import in worker thread."""
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            window,
            "Importar resultados.csv",
            str(Path("data") / "samples"),
            "CSV files (*.csv)",
        )
        if not file_path:
            log("Importacion cancelada por el usuario.")
            return

        def _do_import() -> object:
            from .resultados_importer import import_resultados_csv_to_memory
            return import_resultados_csv_to_memory(file_path, DEFAULT_DB_PATH)

        run_action("Importar resultados", _do_import, threaded=True)

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
    def get_draw() -> int:
        try:
            return int(draw_input.text() or 0)
        except ValueError:
            raise ValueError("El sorteo debe ser un numero entero.")

    def validate_inputs(require_draw=True, require_result=True, require_played=True):
        draw = 0
        if require_draw:
            draw = get_draw()
        
        result_text = result_input.text()
        if require_result:
            try:
                controller.parse_ticket(result_text)
            except ValueError as e:
                raise ValueError(f"Resultado invalido: {e}")
                
        played_text = played_input.toPlainText()
        if require_played:
            try:
                controller.parse_played_tickets_flexible(played_text)
            except ValueError as e:
                raise ValueError(f"Boletos jugados invalidos: {e}")
                
        return draw, result_text, played_text

    def start_trace():
        try:
            draw, result_text, _ = validate_inputs(require_played=False)
            run_action("Trace", lambda: controller.run_trace(draw, result_text), False)
        except Exception as e:
            log(f"Error: {e}")

    def start_postmortem():
        try:
            draw, result_text, played_text = validate_inputs()
            run_action("Postmortem", lambda: controller.run_postmortem(draw, result_text, played_text), True)
        except Exception as e:
            log(f"Error: {e}")

    def start_stress_review():
        try:
            _, result_text, played_text = validate_inputs(require_draw=False)
            run_action("Stress Review", lambda: controller.run_stress(result_text, played_text), True)
        except Exception as e:
            log(f"Error: {e}")

    def start_brain_review():
        try:
            draw, result_text, played_text = validate_inputs()
            run_action("Brain Review", lambda: controller.run_brain(draw, result_text, played_text), True)
        except Exception as e:
            log(f"Error: {e}")

    def start_remember():
        try:
            draw, result_text, played_text = validate_inputs()
            run_action("Remember", lambda: controller.run_remember(draw, result_text, played_text), True)
        except Exception as e:
            log(f"Error: {e}")

    def start_generate_report():
        try:
            draw, result_text, played_text = validate_inputs()
            run_action("Generate Report", lambda: controller.run_report(draw, result_text, played_text), True)
        except Exception as e:
            log(f"Error: {e}")

    def start_graph_visualization():
        try:
            draw, result_text, played_text = validate_inputs()
            run_action("Ver Grafo", lambda: controller.run_graph_visualization(draw, result_text, played_text), True)
        except Exception as e:
            log(f"Error: {e}")

    def start_revision_completa():
        try:
            draw_text = draw_input.text().strip()
            draw = int(draw_text) if draw_text else None
            run_action("Revisión Completa", lambda: controller.run_revision_completa(DEFAULT_DB_PATH, count=10, game="revancha", draw=draw), True)
        except Exception as e:
            log(f"Error: {e}")

    actions_config = [
        ("Revisión Completa", start_revision_completa),
        ("Trace", start_trace),
        ("Postmortem", start_postmortem),
        ("Stress Review", start_stress_review),
        ("Brain Review", start_brain_review),
        ("Remember", start_remember),
        ("Generate Report", start_generate_report),
        ("Ver Grafo", start_graph_visualization),
    ]
    for label, fn in actions_config:
        button = QPushButton(label)
        button.clicked.connect(fn)
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
    dashboard_button = QPushButton("Generar Dashboard Visual")
    historical_graph_button = QPushButton("Ver Grafo Historico")
    
    import_res_button.clicked.connect(start_import_csv_workflow)
    refresh_history_button.clicked.connect(lambda: run_action("Actualizar historial", refresh_history_table, False))
    summarize_history_button.clicked.connect(
        lambda: run_action("Resumen historico", lambda: controller.run_history_summary(DEFAULT_DB_PATH), False)
    )
    dashboard_button.clicked.connect(
        lambda: run_action("Generar Dashboard", lambda: controller.run_history_dashboard(DEFAULT_DB_PATH), False)
    )
    historical_graph_button.clicked.connect(
        lambda: run_action("Ver Grafo Historico", lambda: controller.run_historical_graph(DEFAULT_DB_PATH), True)
    )
    history_actions.addWidget(import_res_button)
    history_actions.addWidget(refresh_history_button)
    history_actions.addWidget(summarize_history_button)
    history_actions.addWidget(dashboard_button)
    history_actions.addWidget(historical_graph_button)
    history_actions.addStretch(1)
    
    action_buttons.extend([import_res_button, refresh_history_button, summarize_history_button, dashboard_button, historical_graph_button])
    
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

    # CANDIDATES PAGE
    candidates_page, candidates_layout = make_page()
    cand_panel = QFrame()
    cand_panel.setObjectName("Panel")
    cand_panel_layout = QHBoxLayout(cand_panel)
    cand_panel_layout.setContentsMargins(14, 14, 14, 14)
    cand_panel_layout.setSpacing(10)
    
    cand_count_select = QComboBox()
    cand_count_select.addItems(["10", "20", "50"])
    
    generate_cand_btn = QPushButton("Generar Tesis y Candidatos")
    
    def start_generate_candidates():
        try:
            count = int(cand_count_select.currentText())
            run_action("Generar Candidatos", lambda: controller.run_generate_candidates(DEFAULT_DB_PATH, count), True)
        except Exception as e:
            log(f"Error: {e}")
            
    generate_cand_btn.clicked.connect(start_generate_candidates)
    
    cand_panel_layout.addWidget(QLabel("Combinaciones a generar:"))
    cand_panel_layout.addWidget(cand_count_select)
    cand_panel_layout.addWidget(generate_cand_btn)
    cand_panel_layout.addStretch()
    
    action_buttons.extend([generate_cand_btn])
    
    candidates_output = QPlainTextEdit()
    candidates_output.setObjectName("ActivityConsole")
    candidates_output.setReadOnly(True)
    
    candidates_layout.addWidget(cand_panel)
    candidates_layout.addWidget(QLabel("Resultados de Tesis y Candidatos:"))
    candidates_layout.addWidget(candidates_output, 1)

    # PORTFOLIO PAGE
    portfolio_page, portfolio_layout = make_page()

    portfolio_splitter = QHBoxLayout()
    portfolio_splitter.setSpacing(16)

    # Left side panel: Portfolios
    left_panel = QFrame()
    left_panel.setObjectName("Panel")
    left_layout = QVBoxLayout(left_panel)
    left_layout.addWidget(QLabel("Historial de Carteras Generadas:"))

    portfolios_table = QTableWidget(0, 4)
    portfolios_table.setObjectName("DataTable")
    portfolios_table.setHorizontalHeaderLabels(["ID", "Sorteo", "Juego", "Fecha"])
    portfolios_table.verticalHeader().setVisible(False)
    portfolios_table.setAlternatingRowColors(True)
    portfolios_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    portfolios_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    portfolios_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    left_layout.addWidget(portfolios_table, 1)

    refresh_portfolios_btn = QPushButton("Actualizar Lista")
    left_layout.addWidget(refresh_portfolios_btn)

    portfolio_splitter.addWidget(left_panel, 2)

    # Right side panel: Candidates in Portfolio
    right_panel = QFrame()
    right_panel.setObjectName("Panel")
    right_layout = QVBoxLayout(right_panel)
    right_layout.addWidget(QLabel("Candidatos del Portfolio Seleccionado:"))

    portfolio_candidates_table = QTableWidget(0, 7)
    portfolio_candidates_table.setObjectName("DataTable")
    portfolio_candidates_table.setHorizontalHeaderLabels(["ID", "Letra", "Números", "Perfil", "Soporte", "Estado", "Aciertos"])
    portfolio_candidates_table.verticalHeader().setVisible(False)
    portfolio_candidates_table.setAlternatingRowColors(True)
    portfolio_candidates_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    portfolio_candidates_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    portfolio_candidates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    right_layout.addWidget(portfolio_candidates_table, 1)

    # Candidate control bar
    candidate_actions = QHBoxLayout()
    state_combo = QComboBox()
    state_combo.addItems(["Pendiente", "Favorito", "Jugado", "Descartado"])
    change_state_btn = QPushButton("Cambiar Estado")

    eval_portfolio_btn = QPushButton("Probar contra Histórico")
    eval_portfolio_btn.setObjectName("PrimaryAction")
    view_portfolio_report_btn = QPushButton("Ver Reporte de Cartera")

    candidate_actions.addWidget(QLabel("Estado:"))
    candidate_actions.addWidget(state_combo)
    candidate_actions.addWidget(change_state_btn)
    candidate_actions.addWidget(eval_portfolio_btn)
    candidate_actions.addWidget(view_portfolio_report_btn)
    candidate_actions.addStretch(1)

    right_layout.addLayout(candidate_actions)

    # Feedback learning panel
    feedback_frame = QFrame()
    feedback_frame.setObjectName("Panel")
    feedback_frame.setStyleSheet("margin-top: 10px; padding: 10px; border: 1px solid #3d3d3d; border-radius: 6px;")
    feedback_layout = QVBoxLayout(feedback_frame)
    feedback_layout.setContentsMargins(10, 10, 10, 10)
    feedback_layout.setSpacing(6)

    feedback_header = QLabel("Aprendizaje y Recalibración Estructural:")
    feedback_header.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
    feedback_layout.addWidget(feedback_header)

    profile_info_label = QLabel("Perfil de Feedback Activo: Ninguno (Usando pesos heurísticos baseline)")
    profile_info_label.setStyleSheet("color: #aaaaaa;")
    profile_info_label.setWordWrap(True)
    feedback_layout.addWidget(profile_info_label)

    learn_buttons_layout = QHBoxLayout()
    learn_btn = QPushButton("Aprender de Historial (learn-feedback)")
    learn_btn.setObjectName("PrimaryAction")
    learn_buttons_layout.addWidget(learn_btn)
    learn_buttons_layout.addStretch(1)
    feedback_layout.addLayout(learn_buttons_layout)

    right_layout.addWidget(feedback_frame)

    portfolio_splitter.addWidget(right_panel, 3)
    portfolio_layout.addLayout(portfolio_splitter)

    action_buttons.extend([refresh_portfolios_btn, change_state_btn, eval_portfolio_btn, view_portfolio_report_btn, learn_btn])

    def refresh_portfolios():
        try:
            records = controller.load_portfolios_list(DEFAULT_DB_PATH)
            portfolios_table.setRowCount(len(records))
            for row, record in enumerate(records):
                portfolios_table.setItem(row, 0, table_item(record["id"]))
                portfolios_table.setItem(row, 1, table_item(record["draw"]))
                portfolios_table.setItem(row, 2, table_item(record["game"]))
                portfolios_table.setItem(row, 3, table_item(record["created_at"]))

            portfolio_candidates_table.setRowCount(0)
        except Exception as e:
            log(f"Error cargando carteras: {e}")

    def on_portfolio_selected():
        row = portfolios_table.currentRow()
        if row < 0:
            return
        try:
            pid = int(portfolios_table.item(row, 0).text())
            refresh_candidates(pid)
        except Exception as e:
            log(f"Error cargando candidatos: {e}")

    def refresh_candidates(pid: int):
        try:
            cands = controller.load_portfolio_candidates(DEFAULT_DB_PATH, pid)
            portfolio_candidates_table.setRowCount(len(cands))
            for row, cand in enumerate(cands):
                portfolio_candidates_table.setItem(row, 0, table_item(cand["id"]))
                letter = cand.get("letter") or chr(ord('A') + row)
                portfolio_candidates_table.setItem(row, 1, table_item(letter))
                nums_text = " ".join(str(n) for n in cand["numbers"])
                portfolio_candidates_table.setItem(row, 2, table_item(nums_text))
                portfolio_candidates_table.setItem(row, 3, table_item(cand["classification"]))
                portfolio_candidates_table.setItem(row, 4, table_item(cand["graph_support_score"]))
                portfolio_candidates_table.setItem(row, 5, table_item(cand["state"]))

                hits = cand.get("hits_count")
                hits_str = str(hits) if hits is not None else "-"
                portfolio_candidates_table.setItem(row, 6, table_item(hits_str))
        except Exception as e:
            log(f"Error cargando candidatos: {e}")

    portfolios_table.itemSelectionChanged.connect(on_portfolio_selected)
    refresh_portfolios_btn.clicked.connect(refresh_portfolios)

    def change_state_clicked():
        row = portfolio_candidates_table.currentRow()
        if row < 0:
            QMessageBox.warning(window, "Advertencia", "Selecciona un candidato de la tabla.")
            return
        try:
            cand_id = int(portfolio_candidates_table.item(row, 0).text())
            new_state = state_combo.currentText()
            controller.change_candidate_state(DEFAULT_DB_PATH, cand_id, new_state)
            log(f"Estado de candidato {cand_id} cambiado a {new_state}.")

            p_row = portfolios_table.currentRow()
            if p_row >= 0:
                pid = int(portfolios_table.item(p_row, 0).text())
                refresh_candidates(pid)
        except Exception as e:
            log(f"Error al cambiar estado: {e}")

    change_state_btn.clicked.connect(change_state_clicked)

    def eval_portfolio_clicked():
        row = portfolios_table.currentRow()
        if row < 0:
            QMessageBox.warning(window, "Advertencia", "Selecciona una cartera de la tabla de carteras.")
            return
        try:
            pid = int(portfolios_table.item(row, 0).text())
            draw = int(portfolios_table.item(row, 1).text())
            game = portfolios_table.item(row, 2).text()

            # Intentar evaluar contra historial primero
            res = controller.evaluate_portfolio_against_history(DEFAULT_DB_PATH, pid)
            if res.get("evaluated", 0) > 0:
                QMessageBox.information(window, "Evaluación Completa", res.get("message", "Evaluado con éxito."))
                refresh_candidates(pid)
                return

            # Si no esta en el historial, pedir entrada manual
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(
                window,
                "Sorteo no encontrado",
                f"El sorteo {draw} no está en el historial.\n"
                f"Introduce los 6 números ganadores oficiales separados por espacios:"
            )
            if ok and text.strip():
                def run_eval_manual():
                    return controller.run_evaluate_portfolio(DEFAULT_DB_PATH, pid, text, game)

                def on_eval_manual_done(res_manual):
                    QMessageBox.information(
                        window,
                        "Evaluación Completa",
                        f"Cartera evaluada contra resultado manual: {res_manual['result_numbers']}"
                    )
                    refresh_candidates(pid)

                run_action("Probar Cartera Manual", run_eval_manual, True, on_eval_manual_done)
        except Exception as e:
            log(f"Error al evaluar cartera: {e}")

    eval_portfolio_btn.clicked.connect(eval_portfolio_clicked)

    def view_portfolio_report_clicked():
        row = portfolios_table.currentRow()
        if row < 0:
            QMessageBox.warning(window, "Advertencia", "Selecciona una cartera de la tabla de carteras.")
            return
        try:
            pid = int(portfolios_table.item(row, 0).text())
            draw = int(portfolios_table.item(row, 1).text())
            report_path = Path("outputs") / f"portfolio_report_{draw}.html"
            if report_path.exists():
                controller.open_report(report_path)
            else:
                cands = controller.load_portfolio_candidates(DEFAULT_DB_PATH, pid)
                from .thesis_memory import load_thesis_portfolios
                ports = controller.load_portfolios_list(DEFAULT_DB_PATH)
                port = next((p for p in ports if p["id"] == pid), None)
                if not port:
                    raise ValueError("Portfolio no encontrado.")
                from .number_utils import analyze_portfolio_redundancy
                redundancy = analyze_portfolio_redundancy(cands)
                from .report_writer import write_consolidated_portfolio_report_html
                write_consolidated_portfolio_report_html(port, cands, redundancy, report_path)
                controller.open_report(report_path)
                log(f"Reporte de cartera generado y abierto en {report_path}.")
        except Exception as e:
            log(f"Error al abrir reporte de cartera: {e}")

    view_portfolio_report_btn.clicked.connect(view_portfolio_report_clicked)

    def update_profile_info():
        try:
            p_row = portfolios_table.currentRow()
            if p_row >= 0:
                game = portfolios_table.item(p_row, 2).text()
            else:
                game = "revancha"
            info = controller.load_active_profile_info(DEFAULT_DB_PATH, game)
            if info:
                metrics = info["metrics"]
                profile_info_label.setText(
                    f"Perfil ID: {info['id']} | Sorteos: {info['source_from_draw']} - {info['source_to_draw']} | "
                    f"Baseline Score: {metrics.get('baseline_score')} | Optimized: {metrics.get('best_score')} "
                    f"({info['algorithm']})"
                )
            else:
                profile_info_label.setText("Perfil de Feedback Activo: Ninguno (Usando pesos heurísticos baseline)")
        except Exception as e:
            log(f"Error cargando informacion del perfil: {e}")

    def learn_btn_clicked():
        p_row = portfolios_table.currentRow()
        game = portfolios_table.item(p_row, 2).text() if p_row >= 0 else "revancha"

        def run_learn():
            return controller.run_learn_feedback(DEFAULT_DB_PATH, game=game)

        def on_learn_done(res):
            if res.get("success"):
                QMessageBox.information(
                    window,
                    "Aprendizaje Completo",
                    f"Procesadas {res['reviewed_count']} carteras revisadas.\n"
                    f"Estado del Perfil: {res['status']}\n"
                    f"¿Activado automáticamente?: {'Sí' if res['activated'] else 'No'}\n"
                    f"Score Optimizado: {res['optimized_score']} (Baseline: {res['baseline_score']})"
                )
                update_profile_info()
            else:
                QMessageBox.warning(window, "Aprendizaje", res.get("message", "No se pudo completar el aprendizaje."))

        run_action("Ejecutando aprendizaje", run_learn, True, on_learn_done)

    learn_btn.clicked.connect(learn_btn_clicked)

    # Conectar update_profile_info a cambios de seleccion y actualizaciones
    portfolios_table.itemSelectionChanged.connect(update_profile_info)
    refresh_portfolios_btn.clicked.connect(update_profile_info)

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

    # BACKTEST PAGE
    backtest_page, backtest_layout = make_page()
    backtest_panel = QFrame()
    backtest_panel.setObjectName("Panel")
    backtest_grid = QGridLayout(backtest_panel)
    backtest_grid.setContentsMargins(18, 18, 18, 18)
    backtest_grid.setHorizontalSpacing(16)
    backtest_grid.setVerticalSpacing(12)

    backtest_game_combo = QComboBox()
    backtest_game_combo.addItems(["revancha", "melate"])

    backtest_limit_combo = QComboBox()
    backtest_limit_combo.addItems(["10", "20", "50", "100"])

    backtest_pool_combo = QComboBox()
    backtest_pool_combo.addItems(["100", "200", "500"])

    backtest_seed_input = QLineEdit("42")
    
    backtest_ml_check = QCheckBox("Usar Machine Learning (Ridge Regression)")
    if not controller.is_ml_supported():
        backtest_ml_check.setEnabled(False)
        backtest_ml_check.setToolTip("Instala scikit-learn para habilitar el ranking ML.")

    run_backtest_btn = QPushButton("Ejecutar Backtesting Estructural")
    run_backtest_btn.setObjectName("PrimaryAction")
    
    open_backtest_report_btn = QPushButton("Ver Reporte de Backtest")
    open_backtest_report_btn.setEnabled(False)

    backtest_grid.addWidget(QLabel("Juego:"), 0, 0)
    backtest_grid.addWidget(backtest_game_combo, 0, 1)
    backtest_grid.addWidget(QLabel("Sorteos a evaluar:"), 1, 0)
    backtest_grid.addWidget(backtest_limit_combo, 1, 1)
    backtest_grid.addWidget(QLabel("Tamaño del pool:"), 2, 0)
    backtest_grid.addWidget(backtest_pool_combo, 2, 1)
    backtest_grid.addWidget(QLabel("Semilla aleatoria:"), 3, 0)
    backtest_grid.addWidget(backtest_seed_input, 3, 1)
    backtest_grid.addWidget(backtest_ml_check, 4, 0, 1, 2)
    
    backtest_actions = QHBoxLayout()
    backtest_actions.addWidget(run_backtest_btn)
    backtest_actions.addWidget(open_backtest_report_btn)
    backtest_actions.addStretch()
    backtest_grid.addLayout(backtest_actions, 5, 0, 1, 2)
    backtest_grid.setColumnStretch(1, 1)

    backtest_output = QPlainTextEdit()
    backtest_output.setObjectName("ActivityConsole")
    backtest_output.setReadOnly(True)

    backtest_layout.addWidget(backtest_panel)
    backtest_layout.addWidget(QLabel("Métricas de Evaluación Retrospectiva:"))
    backtest_layout.addWidget(backtest_output, 1)

    action_buttons.extend([run_backtest_btn, open_backtest_report_btn])

    last_backtest_report_path: dict[str, str | None] = {"path": None}

    def start_backtest():
        try:
            backtest_output.clear()
            game = backtest_game_combo.currentText()
            limit = int(backtest_limit_combo.currentText())
            pool_size = int(backtest_pool_combo.currentText())
            seed = int(backtest_seed_input.text())
            use_ml = backtest_ml_check.isChecked()

            def run_b():
                return controller.run_backtest_lab(
                    DEFAULT_DB_PATH,
                    limit=limit,
                    game=game,
                    pool_size=pool_size,
                    top_k=10,
                    seed=seed,
                    use_ml=use_ml,
                )

            def on_b_done(res):
                last_backtest_report_path["path"] = res.get("html_path")
                open_backtest_report_btn.setEnabled(True)
                
                metrics = res.get("metrics", {})
                summary_text = (
                    f"BACKTESTING COMPLETADO ({game.upper()})\n"
                    f"===================================\n"
                    f"Sorteos evaluados: {metrics.get('draws_evaluated', 0)}\n\n"
                    f"--- Métricas del Ranker Estructural ---\n"
                    f"Promedio Máximo Aciertos (Top 10): {metrics.get('avg_ranker_top_k_max_hits', 0.0)}\n"
                    f"Promedio Medio Aciertos (Top 10): {metrics.get('avg_ranker_top_k_mean_hits', 0.0)}\n"
                    f"Tasa >= 3 Aciertos: {metrics.get('ranker_3plus_rate', 0.0)}%\n"
                    f"Tasa >= 4 Aciertos: {metrics.get('ranker_4plus_rate', 0.0)}%\n\n"
                    f"--- Métricas del Baseline Aleatorio ---\n"
                    f"Promedio Máximo Aciertos (Top 10): {metrics.get('avg_baseline_top_k_max_hits', 0.0)}\n"
                    f"Promedio Medio Aciertos (Top 10): {metrics.get('avg_baseline_top_k_mean_hits', 0.0)}\n"
                    f"Tasa >= 3 Aciertos: {metrics.get('baseline_3plus_rate', 0.0)}%\n"
                    f"Tasa >= 4 Aciertos: {metrics.get('baseline_4plus_rate', 0.0)}%\n"
                )
                backtest_output.setPlainText(summary_text)
                log(f"Backtesting completado para los últimos {limit} sorteos.")

            run_action(
                "Ejecutar Backtest",
                run_b,
                threaded=True,
                on_done=on_b_done,
                on_log_cb=backtest_output.appendPlainText,
            )
        except Exception as e:
            log(f"Error: {e}")

    run_backtest_btn.clicked.connect(start_backtest)
    open_backtest_report_btn.clicked.connect(lambda: controller.open_report(last_backtest_report_path["path"]))

    pages = [
        ("Nuevo analisis", "Ejecuta revisiones locales, guarda memoria y genera reportes sin salir del escritorio.", analysis_page),
        ("Historial", "Importa sorteos previos y revisa la memoria local en tabla.", history_page),
        ("Candidatos", "Genera combinaciones candidatas y tesis analitica basada en historial.", candidates_page),
        ("Cartera de Tesis", "Administra las tesis guardadas y evalúa aciertos retrospectivamente.", portfolio_page),
        ("ML Lab & Backtest", "Ejecuta evaluaciones retrospectivas contra el historial descriptivo.", backtest_page),
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
        elif title == "Cartera de Tesis":
            run_action("Actualizar carteras", refresh_portfolios, False)

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

