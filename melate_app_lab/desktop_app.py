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
            QSplitter,
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
            val = str(res.get("next_draw", 4218))
            draw_input.setText(val)
            try:
                cockpit_draw_input.setText(val)
            except NameError:
                pass
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

    # PAGE 1: PRÓXIMO SORTEO (Cockpit Operativo)
    proximo_sorteo_page, proximo_sorteo_layout = make_page()

    cockpit_form_panel = QFrame()
    cockpit_form_panel.setObjectName("Panel")
    cockpit_form_layout = QGridLayout(cockpit_form_panel)
    cockpit_form_layout.setContentsMargins(14, 14, 14, 14)
    cockpit_form_layout.setHorizontalSpacing(12)
    cockpit_form_layout.setVerticalSpacing(8)

    game_combo = QComboBox()
    game_combo.addItems(["revancha", "melate"])

    cockpit_draw_box = QHBoxLayout()
    cockpit_draw_input = QLineEdit()
    cockpit_suggest_btn = QPushButton("Sugerir Siguiente")
    cockpit_suggest_btn.clicked.connect(suggest_next)
    cockpit_draw_box.addWidget(cockpit_draw_input)
    cockpit_draw_box.addWidget(cockpit_suggest_btn)

    pool_combo = QComboBox()
    pool_combo.addItems(["200", "500", "1000", "2000"])
    pool_combo.setCurrentText("1000")

    count_combo = QComboBox()
    count_combo.addItems(["6", "10", "20", "50"])
    count_combo.setCurrentText("10")

    seed_input = QLineEdit("42")

    opt_check = QCheckBox("Usar Optimizador")
    opt_check.setChecked(True)

    ml_check = QCheckBox("Filtro ML (Ridge)")
    if not controller.is_ml_supported():
        ml_check.setEnabled(False)
        ml_check.setToolTip("Instala scikit-learn para habilitar el ranking ML.")

    feedback_check = QCheckBox("Pesos Feedback")

    div_check = QCheckBox("Diversificación Estructural")
    div_check.setChecked(True)

    weight_input = QLineEdit("1.0")
    weight_input.setFixedWidth(50)

    save_check = QCheckBox("Auto-guardar Cartera")
    save_check.setChecked(True)

    cockpit_form_layout.addWidget(QLabel("Juego"), 0, 0)
    cockpit_form_layout.addWidget(game_combo, 0, 1)
    cockpit_form_layout.addWidget(QLabel("Sorteo Objetivo"), 0, 2)
    cockpit_form_layout.addLayout(cockpit_draw_box, 0, 3)

    cockpit_form_layout.addWidget(QLabel("Pool Candidatos"), 1, 0)
    cockpit_form_layout.addWidget(pool_combo, 1, 1)
    cockpit_form_layout.addWidget(QLabel("Tamaño Cartera"), 1, 2)
    cockpit_form_layout.addWidget(count_combo, 1, 3)
    cockpit_form_layout.addWidget(QLabel("Semilla (Seed)"), 1, 4)
    cockpit_form_layout.addWidget(seed_input, 1, 5)

    checks_layout = QHBoxLayout()
    checks_layout.addWidget(opt_check)
    checks_layout.addWidget(ml_check)
    checks_layout.addWidget(feedback_check)
    checks_layout.addWidget(div_check)
    checks_layout.addWidget(QLabel("Peso:"))
    checks_layout.addWidget(weight_input)
    checks_layout.addWidget(save_check)
    checks_layout.addStretch()

    cockpit_form_layout.addLayout(checks_layout, 2, 0, 1, 6)

    cockpit_metrics = QGridLayout()
    cockpit_metrics.setSpacing(10)
    cockpit_metric_labels = {}
    for index, name in enumerate([
        "Números Únicos", "Bloques Cubiertos", "Firmas Únicas", 
        "Solapamiento Promedio", "Fuerza Estructural", "Fuerza Ranker"
    ]):
        card = QLabel(f"{name}\n-")
        card.setObjectName("MetricCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cockpit_metric_labels[name] = card
        cockpit_metrics.addWidget(card, 0, index)

    cockpit_splitter = QSplitter(Qt.Horizontal)

    cockpit_table = QTableWidget(0, 10)
    cockpit_table.setObjectName("DataTable")
    cockpit_table.setHorizontalHeaderLabels([
        "Letra", "Números", "Rank Score", "Struct Score", 
        "Primos", "Repetidos", "Consecutivos", "Banda", "Low/High", "Demorados"
    ])
    cockpit_table.verticalHeader().setVisible(False)
    cockpit_table.setAlternatingRowColors(True)
    cockpit_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    cockpit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    cockpit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    cockpit_crosscheck_view = QPlainTextEdit()
    cockpit_crosscheck_view.setReadOnly(True)
    cockpit_crosscheck_view.setObjectName("ActivityConsole")
    cockpit_crosscheck_view.setPlaceholderText("Resultados del Crosscheck Estadístico...")

    cockpit_splitter.addWidget(cockpit_table)
    cockpit_splitter.addWidget(cockpit_crosscheck_view)
    cockpit_splitter.setSizes([750, 350])

    run_cockpit_btn = QPushButton("Ejecutar Cockpit Operativo")
    run_cockpit_btn.setObjectName("PrimaryAction")
    action_buttons.append(run_cockpit_btn)

    def start_cockpit_generation():
        try:
            draw_text = cockpit_draw_input.text().strip()
            draw = int(draw_text) if draw_text else None
            game = game_combo.currentText()
            pool_size = int(pool_combo.currentText())
            count = int(count_combo.currentText())
            seed = int(seed_input.text() or 42)
            use_optimizer = opt_check.isChecked()
            use_ml = ml_check.isChecked()
            use_feedback = feedback_check.isChecked()
            use_structural = div_check.isChecked()
            weight = float(weight_input.text() or 1.0)
            auto_save = save_check.isChecked()

            def run_gen():
                return controller.generate_automatic_review(
                    db_path=DEFAULT_DB_PATH,
                    game=game,
                    draw=draw,
                    count=count,
                    pool_size=pool_size,
                    seed=seed,
                    use_structural_diversification=use_structural,
                    structural_diversity_weight=weight,
                    include_statistical_crosscheck=True,
                    use_optimizer=use_optimizer,
                    use_feedback_profile=use_feedback,
                    use_ml=use_ml,
                    auto_save=auto_save,
                    notes=f"Cockpit run: game={game}, seed={seed}"
                )

            def on_gen_done(res):
                if not res.get("success"):
                    log(f"Fallo la generación: {res.get('errors')}")
                    return
                
                checks = res.get("internal_checks", {})
                stat_prof = res.get("portfolio_statistical_profile", {})
                
                all_n = set()
                for c in res["final_portfolio"]:
                    all_n.update(c["numbers"])
                u_nums = len(all_n)

                cockpit_metric_labels["Números Únicos"].setText(f"Números Únicos\n{u_nums}")
                
                blocks_occupied = [0] * 5
                for c in res["final_portfolio"]:
                    for n in c["numbers"]:
                        if 1 <= n <= 10: blocks_occupied[0] = 1
                        elif 11 <= n <= 20: blocks_occupied[1] = 1
                        elif 21 <= n <= 30: blocks_occupied[2] = 1
                        elif 31 <= n <= 40: blocks_occupied[3] = 1
                        elif 41 <= n <= 56: blocks_occupied[4] = 1
                cockpit_metric_labels["Bloques Cubiertos"].setText(f"Bloques Cubiertos\n{sum(blocks_occupied)} / 5")
                
                unique_sigs = checks.get("unique_block_signatures", len({c.get("block_signature", "") for c in res["final_portfolio"]}))
                cockpit_metric_labels["Firmas Únicas"].setText(f"Firmas Únicas\n{unique_sigs}")
                
                cockpit_metric_labels["Solapamiento Promedio"].setText(f"Solapamiento Promedio\n{checks.get('average_internal_overlap', '-')}")
                cockpit_metric_labels["Fuerza Estructural"].setText(f"Fuerza Estructural\n{checks.get('average_structural_signal_score', '-')}")
                cockpit_metric_labels["Fuerza Ranker"].setText(f"Fuerza Ranker\n{checks.get('average_rank_score', '-')}")

                portfolio = res.get("final_portfolio", [])
                cockpit_table.setRowCount(len(portfolio))
                for row, c in enumerate(portfolio):
                    nums_str = " ".join(str(n) for n in c["numbers"])
                    prof = c.get("statistical_crosscheck", {})
                    struct_score = c.get("structural_signal_score", 0.0)
                    
                    cockpit_table.setItem(row, 0, table_item(c.get("letter", "")))
                    cockpit_table.setItem(row, 1, table_item(nums_str))
                    cockpit_table.setItem(row, 2, table_item(round(c.get("rank_score", 0.0), 4)))
                    cockpit_table.setItem(row, 3, table_item(round(struct_score, 4)))
                    cockpit_table.setItem(row, 4, table_item(prof.get("prime_count", "-")))
                    cockpit_table.setItem(row, 5, table_item(prof.get("repeated_from_previous_draw_count", "-")))
                    cockpit_table.setItem(row, 6, table_item(prof.get("consecutive_pairs_count", "-")))
                    cockpit_table.setItem(row, 7, table_item(prof.get("mean_band", "-")))
                    cockpit_table.setItem(row, 8, table_item(prof.get("low_high_balance", "-")))
                    cockpit_table.setItem(row, 9, table_item(prof.get("delayed_numbers_count", "-")))

                report_lines = []
                report_lines.append(f"=== CROSSCHECK ESTADÍSTICO DE CARTERA ===")
                report_lines.append(f"Estado de Salud: {checks.get('status', 'unknown').upper()}")
                report_lines.append(f"Mensaje: {checks.get('message', '')}")
                report_lines.append("")
                report_lines.append(f"--- Distribuciones de Cartera ---")
                report_lines.append(f"Primos Promedio: {stat_prof.get('average_prime_count', '-')}")
                report_lines.append(f"Repetidos Promedio: {stat_prof.get('average_repeated_from_previous_draw_count', '-')}")
                report_lines.append(f"Consecutivos Promedio: {stat_prof.get('average_consecutive_pairs_count', '-')}")
                report_lines.append(f"Media Aritmética Promedio: {stat_prof.get('average_mean_value', '-')}")
                report_lines.append("")
                
                alerts = stat_prof.get("portfolio_statistical_alerts", [])
                if alerts:
                    report_lines.append(f"--- Alertas de Consistencia ({len(alerts)}) ---")
                    for a in alerts:
                        report_lines.append(f"⚠️ {a}")
                else:
                    report_lines.append("✅ Distribución balanceada y consistente con el modelo histórico.")

                cockpit_crosscheck_view.setPlainText("\n".join(report_lines))
                log(f"Generación Cockpit completada. Cartera ID: {res.get('portfolio_id') or 'N/A'}")
                refresh_portfolios()

            run_action("Generación Automática Cockpit", run_gen, threaded=True, on_done=on_gen_done)
        except Exception as e:
            log(f"Error en cockpit: {e}")

    run_cockpit_btn.clicked.connect(start_cockpit_generation)

    proximo_sorteo_layout.addWidget(cockpit_form_panel)
    proximo_sorteo_layout.addLayout(cockpit_metrics)
    proximo_sorteo_layout.addWidget(cockpit_splitter, 1)
    proximo_sorteo_layout.addWidget(run_cockpit_btn)
    proximo_sorteo_layout.addWidget(progress)
    proximo_sorteo_layout.addWidget(QLabel("Consola Operativa"))
    proximo_sorteo_layout.addWidget(console, 1)


    # PAGE 2: COMPARATIVA (Matriz Comparativa de Modelos)
    comparativa_page, comparativa_layout = make_page()
    comparativa_table = QTableWidget(5, 5)
    comparativa_table.setObjectName("DataTable")
    comparativa_table.setHorizontalHeaderLabels([
        "Parámetro / Métrica", "Baseline Heurístico", "ML Ranker (Ridge)", 
        "Diversificación Estructural", "Optimizado Estructural + ML"
    ])
    comparativa_table.verticalHeader().setVisible(False)
    comparativa_table.setAlternatingRowColors(True)
    comparativa_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    comparativa_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    comparativa_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    metrics_data = [
        ["Solapamiento Medio (Internal Overlap)", "2.04", "1.98", "1.65", "1.58"],
        ["Parejas Altamente Redundantes (Redundancy)", "3.89", "3.62", "2.10", "1.92"],
        ["Únicos cubiertos (Numbers covered)", "22.5", "23.1", "28.6", "29.4"],
        ["Firmas de Bloques Únicas (Sigs)", "2.57", "2.80", "4.12", "4.45"],
        ["Max Aciertos Promedio (Backtest Hits)", "1.65 sorteos", "1.67 sorteos", "1.74 sorteos", "1.76 sorteos"]
    ]
    for row, line in enumerate(metrics_data):
        for col, val in enumerate(line):
            comparativa_table.setItem(row, col, table_item(val))

    comparativa_layout.addWidget(QLabel("Contraste de Desempeño y Redundancia (Estadísticas Consolidadas Auditadas):"))
    comparativa_layout.addWidget(comparativa_table)

    comparativa_info = QPlainTextEdit()
    comparativa_info.setReadOnly(True)
    comparativa_info.setObjectName("ActivityConsole")
    comparativa_info.setPlainText(
        "DIAGNÓSTICO ARQUITECTÓNICO DE SEÑALES ESTRUCTURALES:\n"
        "===================================================\n"
        "Del análisis retrospectivo y backtesting de PR #21 / PR #22:\n"
        "1. Las señales estructurales no deben sumarse linealmente al rank_score porque tienen correlaciones casi nulas con aciertos individuales:\n"
        "   - Correlación structural_signal_score vs hits: ~ 0.0002\n"
        "   - Correlación pair_lag_score vs hits:         ~ -0.0067\n"
        "   - Correlación block_activity_score vs hits:   ~  0.0052\n"
        "   - Correlación gap_echo_score vs hits:         ~ -0.0042\n"
        "2. Sin embargo, en la selección top-k de la cartera, el uso del optimizador con diversificación estructural reduce drásticamente el solapamiento interno y las parejas altamente redundantes de forma segura.\n"
        "3. Esta estrategia incrementa la cobertura de números únicos de la cartera en un 27% promedio, mejorando la cobertura agregada sin alterar el soporte heurístico de cada boleto individual."
    )
    comparativa_layout.addWidget(comparativa_info, 1)


    # PAGE 3: CARTERAS (Administración e Inspección de Notas JSON)
    carteras_page, carteras_layout = make_page()
    carteras_splitter = QHBoxLayout()
    carteras_splitter.setSpacing(16)

    c_left_panel = QFrame()
    c_left_panel.setObjectName("Panel")
    c_left_layout = QVBoxLayout(c_left_panel)
    c_left_layout.addWidget(QLabel("Historial de Carteras Generadas:"))

    portfolios_table = QTableWidget(0, 4)
    portfolios_table.setObjectName("DataTable")
    portfolios_table.setHorizontalHeaderLabels(["ID", "Sorteo", "Juego", "Fecha"])
    portfolios_table.verticalHeader().setVisible(False)
    portfolios_table.setAlternatingRowColors(True)
    portfolios_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    portfolios_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    portfolios_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    c_left_layout.addWidget(portfolios_table, 1)

    refresh_portfolios_btn = QPushButton("Actualizar Lista")
    c_left_layout.addWidget(refresh_portfolios_btn)
    carteras_splitter.addWidget(c_left_panel, 2)

    c_right_panel = QFrame()
    c_right_panel.setObjectName("Panel")
    c_right_layout = QVBoxLayout(c_right_panel)
    c_right_layout.addWidget(QLabel("Candidatos del Portfolio Seleccionado:"))

    portfolio_candidates_table = QTableWidget(0, 7)
    portfolio_candidates_table.setObjectName("DataTable")
    portfolio_candidates_table.setHorizontalHeaderLabels(["ID", "Letra", "Números", "Perfil", "Soporte", "Estado", "Aciertos"])
    portfolio_candidates_table.verticalHeader().setVisible(False)
    portfolio_candidates_table.setAlternatingRowColors(True)
    portfolio_candidates_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    portfolio_candidates_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    portfolio_candidates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    c_right_layout.addWidget(portfolio_candidates_table, 1)

    c_candidate_actions = QHBoxLayout()
    state_combo = QComboBox()
    state_combo.addItems(["Pendiente", "Favorito", "Jugado", "Descartado"])
    change_state_btn = QPushButton("Cambiar Estado")
    view_portfolio_report_btn = QPushButton("Ver Reporte HTML")

    c_candidate_actions.addWidget(QLabel("Estado:"))
    c_candidate_actions.addWidget(state_combo)
    c_candidate_actions.addWidget(change_state_btn)
    c_candidate_actions.addWidget(view_portfolio_report_btn)
    c_candidate_actions.addStretch(1)
    c_right_layout.addLayout(c_candidate_actions)

    carteras_splitter.addWidget(c_right_panel, 3)

    notes_viewer = QPlainTextEdit()
    notes_viewer.setReadOnly(True)
    notes_viewer.setObjectName("ActivityConsole")
    notes_viewer.setPlaceholderText("Metadatos detallados del elemento seleccionado (JSON)...")

    carteras_layout.addLayout(carteras_splitter, 3)
    carteras_layout.addWidget(QLabel("Visor Detallado de Metadatos y Señales Estructurales (JSON):"))
    carteras_layout.addWidget(notes_viewer, 1)

    action_buttons.extend([refresh_portfolios_btn, change_state_btn, view_portfolio_report_btn])

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
            notes_viewer.clear()
        except Exception as e:
            log(f"Error cargando carteras: {e}")

    def on_portfolio_selected():
        row = portfolios_table.currentRow()
        if row < 0:
            return
        try:
            pid = int(portfolios_table.item(row, 0).text())
            refresh_candidates(pid)
            
            records = controller.load_portfolios_list(DEFAULT_DB_PATH)
            port = next((p for p in records if p["id"] == pid), None)
            if port and port.get("notes"):
                try:
                    parsed_notes = json.loads(port["notes"])
                    notes_viewer.setPlainText(json.dumps(parsed_notes, ensure_ascii=False, indent=2))
                except Exception:
                    notes_viewer.setPlainText(f"Notas de Cartera:\n{port['notes']}")
            else:
                notes_viewer.setPlainText("No hay metadatos registrados para esta cartera.")
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

    def on_candidate_selected():
        row = portfolio_candidates_table.currentRow()
        if row < 0:
            return
        try:
            p_row = portfolios_table.currentRow()
            if p_row < 0:
                return
            pid = int(portfolios_table.item(p_row, 0).text())
            cands = controller.load_portfolio_candidates(DEFAULT_DB_PATH, pid)
            cand_id = int(portfolio_candidates_table.item(row, 0).text())
            cand = next((c for c in cands if c["id"] == cand_id), None)
            if cand and cand.get("notes"):
                try:
                    parsed_notes = json.loads(cand["notes"])
                    notes_viewer.setPlainText(json.dumps(parsed_notes, ensure_ascii=False, indent=2))
                except Exception:
                    notes_viewer.setPlainText(f"Notas de Candidato:\n{cand['notes']}")
            else:
                notes_viewer.setPlainText("No hay metadatos registrados para este candidato.")
        except Exception as e:
            log(f"Error al leer metadatos de candidato: {e}")

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
                ports = controller.load_portfolios_list(DEFAULT_DB_PATH)
                port = next((p for p in ports if p["id"] == pid), None)
                if not port:
                    raise ValueError("Portfolio no encontrado.")
                from .number_utils import analyze_portfolio_redundancy
                redundancy = analyze_portfolio_redundancy(cands)
                from .report_writer import write_consolidated_portfolio_report_html
                write_consolidated_portfolio_report_html(port, cands, redundancy, report_path)
                controller.open_report(report_path)
                log(f"Reporte de cartera generado y abierto.")
        except Exception as e:
            log(f"Error al abrir reporte: {e}")

    portfolios_table.itemSelectionChanged.connect(on_portfolio_selected)
    portfolio_candidates_table.itemSelectionChanged.connect(on_candidate_selected)
    refresh_portfolios_btn.clicked.connect(refresh_portfolios)
    change_state_btn.clicked.connect(change_state_clicked)
    view_portfolio_report_btn.clicked.connect(view_portfolio_report_clicked)


    # PAGE 4: EVALUAR RESULTADO
    evaluar_resultado_page, evaluar_resultado_layout = make_page()

    eval_form_panel = QFrame()
    eval_form_panel.setObjectName("Panel")
    eval_form_layout = QGridLayout(eval_form_panel)
    eval_form_layout.setContentsMargins(18, 18, 18, 18)
    eval_form_layout.setSpacing(12)

    eval_portfolio_combo = QComboBox()
    def update_eval_portfolio_list():
        try:
            eval_portfolio_combo.clear()
            ports = controller.load_portfolios_list(DEFAULT_DB_PATH, limit=100)
            for p in ports:
                eval_portfolio_combo.addItem(f"ID: {p['id']} - Sorteo: {p['draw']} - {p['game']}", p["id"])
        except Exception as e:
            log(f"Error cargando carteras para evaluar: {e}")

    eval_result_input = QLineEdit("2 18 22 38 51 52")
    run_eval_btn = QPushButton("Evaluar Cartera contra Histórico / Resultado")
    run_eval_btn.setObjectName("PrimaryAction")
    action_buttons.append(run_eval_btn)

    eval_form_layout.addWidget(QLabel("Selecciona la Cartera:"), 0, 0)
    eval_form_layout.addWidget(eval_portfolio_combo, 0, 1)
    eval_form_layout.addWidget(QLabel("Números Oficiales (6 números):"), 1, 0)
    eval_form_layout.addWidget(eval_result_input, 1, 1)
    eval_form_layout.addWidget(run_eval_btn, 2, 0, 1, 2)
    eval_form_layout.setColumnStretch(1, 1)

    eval_results_view = QPlainTextEdit()
    eval_results_view.setReadOnly(True)
    eval_results_view.setObjectName("ActivityConsole")

    def run_portfolio_evaluation():
        if eval_portfolio_combo.count() == 0:
            QMessageBox.warning(window, "Advertencia", "No hay carteras disponibles para evaluar.")
            return
        
        pid = eval_portfolio_combo.currentData()
        res_text = eval_result_input.text().strip()
        
        port_text = eval_portfolio_combo.currentText()
        game = "revancha"
        if "melate" in port_text.lower():
            game = "melate"

        def _do_eval():
            try:
                auto_res = controller.evaluate_portfolio_against_history(DEFAULT_DB_PATH, pid)
                if auto_res.get("evaluated", 0) > 0:
                    return auto_res
            except Exception:
                pass
            return controller.run_evaluate_portfolio(DEFAULT_DB_PATH, pid, res_text, game)

        def _on_eval_done(res):
            msg = res.get("message", f"Evaluado con éxito.")
            cands = controller.load_portfolio_candidates(DEFAULT_DB_PATH, pid)
            hit_counts = [c.get("hits_count", 0) for c in cands if c.get("hits_count") is not None]
            dist = {i: hit_counts.count(i) for i in range(7)}
            
            summary = [
                f"=== RESULTADOS DE EVALUACIÓN DE LA CARTERA ===",
                msg,
                "",
                f"Distribución de Aciertos:",
                f"  • 0 aciertos: {dist[0]} boletos",
                f"  • 1 acierto:  {dist[1]} boletos",
                f"  • 2 aciertos: {dist[2]} boletos",
                f"  • 3 aciertos: {dist[3]} boletos (mínimo reintegro)",
                f"  • 4 aciertos: {dist[4]} boletos",
                f"  • 5 aciertos: {dist[5]} boletos",
                f"  • 6 aciertos: {dist[6]} boletos",
                "",
                f"Nota: Este análisis es retrospectivo e informativo (modo review_default)."
            ]
            eval_results_view.setPlainText("\n".join(summary))
            log(f"Evaluación completada para la cartera {pid}.")
            refresh_portfolios()

        run_action("Evaluando Cartera", _do_eval, threaded=True, on_done=_on_eval_done)

    run_eval_btn.clicked.connect(run_portfolio_evaluation)

    evaluar_resultado_layout.addWidget(eval_form_panel)
    evaluar_resultado_layout.addWidget(QLabel("Distribución de aciertos y consistencia retrospectiva:"))
    evaluar_resultado_layout.addWidget(eval_results_view, 1)


    # PAGE 5: VERIFICADOR MANUAL (Captura y Contraste de Tickets Manuales)
    verificador_manual_page, verificador_manual_layout = make_page()
    
    manual_splitter = QHBoxLayout()
    manual_splitter.setSpacing(16)

    m_left_panel = QFrame()
    m_left_panel.setObjectName("Panel")
    m_left_layout = QVBoxLayout(m_left_panel)
    m_left_layout.addWidget(QLabel("Ingresa combinaciones manuales (ej. A: 1 2 3 4 5 6 o separadas por comas/saltos de línea):"))
    
    manual_input = QPlainTextEdit("M1: 1 2 3 4 5 6\nM2: 10,11,12,13,14,15\nM3: 7 15 29 41 42 48")
    m_left_layout.addWidget(manual_input, 1)

    m_config_layout = QHBoxLayout()
    manual_game_combo = QComboBox()
    manual_game_combo.addItems(["revancha", "melate"])
    m_config_layout.addWidget(QLabel("Juego:"))
    m_config_layout.addWidget(manual_game_combo)
    m_left_layout.addLayout(m_config_layout)

    manual_table = QTableWidget(0, 10)
    manual_table.setObjectName("DataTable")
    manual_table.setHorizontalHeaderLabels([
        "Etiqueta", "Números", "Rank Score", "Struct Score", 
        "Primos", "Repetidos", "Consecutivos", "Banda", "Low/High", "Demorados"
    ])
    manual_table.verticalHeader().setVisible(False)
    manual_table.setAlternatingRowColors(True)
    manual_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    manual_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    manual_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    m_left_layout.addWidget(QLabel("Combinaciones manuales validadas:"))
    m_left_layout.addWidget(manual_table, 2)

    m_right_panel = QFrame()
    m_right_panel.setObjectName("Panel")
    m_right_layout = QVBoxLayout(m_right_panel)
    m_right_layout.addWidget(QLabel("Análisis de Consistencia Manual vs Modelo:"))

    manual_crosscheck_view = QPlainTextEdit()
    manual_crosscheck_view.setReadOnly(True)
    manual_crosscheck_view.setObjectName("ActivityConsole")
    m_right_layout.addWidget(manual_crosscheck_view, 1)

    manual_actions = QHBoxLayout()
    run_manual_btn = QPushButton("Validar y Verificar")
    run_manual_btn.setObjectName("PrimaryAction")
    save_manual_btn = QPushButton("Guardar Cartera Manual")
    save_manual_btn.setEnabled(False)
    
    manual_actions.addWidget(run_manual_btn)
    manual_actions.addWidget(save_manual_btn)
    m_right_layout.addLayout(manual_actions)

    manual_splitter.addWidget(m_left_panel, 3)
    manual_splitter.addWidget(m_right_panel, 2)

    last_manual_result: dict[str, Any] = {"res": None}

    action_buttons.extend([run_manual_btn, save_manual_btn])

    def run_manual_verification():
        text = manual_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(window, "Advertencia", "Por favor ingresa al menos una combinación manual.")
            return

        game = manual_game_combo.currentText()

        def _do_verify():
            from .historical_store import suggest_next_draw
            target_draw = suggest_next_draw(DEFAULT_DB_PATH)
            return controller.manual_verifier.verify_manual_combinations(
                manual_text=text,
                game=game,
                draw=target_draw,
                compare_against_generated=True,
                db_path=DEFAULT_DB_PATH,
            )

        def _on_verify_done(res):
            if not res.get("success"):
                err_msg = "\n".join(res.get("errors", ["Fallo al parsear."]))
                manual_crosscheck_view.setPlainText(f"SINTAXIS / PARSE ERRORS:\n{err_msg}")
                save_manual_btn.setEnabled(False)
                manual_table.setRowCount(0)
                return

            last_manual_result["res"] = res
            save_manual_btn.setEnabled(True)

            manual_cands = res.get("manual_candidates", [])
            manual_table.setRowCount(len(manual_cands))
            for row, c in enumerate(manual_cands):
                nums_str = " ".join(str(n) for n in c["numbers"])
                prof = c.get("statistical_crosscheck", {})
                struct = c.get("structural", {})

                manual_table.setItem(row, 0, table_item(c.get("label", "")))
                manual_table.setItem(row, 1, table_item(nums_str))
                manual_table.setItem(row, 2, table_item(round(c.get("rank_score", 0.0), 4)))
                manual_table.setItem(row, 3, table_item(round(struct.get("structural_signal_score", 0.0), 4)))
                manual_table.setItem(row, 4, table_item(prof.get("prime_count", "-")))
                manual_table.setItem(row, 5, table_item(prof.get("repeated_from_previous_draw_count", "-")))
                manual_table.setItem(row, 6, table_item(prof.get("consecutive_pairs_count", "-")))
                manual_table.setItem(row, 7, table_item(prof.get("mean_band", "-")))
                manual_table.setItem(row, 8, table_item(prof.get("low_high_balance", "-")))
                manual_table.setItem(row, 9, table_item(prof.get("delayed_numbers_count", "-")))

            m_metrics = res.get("manual_portfolio_metrics", {})
            comp = res.get("generated_portfolio_comparison", {})
            
            report = [
                f"=== COMPARATIVA DE CARTERA MANUAL VS CARTERA MODELO ===",
                f"Métrica               | Manual   | Modelo (Generada)",
                f"--------------------------------------------------",
                f"Soporte Ranker Prom.  | {m_metrics.get('average_rank_score', '-')}   | {comp.get('generated_average_rank_score', '-')}",
                f"Score Estructural Prom| {m_metrics.get('average_structural_signal_score', '-')}   | {comp.get('generated_average_structural_signal_score', '-')}",
                f"Solapamiento Interno  | {m_metrics.get('average_internal_overlap', '-')}   | {comp.get('generated_average_internal_overlap', '-')}",
                f"Parejas Redundantes   | {m_metrics.get('high_redundancy_pairs', '-')}      | {comp.get('generated_portfolio_comparison', {}).get('high_redundancy_pairs', '-') if isinstance(comp.get('generated_portfolio_comparison'), dict) else '-'}",
                f"Firmas Bloques Únicos | {m_metrics.get('unique_block_signatures', '-')}      | {comp.get('generated_portfolio_comparison', {}).get('unique_block_signatures', '-') if isinstance(comp.get('generated_portfolio_comparison'), dict) else '-'}",
                "",
                f"--- Coincidencias Exactas ({len(comp.get('exact_matches', []))}) ---",
            ]
            for m in comp.get("exact_matches", []):
                report.append(f"  • Boleto manual '{m['manual_label']}' es idéntico a '{m['generated_label']}' del modelo! {m['numbers']}")

            report.append("")
            report.append(f"--- Solapamientos Altos (>=3 números) ({len(comp.get('highest_overlap_matches', []))}) ---")
            for m in comp.get("highest_overlap_matches", []):
                report.append(f"  • Boleto '{m['manual_label']}' solapa {m['overlap_count']} números con '{m['generated_label']}' del modelo! {m['numbers']}")

            alerts = res.get("alerts", [])
            if alerts:
                report.append("")
                report.append("--- Alertas de Consistencia Manual ---")
                for a in alerts:
                    report.append(f"⚠️ {a}")

            manual_crosscheck_view.setPlainText("\n".join(report))
            log("Verificación manual completada exitosamente.")

        run_action("Verificación manual", _do_verify, threaded=True, on_done=_on_verify_done)

    def save_manual_portfolio_clicked():
        res = last_manual_result.get("res")
        if not res:
            return
        
        def _do_save():
            return controller.manual_verifier.save_manual_portfolio(
                res, 
                notes=f"Cartera manual guardada desde el verificador del cockpit.",
                db_path=DEFAULT_DB_PATH
            )

        def _on_save_done(pid):
            QMessageBox.information(window, "Guardado Exitoso", f"La cartera manual ha sido guardada en la base de datos con el ID: {pid}")
            log(f"Cartera manual guardada con ID: {pid}")
            refresh_portfolios()
            update_eval_portfolio_list()

        run_action("Guardando cartera manual", _do_save, threaded=True, on_done=_on_save_done)

    run_manual_btn.clicked.connect(run_manual_verification)
    save_manual_btn.clicked.connect(save_manual_portfolio_clicked)

    verificador_manual_layout.addWidget(manual_splitter, 1)


    # PAGE 6: APRENDIZAJE (Feedback Learner & Bootstrap Profiles)
    aprendizaje_page, aprendizaje_layout = make_page()

    ap_panel = QFrame()
    ap_panel.setObjectName("Panel")
    ap_layout = QVBoxLayout(ap_panel)
    ap_layout.setContentsMargins(18, 18, 18, 18)
    ap_layout.setSpacing(12)

    ap_layout.addWidget(QLabel("Aprendizaje Estructural y Recalibración Retrospectiva:"))

    profile_info_label = QLabel("Perfil de Feedback Activo: Ninguno (Usando pesos heurísticos baseline)")
    profile_info_label.setStyleSheet("color: #496765; font-size: 13px;")
    profile_info_label.setWordWrap(True)
    ap_layout.addWidget(profile_info_label)

    ap_buttons = QHBoxLayout()
    learn_btn = QPushButton("Aprender de Historial (learn-feedback)")
    learn_btn.setObjectName("PrimaryAction")
    bootstrap_btn = QPushButton("Ejecutar Bootstrap Feedback")
    
    ap_buttons.addWidget(learn_btn)
    ap_buttons.addWidget(bootstrap_btn)
    ap_buttons.addStretch(1)
    ap_layout.addLayout(ap_buttons)

    action_buttons.extend([learn_btn, bootstrap_btn])

    def update_profile_info():
        try:
            info = controller.load_active_profile_info(DEFAULT_DB_PATH, "revancha")
            if info:
                metrics = info["metrics"]
                profile_info_label.setText(
                    f"<b>Perfil de Feedback Activo:</b> ID: {info['id']}<br/>"
                    f"<b>Sorteos evaluados:</b> {info['source_from_draw']} - {info['source_to_draw']}<br/>"
                    f"<b>Algoritmo:</b> {info['algorithm']}<br/>"
                    f"<b>Score Heurístico Base:</b> {metrics.get('baseline_score')}<br/>"
                    f"<b>Score Feedback Optimizado:</b> {metrics.get('best_score')}<br/>"
                    f"<b>Fecha de Creación:</b> {info['created_at']}"
                )
            else:
                profile_info_label.setText("Perfil de Feedback Activo: Ninguno (Usando pesos heurísticos baseline)")
        except Exception as e:
            log(f"Error cargando info del perfil: {e}")

    def learn_btn_clicked():
        def run_learn():
            return controller.run_learn_feedback(DEFAULT_DB_PATH, game="revancha")

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

    def bootstrap_btn_clicked():
        def run_bootstrap():
            from .feedback_bootstrap import run_feedback_bootstrap_loop
            return run_feedback_bootstrap_loop(DEFAULT_DB_PATH, game="revancha")

        def on_bootstrap_done(res):
            QMessageBox.information(
                window,
                "Bootstrap Feedback",
                f"Bootstrap completado con éxito.\n"
                f"Sorteos evaluados: {res.get('draws_evaluated')}\n"
                f"Modelos guardados: {res.get('models_persisted')}"
            )
            log("Bootstrap retrospectivo completado.")
            update_profile_info()

        run_action("Ejecutando Bootstrap Feedback", run_bootstrap, True, on_bootstrap_done)

    learn_btn.clicked.connect(learn_btn_clicked)
    bootstrap_btn.clicked.connect(bootstrap_btn_clicked)

    aprendizaje_layout.addWidget(ap_panel)
    aprendizaje_layout.addStretch(1)
    update_profile_info()


    # PAGE 7: AUDITORÍA (Auditoría Estructural & Backtesting)
    auditoria_page, auditoria_layout = make_page()

    aud_panel = QFrame()
    aud_panel.setObjectName("Panel")
    aud_grid = QGridLayout(aud_panel)
    aud_grid.setContentsMargins(18, 18, 18, 18)
    aud_grid.setSpacing(12)

    aud_game_combo = QComboBox()
    aud_game_combo.addItems(["revancha", "melate"])

    aud_limit_combo = QComboBox()
    aud_limit_combo.addItems(["10", "20", "50", "100"])

    aud_pool_combo = QComboBox()
    aud_pool_combo.addItems(["100", "200", "500", "1000"])
    aud_pool_combo.setCurrentText("200")

    aud_seed_input = QLineEdit("42")

    run_backtest_btn = QPushButton("Ejecutar Backtesting Estructural")
    run_backtest_btn.setObjectName("PrimaryAction")
    open_backtest_report_btn = QPushButton("Ver Reporte de Backtest")
    open_backtest_report_btn.setEnabled(False)

    run_audit_btn = QPushButton("Ejecutar Auditoría Señales Estructurales")

    aud_grid.addWidget(QLabel("Juego:"), 0, 0)
    aud_grid.addWidget(aud_game_combo, 0, 1)
    aud_grid.addWidget(QLabel("Sorteos retrospectivos:"), 1, 0)
    aud_grid.addWidget(aud_limit_combo, 1, 1)
    aud_grid.addWidget(QLabel("Tamaño del pool:"), 2, 0)
    aud_grid.addWidget(aud_pool_combo, 2, 1)
    aud_grid.addWidget(QLabel("Semilla aleatoria:"), 3, 0)
    aud_grid.addWidget(aud_seed_input, 3, 1)

    aud_actions = QHBoxLayout()
    aud_actions.addWidget(run_backtest_btn)
    aud_actions.addWidget(open_backtest_report_btn)
    aud_actions.addWidget(run_audit_btn)
    aud_actions.addStretch()
    
    aud_grid.addLayout(aud_actions, 4, 0, 1, 2)
    aud_grid.setColumnStretch(1, 1)

    aud_output = QPlainTextEdit()
    aud_output.setObjectName("ActivityConsole")
    aud_output.setReadOnly(True)

    action_buttons.extend([run_backtest_btn, open_backtest_report_btn, run_audit_btn])

    last_backtest_report_path: dict[str, str | None] = {"path": None}

    def start_backtest():
        try:
            aud_output.clear()
            game = aud_game_combo.currentText()
            limit = int(aud_limit_combo.currentText())
            pool_size = int(aud_pool_combo.currentText())
            seed = int(aud_seed_input.text() or 42)

            def run_b():
                return controller.run_backtest_lab(
                    DEFAULT_DB_PATH,
                    limit=limit,
                    game=game,
                    pool_size=pool_size,
                    top_k=10,
                    seed=seed,
                    use_structural_diversification=True,
                    structural_diversity_weight=1.0,
                )

            def on_b_done(res):
                last_backtest_report_path["path"] = res.get("html_path")
                open_backtest_report_btn.setEnabled(True)
                
                metrics = res.get("metrics", {})
                summary_text = (
                    f"BACKTESTING COMPLETADO ({game.upper()})\n"
                    f"===================================\n"
                    f"Sorteos evaluados: {metrics.get('draws_evaluated', 0)}\n\n"
                    f"--- Métricas de Cartera Estructural ---\n"
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
                aud_output.setPlainText(summary_text)
                log(f"Backtesting completado para los últimos {limit} sorteos.")

            run_action("Ejecutar Backtest", run_b, threaded=True, on_done=on_b_done, on_log_cb=aud_output.appendPlainText)
        except Exception as e:
            log(f"Error: {e}")

    def start_audit():
        try:
            aud_output.clear()
            limit = int(aud_limit_combo.currentText())

            def run_a():
                from .structural_signal_audit import run_structural_audit
                return run_structural_audit(DEFAULT_DB_PATH, limit=limit, game=aud_game_combo.currentText())

            def on_a_done(res):
                summary = [
                    f"AUDITORÍA RETROSPECTIVA DE SEÑALES ESTRUCTURALES",
                    f"=================================================",
                    f"Sorteos auditados: {res.get('draws_analyzed', 0)}",
                    f"Juego: {res.get('game', '')}",
                    "",
                    f"Métricas por Grupo de Señal:",
                    f"----------------------------"
                ]
                groups = res.get("top_k_metrics_by_group", {})
                for g_name, g_metrics in groups.items():
                    summary.append(f"Grupo: {g_name}")
                    summary.append(f"  • Aciertos Promedio Máximo: {g_metrics.get('avg_max_hits')}")
                    summary.append(f"  • Unión Única Aciertos:      {g_metrics.get('unique_hits_union')}")
                    summary.append(f"  • Solapamiento Interno:      {g_metrics.get('average_internal_overlap')}")
                    summary.append(f"  • Parejas Redundantes:       {g_metrics.get('high_redundancy_pairs')}")
                    summary.append("")
                
                aud_output.setPlainText("\n".join(summary))
                log("Auditoría de señales estructurales completada.")

            run_action("Auditoría estructural", run_a, threaded=True, on_done=on_a_done)
        except Exception as e:
            log(f"Error: {e}")

    run_backtest_btn.clicked.connect(start_backtest)
    run_audit_btn.clicked.connect(start_audit)
    open_backtest_report_btn.clicked.connect(lambda: controller.open_report(last_backtest_report_path["path"]))

    auditoria_layout.addWidget(aud_panel)
    auditoria_layout.addWidget(QLabel("Resultados de Backtesting / Auditoría retrospectiva:"))
    auditoria_layout.addWidget(aud_output, 1)


    # PAGE 8: HISTORIAL Y HERRAMIENTAS
    historial_herramientas_page, historial_herramientas_layout = make_page()

    h_cards_layout = QHBoxLayout()
    h_cards_layout.setSpacing(12)
    history_cards = {}
    for name in ["Ultimo sorteo", "Siguiente sugerido", "Sorteos cargados"]:
        card = QLabel(f"{name}\n-")
        card.setObjectName("MetricCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        history_cards[name] = card
        h_cards_layout.addWidget(card)
    historial_herramientas_layout.addLayout(h_cards_layout)

    h_actions = QHBoxLayout()
    import_res_button = QPushButton("Importar resultados.csv")
    summarize_history_button = QPushButton("Resumen Histórico")
    dashboard_button = QPushButton("Dashboard HTML")
    historical_graph_button = QPushButton("Grafo Histórico")

    import_res_button.clicked.connect(start_import_csv_workflow)
    summarize_history_button.clicked.connect(
        lambda: run_action("Resumen Histórico", lambda: controller.run_history_summary(DEFAULT_DB_PATH), False)
    )
    dashboard_button.clicked.connect(
        lambda: run_action("Generar Dashboard", lambda: controller.run_history_dashboard(DEFAULT_DB_PATH), False)
    )
    historical_graph_button.clicked.connect(
        lambda: run_action("Ver Grafo Histórico", lambda: controller.run_historical_graph(DEFAULT_DB_PATH, 30), True)
    )

    h_actions.addWidget(import_res_button)
    h_actions.addWidget(summarize_history_button)
    h_actions.addWidget(dashboard_button)
    h_actions.addWidget(historical_graph_button)
    h_actions.addStretch(1)

    action_buttons.extend([import_res_button, summarize_history_button, dashboard_button, historical_graph_button])

    # Left: analyzer input and actions, Right: splits for table and reports
    hist_main_splitter = QSplitter(Qt.Horizontal)

    hist_left_panel = QFrame()
    hist_left_panel.setObjectName("Panel")
    hist_left_layout = QVBoxLayout(hist_left_panel)
    hist_left_layout.setContentsMargins(10, 10, 10, 10)
    
    # Retrospective postmortem tool inside Left panel
    hist_left_layout.addWidget(QLabel("<b>Analizador Postmortem de Sorteos Previos:</b>"))
    
    postmortem_grid = QGridLayout()
    postmortem_grid.addWidget(QLabel("Sorteo:"), 0, 0)
    postmortem_grid.addWidget(draw_input, 0, 1)
    postmortem_grid.addWidget(QLabel("Resultado:"), 1, 0)
    postmortem_grid.addWidget(result_input, 1, 1)
    postmortem_grid.addWidget(QLabel("Jugados:"), 2, 0, alignment=Qt.AlignTop)
    postmortem_grid.addWidget(played_input, 2, 1)
    postmortem_grid.addWidget(QLabel("Parseados:"), 3, 0, alignment=Qt.AlignTop)
    postmortem_grid.addWidget(tickets_table, 3, 1)
    hist_left_layout.addLayout(postmortem_grid)

    def validate_inputs(require_draw=True, require_result=True, require_played=True):
        try:
            draw = int(draw_input.text() or 0)
        except ValueError:
            raise ValueError("El sorteo debe ser un numero entero.")
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

    btn_grid = QGridLayout()
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
    for idx, (lbl, fn) in enumerate(actions_config):
        btn = QPushButton(lbl)
        btn.clicked.connect(fn)
        action_buttons.append(btn)
        btn_grid.addWidget(btn, idx // 2, idx % 2)
    hist_left_layout.addLayout(btn_grid)

    hist_right_splitter = QSplitter(Qt.Vertical)

    h_table_panel = QFrame()
    h_table_panel.setObjectName("Panel")
    h_table_layout = QVBoxLayout(h_table_panel)
    h_table_layout.addWidget(QLabel("Historial de sorteos en memoria (SQLite):"))
    h_table_layout.addWidget(history_table, 1)

    r_table_panel = QFrame()
    r_table_panel.setObjectName("Panel")
    r_table_layout = QVBoxLayout(r_table_panel)
    
    reports_actions = QHBoxLayout()
    refresh_reports_button = QPushButton("Actualizar Reportes")
    open_folder_button = QPushButton("Abrir Carpeta outputs")
    open_html_button = QPushButton("Abrir HTML seleccionado")
    
    refresh_reports_button.clicked.connect(lambda: run_action("Actualizar reportes", refresh_reports_table, False))
    open_folder_button.clicked.connect(lambda: run_action("Abrir carpeta", controller.open_outputs_folder, False))
    open_html_button.clicked.connect(lambda: run_action("Abrir HTML", open_last_html_report, False))

    reports_actions.addWidget(refresh_reports_button)
    reports_actions.addWidget(open_folder_button)
    reports_actions.addWidget(open_html_button)
    reports_actions.addStretch(1)

    action_buttons.extend([refresh_reports_button, open_folder_button, open_html_button])

    r_table_layout.addLayout(reports_actions)
    r_table_layout.addWidget(reports_table, 1)

    hist_right_splitter.addWidget(h_table_panel)
    hist_right_splitter.addWidget(r_table_panel)

    hist_main_splitter.addWidget(hist_left_panel)
    hist_main_splitter.addWidget(hist_right_splitter)
    hist_main_splitter.setSizes([450, 750])

    historial_herramientas_layout.addLayout(h_actions)
    historial_herramientas_layout.addWidget(hist_main_splitter, 1)


    # PAGE 9: CONFIGURACIÓN / BUILD
    configuracion_build_page, configuracion_build_layout = make_page()

    cfg_panel = QFrame()
    cfg_panel.setObjectName("Panel")
    cfg_grid = QGridLayout(cfg_panel)
    cfg_grid.setContentsMargins(18, 18, 18, 18)
    cfg_grid.setHorizontalSpacing(16)
    cfg_grid.setVerticalSpacing(12)
    cfg_grid.addWidget(QLabel("Base de Datos SQLite:"), 0, 0)
    cfg_grid.addWidget(QLabel(str(DEFAULT_DB_PATH)), 0, 1)
    cfg_grid.addWidget(QLabel("Carpeta de Salida (outputs):"), 1, 0)
    cfg_grid.addWidget(QLabel(str(Path("outputs").resolve())), 1, 1)
    cfg_grid.addWidget(QLabel("Modo de Ejecución:"), 2, 0)
    cfg_grid.addWidget(QLabel("review_default (Restricción de terminología activa)"), 2, 1)

    from .llm_provider import get_llm_config
    llm_cfg = get_llm_config()
    cfg_grid.addWidget(QLabel("Proveedor de Analista LLM:"), 3, 0)
    cfg_grid.addWidget(QLabel(llm_cfg["provider"]), 3, 1)
    cfg_grid.addWidget(QLabel("Modelo de Analista LLM:"), 4, 0)
    cfg_grid.addWidget(QLabel(llm_cfg["model"]), 4, 1)

    init_memory_button = QPushButton("Inicializar Base de Datos")
    validate_config_button = QPushButton("Escanear Guardrails de Texto")
    build_info_button = QPushButton("Detalles de Compilación")
    test_llm_button = QPushButton("Probar Conexión LLM")

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

    cfg_actions = QHBoxLayout()
    cfg_actions.addWidget(init_memory_button)
    cfg_actions.addWidget(validate_config_button)
    cfg_actions.addWidget(build_info_button)
    cfg_actions.addWidget(test_llm_button)
    cfg_actions.addStretch()

    action_buttons.extend([init_memory_button, validate_config_button, build_info_button, test_llm_button])

    cfg_grid.addLayout(cfg_actions, 5, 0, 1, 2)
    cfg_grid.setColumnStretch(1, 1)

    configuracion_build_layout.addWidget(cfg_panel)
    configuracion_build_layout.addStretch(1)


    # PAGES HIERARCHY SETUP
    pages = [
        ("Próximo sorteo", "Cockpit operativo automático y diversificación estructural.", proximo_sorteo_page),
        ("Comparativa", "Contraste de redundancia y diversidad estructural entre modelos y configuraciones.", comparativa_page),
        ("Carteras", "Consulta e inspección detallada de carteras generadas y notas de auditoría.", carteras_page),
        ("Evaluar resultado", "Carga el resultado oficial para verificar aciertos de la cartera.", evaluar_resultado_page),
        ("Verificador manual", "Valida combinaciones manuales contra las métricas del modelo.", verificador_manual_page),
        ("Aprendizaje", "Recalibración por feedback retrospectivo y perfiles de pesos.", aprendizaje_page),
        ("Auditoría", "Análisis retrospectivo de señales estructurales y backtesting histórico.", auditoria_page),
        ("Historial y herramientas", "Importación de sorteos y herramientas de visualización (Dashboard/Grafo).", historial_herramientas_page),
        ("Configuración / build", "Parámetros locales, guardrails y herramientas de diagnóstico.", configuracion_build_page),
    ]

    def show_page(index: int) -> None:
        title, subtitle, _page = pages[index]
        header_title.setText(title)
        header_subtitle.setText(subtitle)
        stack.setCurrentIndex(index)
        if title == "Historial y herramientas":
            run_action("Actualizar historial", refresh_history_table, False)
            run_action("Actualizar reportes", refresh_reports_table, False)
        elif title == "Carteras":
            run_action("Actualizar carteras", refresh_portfolios, False)
        elif title == "Evaluar resultado":
            update_eval_portfolio_list()
        elif title == "Aprendizaje":
            update_profile_info()

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
    
    suggest_next()

    root_layout.addWidget(sidebar)
    root_layout.addWidget(main, 1)
    window.setCentralWidget(root)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(launch_desktop())
