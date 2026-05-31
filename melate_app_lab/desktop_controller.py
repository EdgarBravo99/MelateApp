from __future__ import annotations

import os
import re
import webbrowser
from pathlib import Path
from typing import Any, Callable

from .draw_trace import trace_draw
from .evaluator_brain import brain_review
from .guardrails import validate_output_json
from .historical_store import import_draws_to_memory, load_draw_history
from .importers import parse_draw_csv, parse_draw_json
from .memory import DEFAULT_DB_PATH, init_db, remember_draw, remember_played_tickets, remember_postmortem
from .montecarlo_stress import stress_review
from .number_utils import parse_numbers
from .postmortem import postmortem_review
from .report_writer import write_csv_summary, write_html_report, write_json_report


def _ensure_db_parent(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def parse_ticket(text: str) -> list[int]:
    numbers = parse_numbers(text)
    if len(numbers) != 6:
        raise ValueError(f"El resultado debe contener exactamente 6 numeros (se encontraron {len(numbers)}).")
    
    out_of_range = [number for number in numbers if number < 1 or number > 56]
    if out_of_range:
        raise ValueError(f"Numeros fuera de rango 1-56: {out_of_range}.")

    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        raise ValueError(f"Numeros duplicados en el resultado: {duplicates}.")
        
    return numbers


def parse_played_tickets_flexible(text: str) -> list[list[int]]:
    for match in re.findall(r"\d+", text):
        if len(match) > 2:
            raise ValueError(
                "Cada boleto debe tener 6 números separados por espacio, coma, tab o salto de línea."
            )

    numbers = [int(match) for match in re.findall(r"\d+", text)]
    if not numbers:
        return []

    leftover = len(numbers) % 6
    if leftover:
        raise ValueError(
            "Cada boleto debe tener 6 números separados por espacio, coma, tab o salto de línea."
        )

    tickets: list[list[int]] = []
    for offset in range(0, len(numbers), 6):
        ticket = numbers[offset : offset + 6]
        out_of_range = [number for number in ticket if number < 1 or number > 56]
        if out_of_range:
            raise ValueError(
                "Cada boleto debe tener 6 números separados por espacio, coma, tab o salto de línea."
            )

        duplicates = sorted({number for number in ticket if ticket.count(number) > 1})
        if duplicates:
            raise ValueError(
                "Cada boleto debe tener 6 números separados por espacio, coma, tab o salto de línea."
            )

        tickets.append(ticket)

    return tickets


def parse_multiline_tickets(text: str) -> list[list[int]]:
    return parse_played_tickets_flexible(text)


def suggest_next_draw_from_memory(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    from .historical_store import suggest_next_draw, load_draw_history
    _ensure_db_parent(db_path)
    next_draw = suggest_next_draw(db_path)
    history = load_draw_history(db_path)
    return validate_output_json(
        {
            "next_draw": next_draw,
            "history_count": len(history),
            "memory_path": str(db_path),
            "review_default": {
                "mode": "review_default",
                "notes_es": "Sugerencia local basada en el sorteo historico mas alto en memoria.",
            },
        }
    )


def import_history_file(path: str | Path, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    _ensure_db_parent(db_path)
    history_path = Path(path)
    suffix = history_path.suffix.casefold()
    if suffix == ".csv":
        from .resultados_importer import import_resultados_csv_to_memory
        res = import_resultados_csv_to_memory(history_path, db_path)
        res["memory_path"] = str(db_path)
        res["review_default"] = {
            "mode": "review_default",
            "notes_es": "Historial importado en memoria local.",
        }
        return validate_output_json(res)
    elif suffix == ".json":
        records = parse_draw_json(history_path)
        import_draws_to_memory(records, db_path)
        history = load_draw_history(db_path)
        return validate_output_json(
            {
                "imported": len(records),
                "history_count": len(history),
                "memory_path": str(db_path),
                "review_default": {
                    "mode": "review_default",
                    "notes_es": "Historial importado en memoria local.",
                },
            }
        )
    else:
        raise ValueError("History file must be .csv or .json.")


def load_history_table(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    _ensure_db_parent(db_path)
    return validate_output_json(load_draw_history(db_path))


def list_report_files(outputs_path: str | Path = "outputs") -> list[dict[str, str]]:
    outputs = Path(outputs_path)
    if not outputs.exists():
        return []

    report_files = [
        path
        for path in outputs.iterdir()
        if path.is_file() and path.suffix.casefold() in {".csv", ".html", ".json"}
    ]
    return validate_output_json(
        [
            {"name": path.name, "path": str(path), "extension": path.suffix.casefold().lstrip(".")}
            for path in sorted(report_files, key=lambda item: item.name.casefold())
        ]
    )


def open_outputs_folder() -> dict[str, str]:
    outputs = Path("outputs")
    outputs.mkdir(exist_ok=True)
    return open_report(outputs)


def run_trace(draw: int, result_text: str) -> dict[str, Any]:
    return trace_draw(draw, result_text)


def run_postmortem(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    return postmortem_review(draw, parse_numbers(result_text), parse_multiline_tickets(played_text))


def run_stress(result_text: str, played_text: str) -> dict[str, Any]:
    return stress_review(parse_numbers(result_text), parse_multiline_tickets(played_text))


def run_brain(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    return brain_review(draw, parse_numbers(result_text), parse_multiline_tickets(played_text))


def run_remember(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    result_numbers = parse_numbers(result_text)
    tickets = parse_multiline_tickets(played_text)
    postmortem = postmortem_review(draw, result_numbers, tickets)
    init_db(DEFAULT_DB_PATH)
    remember_draw(DEFAULT_DB_PATH, trace_draw(draw, result_numbers))
    remember_played_tickets(DEFAULT_DB_PATH, draw, tickets)
    remember_postmortem(DEFAULT_DB_PATH, postmortem)
    return validate_output_json({"draw": int(draw), "memory_path": str(DEFAULT_DB_PATH), "stored": True})


def run_report(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    report = run_brain(draw, result_text, played_text)
    json_path = Path("outputs") / f"postmortem_{draw}.json"
    html_path = Path("outputs") / f"postmortem_{draw}.html"
    csv_path = Path("outputs") / f"postmortem_{draw}.csv"
    write_json_report(report, json_path)
    write_html_report(report, html_path)
    write_csv_summary(report, csv_path)
    return validate_output_json(
        {"draw": int(draw), "json_path": str(json_path), "html_path": str(html_path), "csv_path": str(csv_path)}
    )


def initialize_memory(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    init_db(db_path)
    return validate_output_json({"memory_path": str(db_path), "initialized": True})


def run_guardrail_scan() -> dict[str, Any]:
    from scripts.run_guardrail_scan import run_scan
    return validate_output_json(run_scan())


def get_build_info() -> dict[str, Any]:
    from .packaging import build_info
    return validate_output_json(build_info())


def run_history_summary(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    from .historical_analysis import summarize_history
    history = load_draw_history(db_path)
    return validate_output_json(summarize_history(history))


def validate_desktop_config(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    return validate_output_json({
        "db_path": str(db_path),
        "db_exists": Path(db_path).exists(),
        "outputs_path": str(Path("outputs").resolve())
    })


def test_llm_connection() -> dict[str, Any]:
    from .llm_provider import call_llm, get_llm_config
    config = get_llm_config()
    if config["provider"] in ("disabled", "local_stub"):
        return validate_output_json({"status": "disabled", "message": "Analista LLM desactivado; usando analista local."})
    res = call_llm("Prueba de conexion", system_prompt="Responde solo 'OK' en JSON: {\"status\": \"OK\"}")
    if res:
        return validate_output_json({"status": "success", "message": f"Conexion exitosa a {config['provider']}"})
    return validate_output_json({"status": "error", "message": "Fallo la conexion al proveedor LLM configurado."})

def open_report(path: str | Path) -> dict[str, str]:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(str(report_path))
    if hasattr(os, "startfile"):
        os.startfile(report_path)  # type: ignore[attr-defined]
    else:
        webbrowser.open(report_path.resolve().as_uri())
    return {"opened": str(report_path)}


def run_generate_candidates(db_path: str | Path = DEFAULT_DB_PATH, count: int = 10) -> dict[str, Any]:
    from .historical_store import load_draw_history
    from .candidate_generator import analyze_time_window, generate_candidates, format_candidates_report
    from .relation_graph import build_historical_relation_graph
    history = load_draw_history(db_path)
    if not history:
        raise ValueError("No hay historial en la memoria para generar candidatos. Importa resultados primero.")
    analysis = analyze_time_window(history, window=30)
    graph_data = build_historical_relation_graph(history, window=30, game="revancha")
    candidates = generate_candidates(analysis, count=count, graph_data=graph_data)
    report_text = format_candidates_report(candidates)
    return validate_output_json({
        "candidates": candidates,
        "report_text": report_text,
        "history_count": len(history),
        "review_default": {
            "mode": "review_default",
            "notes_es": "Tesis y combinaciones candidatas generadas con exito."
        }
    })


def run_graph_visualization(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    from .relation_graph import build_relation_graph
    from .report_writer import write_graph_html_report
    # parse input strings first
    result_numbers = parse_numbers(result_text)
    tickets = parse_played_tickets_flexible(played_text)
    graph = build_relation_graph(draw, result_numbers, tickets)
    html_path = Path("outputs") / f"relation_graph_{draw}.html"
    write_graph_html_report(graph, html_path)
    open_report(html_path)
    return validate_output_json({
        "draw": int(draw),
        "html_path": str(html_path),
        "review_default": {
            "mode": "review_default",
            "notes_es": f"Grafo postmortem del sorteo {draw} generado y abierto."
        }
    })


def run_historical_graph(db_path: str | Path = DEFAULT_DB_PATH, window: int = 30) -> dict[str, Any]:
    from .historical_store import load_draw_history
    from .relation_graph import build_historical_relation_graph
    from .report_writer import write_graph_html_report
    from .candidate_generator import analyze_time_window, generate_candidates
    history = load_draw_history(db_path)
    if not history:
        raise ValueError("No hay historial en la memoria para generar el grafo. Importa resultados primero.")
    graph_data = build_historical_relation_graph(history, window=window, game="revancha")
    analysis = analyze_time_window(history, window=window)
    candidates = generate_candidates(analysis, count=10, graph_data=graph_data)
    graph_data["candidates"] = candidates
    html_path = Path("outputs") / "historical_graph.html"
    write_graph_html_report(graph_data, html_path)
    open_report(html_path)
    return validate_output_json({
        "html_path": str(html_path),
        "history_count": len(history),
        "window": window,
        "review_default": {
            "mode": "review_default",
            "notes_es": f"Grafo historico de Revancha (ultimos {window} sorteos) generado y abierto."
        }
    })


def run_history_dashboard(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    from .historical_store import load_draw_history
    from .report_writer import write_history_dashboard_html
    history = load_draw_history(db_path)
    if not history:
        raise ValueError("No hay historial en la memoria para generar el dashboard. Importa resultados primero.")
    html_path = Path("outputs") / "history_dashboard.html"
    write_history_dashboard_html(history, html_path)
    open_report(html_path)
    return validate_output_json({
        "html_path": str(html_path),
        "history_count": len(history),
        "review_default": {
            "mode": "review_default",
            "notes_es": "Dashboard historico generado y abierto."
        }
    })


def run_revision_completa(
    db_path: str | Path = DEFAULT_DB_PATH,
    count: int = 10,
    game: str = "revancha",
    notes: str | None = None,
    draw: int | None = None,
    use_structural_diversification: bool = False,
    structural_diversity_weight: float = 1.0,
) -> dict[str, Any]:
    from .historical_store import load_draw_history, suggest_next_draw
    from .candidate_generator import analyze_time_window, generate_candidates
    from .relation_graph import build_historical_relation_graph
    from .thesis_memory import save_thesis_portfolio, load_thesis_portfolios
    from .number_utils import analyze_portfolio_redundancy
    from .report_writer import write_consolidated_portfolio_report_html, write_graph_html_report

    _ensure_db_parent(db_path)
    history = load_draw_history(db_path)
    if not history:
        raise ValueError("No hay historial en la memoria para realizar la revisión. Importa resultados primero.")

    next_draw = draw if draw is not None else suggest_next_draw(db_path)
    analysis = analyze_time_window(history, window=30)
    graph_data = build_historical_relation_graph(history, window=30, game=game)

    if not use_structural_diversification:
        candidates = generate_candidates(analysis, count=count, graph_data=graph_data)
        # Assign letter labels
        for idx, cand in enumerate(candidates):
            cand["letter"] = chr(ord('A') + idx)
    else:
        # Generar pool mayor y aplicar diversificación
        pool_size = max(100, count * 10)
        pool = generate_candidates(analysis, count=pool_size, seed=4218, graph_data=graph_data)
        
        # Calcular campos necesarios para el ranker actual
        for cand in pool:
            nums = cand["numbers"]
            cand["even_count"] = sum(1 for n in nums if n % 2 == 0)
            cand["odd_count"] = 6 - cand["even_count"]
            cand["diversity_score"] = cand["block_presence_signature"].count("1")
            cand["pair_edges_count"] = len(cand.get("pair_edges", []))
            cand["historical_exact_match"] = False
            
        from .candidate_ranker import rank_candidates
        common_sigs = analysis.get("common_signatures", [])
        common_bands = analysis.get("common_bands", [])
        ranked = rank_candidates(pool, common_sigs, common_bands)
        
        # Calcular senales estructurales
        prior_history = [d for d in history if d["draw"] < next_draw]
        if not prior_history:
            prior_history = history
        from .structural_signal_engine import compute_structural_signals_batch
        ranked = compute_structural_signals_batch(ranked, prior_history, window=30, gap_window=50, max_lag=5)
        
        # Optimizar cartera usando diversificación estructural
        from .portfolio_optimizer import optimize_portfolio
        candidates = optimize_portfolio(
            ranked,
            count,
            use_structural_diversification=True,
            structural_diversity_weight=structural_diversity_weight
        )
        
        # Formatear el campo notes para guardar en la base de datos
        import json
        for c in candidates:
            c["notes"] = json.dumps({
                "rank_score": c.get("rank_score", 0.0),
                "structural_signal_score": c.get("structural_signal_score", 0.0),
                "pair_lag_score": c.get("pair_lag_score", 0.0),
                "block_activity_score": c.get("block_activity_score", 0.0),
                "gap_echo_score": c.get("gap_echo_score", 0.0),
                "gap_family": c.get("gap_family", ""),
                "selection_reason": c.get("selection_reason", ""),
                "structural_notes": c.get("structural_notes", []),
            })
            
        # Asignar etiquetas de letras
        for idx, cand in enumerate(candidates):
            cand["letter"] = chr(ord('A') + idx)

    # Save portfolio
    portfolio_id = save_thesis_portfolio(
        db_path, draw=next_draw, game=game, candidates=candidates, notes=notes
    )

    # Load recent portfolio to match database state
    ports = load_thesis_portfolios(db_path, limit=1)
    portfolio = ports[0] if ports else {
        "id": portfolio_id,
        "draw": next_draw,
        "game": game,
        "notes": notes or "",
        "created_at": ""
    }

    # Redundancy analysis
    redundancy = analyze_portfolio_redundancy(candidates)

    # Generate consolidated portfolio report
    portfolio_report_path = Path("outputs") / f"portfolio_report_{next_draw}.html"
    write_consolidated_portfolio_report_html(portfolio, candidates, redundancy, portfolio_report_path)

    # Generate historical graph report
    graph_data["candidates"] = candidates
    graph_html_path = Path("outputs") / f"historical_graph_{next_draw}.html"
    write_graph_html_report(graph_data, graph_html_path)

    # Open reports
    open_report(portfolio_report_path)
    open_report(graph_html_path)

    return validate_output_json({
        "portfolio_id": portfolio_id,
        "portfolio_report_path": str(portfolio_report_path),
        "graph_html_path": str(graph_html_path),
        "next_draw": next_draw,
        "history_count": len(history),
        "review_default": {
            "mode": "review_default",
            "notes_es": f"Revisión completa ejecutada. Cartera de tesis (ID: {portfolio_id}) guardada y reportes abiertos."
        }
    })


def load_portfolios_list(db_path: str | Path = DEFAULT_DB_PATH, limit: int = 10) -> list[dict[str, Any]]:
    from .thesis_memory import load_thesis_portfolios
    _ensure_db_parent(db_path)
    return validate_output_json(load_thesis_portfolios(db_path, limit))


def load_portfolio_candidates(db_path: str | Path = DEFAULT_DB_PATH, portfolio_id: int = 0) -> list[dict[str, Any]]:
    from .thesis_memory import load_thesis_candidates
    _ensure_db_parent(db_path)
    return validate_output_json(load_thesis_candidates(db_path, portfolio_id))


def change_candidate_state(db_path: str | Path = DEFAULT_DB_PATH, candidate_id: int = 0, state: str = "Pendiente") -> None:
    from .thesis_memory import update_candidate_state
    _ensure_db_parent(db_path)
    update_candidate_state(db_path, candidate_id, state)


def save_candidate_review(db_path: str | Path = DEFAULT_DB_PATH, candidate_id: int = 0, result_numbers: list[int] = [], hits_count: int = 0) -> None:
    from .thesis_memory import update_candidate_review_result
    _ensure_db_parent(db_path)
    update_candidate_review_result(db_path, candidate_id, result_numbers, hits_count)


def evaluate_portfolio_against_history(db_path: str | Path = DEFAULT_DB_PATH, portfolio_id: int = 0) -> dict[str, Any]:
    from .thesis_memory import load_thesis_candidates, update_candidate_review_result, load_thesis_portfolios
    from .historical_store import load_draw_history

    _ensure_db_parent(db_path)
    candidates = load_thesis_candidates(db_path, portfolio_id)
    if not candidates:
        return {"evaluated": 0, "message": "No hay candidatos en este portfolio."}

    portfolios = load_thesis_portfolios(db_path, limit=100)
    port = next((p for p in portfolios if p["id"] == portfolio_id), None)
    if not port:
        return {"evaluated": 0, "message": "Portfolio no encontrado."}

    draw_num = port["draw"]

    history = load_draw_history(db_path)
    draw_record = next((d for d in history if d["draw"] == draw_num), None)
    if not draw_record:
        return {
            "evaluated": 0,
            "message": f"El sorteo {draw_num} no esta en el historial en memoria. Importa resultados mas recientes primero."
        }

    result_numbers = draw_record["numbers"]
    result_set = set(result_numbers)

    evaluated_count = 0
    for cand in candidates:
        cand_set = set(cand["numbers"])
        hits = len(cand_set & result_set)
        update_candidate_review_result(db_path, cand["id"], result_numbers, hits)
        evaluated_count += 1

    return {
        "evaluated": evaluated_count,
        "draw": draw_num,
        "result_numbers": result_numbers,
        "message": f"Se evaluaron {evaluated_count} candidatos contra el sorteo {draw_num} ({' '.join(map(str, result_numbers))})."
    }


def run_backtest_lab(
    db_path: str | Path = DEFAULT_DB_PATH,
    limit: int = 10,
    game: str = "revancha",
    pool_size: int = 200,
    top_k: int = 10,
    seed: int = 42,
    use_ml: bool = False,
    use_optimizer: bool = False,
    use_feedback_profile: bool = False,
    log_fn: Callable[[str], None] | None = None,
    use_structural_diversification: bool = False,
    structural_diversity_weight: float = 1.0,
) -> dict[str, Any]:
    from .historical_store import load_draw_history
    from .backtest_lab import run_backtest
    from .report_writer import write_backtest_report_html

    _ensure_db_parent(db_path)
    history = load_draw_history(db_path)
    if not history:
        raise ValueError("No hay historial en la memoria para el backtesting. Importa resultados primero.")

    filtered = [d for d in history if str(d.get("game", "")).casefold() == game.casefold()]
    filtered.sort(key=lambda d: d.get("draw", 0))

    if not filtered:
        raise ValueError(f"No hay sorteos en el historial para el juego: {game}")

    target_draws = [d["draw"] for d in filtered[-limit:]]

    results = run_backtest(
        history=history,
        target_draws=target_draws,
        window=30,
        pool_size=pool_size,
        top_k=top_k,
        seed=seed,
        game=game,
        use_ml=use_ml,
        use_optimizer=use_optimizer,
        use_feedback_profile=use_feedback_profile,
        db_path=db_path,
        log_fn=log_fn,
        use_structural_diversification=use_structural_diversification,
        structural_diversity_weight=structural_diversity_weight,
    )

    html_path = Path("outputs") / "backtest_report.html"
    write_backtest_report_html(results, html_path)
    results["html_path"] = str(html_path)

    return validate_output_json(results)


def is_ml_supported() -> bool:
    from .ml_ranker import is_ml_available
    return is_ml_available()


def run_evaluate_portfolio(
    db_path: str | Path,
    portfolio_id: int,
    result_text: str,
    game: str = "revancha",
) -> dict[str, Any]:
    from .portfolio_evaluator import evaluate_existing_portfolio
    from .number_utils import parse_numbers
    result_numbers = parse_numbers(result_text)
    _ensure_db_parent(db_path)
    return validate_output_json(
        evaluate_existing_portfolio(
            db_path=db_path,
            portfolio_id=portfolio_id,
            result_numbers=result_numbers,
            game=game,
            persist=True,
        )
    )


def run_learn_feedback(
    db_path: str | Path,
    game: str = "revancha",
    seed: int = 42,
) -> dict[str, Any]:
    from .feedback_learner import learn_from_reviewed_portfolios
    _ensure_db_parent(db_path)
    return validate_output_json(
        learn_from_reviewed_portfolios(
            db_path=db_path,
            game=game,
            seed=seed,
        )
    )


def load_active_profile_info(
    db_path: str | Path,
    game: str = "revancha",
) -> dict[str, Any] | None:
    from .thesis_memory import get_active_feedback_profile
    _ensure_db_parent(db_path)
    profile = get_active_feedback_profile(db_path, game)
    if not profile:
        return None
    return validate_output_json({
        "id": profile["id"],
        "game": profile["game"],
        "source_from_draw": profile["source_from_draw"],
        "source_to_draw": profile["source_to_draw"],
        "algorithm": profile["algorithm"],
        "metrics": profile["metrics"],
        "active": profile["active"],
        "created_at": profile["created_at"],
    })


def run_internal_portfolio_checks(portfolio: list[dict[str, Any]]) -> dict[str, Any]:
    from .metrics import average_internal_overlap, high_redundancy_pairs
    if not portfolio:
        return {
            "status": "review",
            "average_internal_overlap": 0.0,
            "high_redundancy_pairs": 0,
            "unique_block_signatures": 0,
            "unique_gap_families": 0,
            "average_rank_score": 0.0,
            "average_structural_signal_score": 0.0,
            "message": "Cartera vacía."
        }
    
    nums_only = [c["numbers"] for c in portfolio]
    avg_overlap = average_internal_overlap(nums_only)
    high_red = high_redundancy_pairs(nums_only)
    
    avg_rank = sum(c.get("rank_score", 0.0) for c in portfolio) / len(portfolio)
    
    # Check if structural signals exist (could be nested in 'structural' or keys are structural_signal_score)
    struct_scores = []
    for c in portfolio:
        if "structural" in c and isinstance(c["structural"], dict):
            struct_scores.append(c["structural"].get("structural_signal_score", 0.0))
        else:
            struct_scores.append(c.get("structural_signal_score", 0.0))
            
    avg_struct = sum(struct_scores) / len(portfolio) if struct_scores else 0.0
    
    unique_sigs = len({c.get("block_signature", "") for c in portfolio if c.get("block_signature")})
    unique_gaps = len({c.get("gap_family", "") for c in portfolio if c.get("gap_family")})
    
    # Decide status
    if avg_overlap > 2.8 or high_red > 4:
        status = "atypical"
        msg = "Alta redundancia en la cartera (solapamiento > 2.8 o parejas muy redundantes)."
    elif avg_overlap > 2.3 or high_red >= 2:
        status = "review"
        msg = "Redundancia moderada detectada. Se recomienda revisión de parámetros."
    else:
        status = "stable"
        msg = "Cartera estable. Niveles de redundancia y dispersión dentro de rangos normales."
        
    return {
        "status": status,
        "average_internal_overlap": round(avg_overlap, 4),
        "high_redundancy_pairs": high_red,
        "unique_block_signatures": unique_sigs,
        "unique_gap_families": unique_gaps,
        "average_rank_score": round(avg_rank, 4),
        "average_structural_signal_score": round(avg_struct, 4),
        "message": msg
    }


def generate_automatic_review(
    db_path: str | Path = DEFAULT_DB_PATH,
    game: str = "revancha",
    draw: int | None = None,
    count: int = 10,
    pool_size: int = 1000,
    seed: int = 42,
    use_structural_diversification: bool = True,
    structural_diversity_weight: float = 1.0,
    include_statistical_crosscheck: bool = True,
    use_optimizer: bool = True,
    use_feedback_profile: bool = False,
    use_ml: bool = False,
    ml_model: str | None = None,
    auto_save: bool = False,
    notes: str | None = None,
) -> dict[str, Any]:
    import json
    from .historical_store import load_draw_history, suggest_next_draw
    from .candidate_generator import analyze_time_window
    from .candidate_search import search_candidates
    from .feature_extractor import extract_features
    from .relation_graph import build_historical_relation_graph
    from .candidate_ranker import rank_candidates
    from .structural_signal_engine import compute_structural_signals_batch
    from .statistical_crosscheck import (
        analyze_candidate_statistical_profile,
        analyze_portfolio_statistical_profile,
    )
    from .thesis_memory import save_thesis_portfolio

    _ensure_db_parent(db_path)
    history = load_draw_history(db_path)
    if not history:
        return {
            "success": False,
            "errors": ["El historial en la base de datos está vacío."],
        }

    target_draw = draw if draw is not None else suggest_next_draw(db_path)
    prior_history = [d for d in history if d["draw"] < target_draw]
    if not prior_history:
        prior_history = history

    # 1. Analyze window & build graph
    analysis = analyze_time_window(prior_history, window=30)
    graph_data = build_historical_relation_graph(prior_history, window=30, game=game)

    # 2. Generate Candidate Pool
    effective_pool_size = max(pool_size, count * 2)
    candidate_pool = search_candidates(analysis, pool_size=effective_pool_size, seed=seed)

    # 3. Extract Features
    cand_features = []
    train_history = prior_history[-30:] if len(prior_history) >= 30 else prior_history
    for cand in candidate_pool:
        feats = extract_features(cand, train_history, prior_history, graph_data)
        cand_features.append(feats)

    # 4. Rank Candidates
    common_sigs = analysis.get("common_signatures", [])
    common_bands = analysis.get("common_bands", [])

    # Load feedback weights if active
    weights = None
    if use_feedback_profile:
        from .thesis_memory import get_active_feedback_profile
        active_profile = get_active_feedback_profile(db_path, game)
        if active_profile:
            weights = active_profile["weights"]

    ranked = rank_candidates(cand_features, common_sigs, common_bands, weights=weights)

    # 5. ML Scoring if active
    if use_ml:
        from .ml_ranker import is_ml_available, train_ml_ranker, rank_candidates_ml
        if is_ml_available():
            prior_draw_ids = [d["draw"] for d in prior_history]
            ml_train_draws = prior_draw_ids[-30:] if len(prior_draw_ids) >= 30 else prior_draw_ids
            model = train_ml_ranker(history, ml_train_draws, window=30, game=game)
            ml_res = rank_candidates_ml(model, ranked, common_sigs, common_bands)
            if ml_res:
                ranked = ml_res

    # 6. Compute Structural Signals
    ranked = compute_structural_signals_batch(ranked, prior_history, window=30, gap_window=50, max_lag=5)

    # 7. Select Portfolio (Optimizer / Top-k)
    if use_optimizer:
        from .portfolio_optimizer import optimize_portfolio
        final_portfolio = optimize_portfolio(
            ranked,
            count,
            use_structural_diversification=use_structural_diversification,
            structural_diversity_weight=structural_diversity_weight,
        )
    else:
        final_portfolio = ranked[:count]

    # Assign Letter Labels & Extract Statistical Profiles
    for idx, c in enumerate(final_portfolio):
        c["letter"] = chr(ord('A') + idx)
        if include_statistical_crosscheck:
            c["statistical_crosscheck"] = analyze_candidate_statistical_profile(c["numbers"], prior_history)
        else:
            c["statistical_crosscheck"] = {}

    # 8. Run Portfolio statistical check & internal checks
    port_stat_prof = {}
    if include_statistical_crosscheck:
        port_stat_prof = analyze_portfolio_statistical_profile(final_portfolio, prior_history)

    internal_checks = run_internal_portfolio_checks(final_portfolio)

    portfolio_id = None
    if auto_save:
        # Build candidate payloads for DB
        db_candidates = []
        for idx, c in enumerate(final_portfolio):
            c_notes = {
                "label": c["letter"],
                "rank_score": round(c.get("rank_score", 0.0), 4),
                "selection_reason": c.get("selection_reason", "Selección automática del cockpit"),
                "source": "automatic_review",
                "structural": {
                    "structural_signal_score": round(c.get("structural_signal_score", 0.0), 4),
                    "pair_lag_score": round(c.get("pair_lag_score", 0.0), 4),
                    "block_activity_score": round(c.get("block_activity_score", 0.0), 4),
                    "gap_echo_score": round(c.get("gap_echo_score", 0.0), 4),
                    "block_signature": c.get("block_signature", ""),
                    "gap_family": c.get("gap_family", ""),
                },
                "statistical_crosscheck": c.get("statistical_crosscheck", {}),
            }
            from .workflow_loop import classify_candidate
            strat = classify_candidate(c)
            db_candidates.append({
                "numbers": c["numbers"],
                "classification": strat,
                "graph_support_score": c.get("graph_support_score", 0.0),
                "notes": json.dumps(c_notes, ensure_ascii=False),
            })

        portfolio_notes = {
            "source": "automatic_review",
            "user_notes": notes or "",
            "config": {
                "game": game,
                "draw": target_draw,
                "seed": seed,
                "pool_size": pool_size,
                "use_structural_diversification": use_structural_diversification,
                "structural_diversity_weight": structural_diversity_weight,
                "use_optimizer": use_optimizer,
                "use_feedback_profile": use_feedback_profile,
                "use_ml": use_ml,
            },
            "metrics": internal_checks,
            "portfolio_statistical_profile": port_stat_prof,
        }

        portfolio_id = save_thesis_portfolio(
            db_path=db_path,
            draw=target_draw,
            game=game,
            candidates=db_candidates,
            notes=json.dumps(portfolio_notes, ensure_ascii=False),
        )

    return {
        "success": True,
        "portfolio_id": portfolio_id,
        "final_portfolio": final_portfolio,
        "internal_checks": internal_checks,
        "portfolio_statistical_profile": port_stat_prof,
        "next_draw": target_draw,
        "history_count": len(history),
        "game": game,
        "notes": notes,
    }





