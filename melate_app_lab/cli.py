from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .draw_trace import trace_draw
from .evaluator_brain import brain_review
from .guardrails import validate_output_json
from .memory import (
    DEFAULT_DB_PATH,
    init_db,
    remember_draw,
    remember_played_tickets,
    remember_postmortem,
)
from .montecarlo_stress import stress_review
from .number_utils import parse_numbers
from .postmortem import postmortem_review
from .relation_graph import build_relation_graph, export_relation_graph
from .report_writer import write_csv_summary, write_html_report, write_json_report


app = typer.Typer(no_args_is_help=True, add_completion=False)


def _json(data: object) -> None:
    validate_output_json(data)
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _played(values: tuple[str, ...]) -> list[list[int]]:
    if not values:
        raise typer.BadParameter("Agrega al menos un boleto con --played.")
    return [parse_numbers(value) for value in values]


def _played_from_option(first_value: str | None, extras: list[str]) -> list[list[int]]:
    values = tuple([value for value in [first_value, *extras] if value])
    return _played(values)


@app.command()
def trace(draw: Annotated[int, typer.Option()], numbers: Annotated[str, typer.Option()]) -> None:
    result = trace_draw(draw, numbers)
    _json(result)
    typer.echo(f"Huella del sorteo {draw}: {result['block_signature']} | suma {result['sum']}")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def postmortem(
    ctx: typer.Context,
    draw: Annotated[int, typer.Option()],
    result: Annotated[str, typer.Option()],
    played: Annotated[str | None, typer.Option()],
) -> None:
    review = postmortem_review(draw, parse_numbers(result), _played_from_option(played, ctx.args))
    _json(review)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def remember(
    ctx: typer.Context,
    draw: Annotated[int, typer.Option()],
    result: Annotated[str, typer.Option()],
    played: Annotated[str | None, typer.Option()],
) -> None:
    result_numbers = parse_numbers(result)
    played_tickets = _played_from_option(played, ctx.args)
    review = postmortem_review(draw, result_numbers, played_tickets)
    init_db(DEFAULT_DB_PATH)
    remember_draw(DEFAULT_DB_PATH, trace_draw(draw, result_numbers))
    remember_played_tickets(DEFAULT_DB_PATH, draw, played_tickets)
    remember_postmortem(DEFAULT_DB_PATH, review)
    _json({"draw": draw, "memory_path": str(DEFAULT_DB_PATH), "stored": True})


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def graph(
    ctx: typer.Context,
    draw: Annotated[int, typer.Option()],
    result: Annotated[str, typer.Option()],
    played: Annotated[str | None, typer.Option()] = None,
) -> None:
    played_tickets = _played_from_option(played, ctx.args) if played or ctx.args else None
    graph_data = build_relation_graph(draw, parse_numbers(result), played_tickets)
    output_path = Path("outputs") / f"relation_graph_{draw}.json"
    export_relation_graph(graph_data, output_path)
    _json({"draw": draw, "output_path": str(output_path), "graph": graph_data})


@app.command("montecarlo-stress", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def montecarlo_stress_command(
    ctx: typer.Context,
    result: Annotated[str, typer.Option()],
    played: Annotated[str | None, typer.Option()],
    simulations: Annotated[int, typer.Option()] = 1000,
    seed: Annotated[int, typer.Option()] = 4218,
) -> None:
    review = stress_review(
        parse_numbers(result),
        _played_from_option(played, ctx.args),
        simulations=simulations,
        seed=seed,
    )
    _json(review)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def brain(
    ctx: typer.Context,
    draw: Annotated[int, typer.Option()],
    result: Annotated[str, typer.Option()],
    played: Annotated[str | None, typer.Option()],
) -> None:
    review = brain_review(draw, parse_numbers(result), _played_from_option(played, ctx.args))
    _json(review)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def report(
    ctx: typer.Context,
    draw: Annotated[int, typer.Option()],
    result: Annotated[str, typer.Option()],
    played: Annotated[str | None, typer.Option()],
) -> None:
    review = brain_review(draw, parse_numbers(result), _played_from_option(played, ctx.args))
    json_path = Path("outputs") / f"postmortem_{draw}.json"
    html_path = Path("outputs") / f"postmortem_{draw}.html"
    csv_path = Path("outputs") / f"postmortem_{draw}.csv"
    write_json_report(review, json_path)
    write_html_report(review, html_path)
    write_csv_summary(review, csv_path)
    _json({"draw": draw, "json_path": str(json_path), "html_path": str(html_path), "csv_path": str(csv_path)})


@app.command("import-history")
def import_history(file: Annotated[Path, typer.Option("--file")]) -> None:
    if file.suffix.lower() == ".json":
        from .historical_store import import_draws_to_memory, load_draw_history
        from .importers import parse_draw_json

        records = parse_draw_json(file)
        import_draws_to_memory(records, DEFAULT_DB_PATH)
        history = load_draw_history(DEFAULT_DB_PATH)
        _json({"imported": len(records), "history_count": len(history), "memory_path": str(DEFAULT_DB_PATH)})
    else:
        from .resultados_importer import import_resultados_csv_to_memory

        result = import_resultados_csv_to_memory(file, DEFAULT_DB_PATH)
        result["memory_path"] = str(DEFAULT_DB_PATH)
        # Remove sample rows from CLI output for cleanliness
        result.pop("invalid_row_samples", None)
        _json(result)


@app.command("history-summary")
def history_summary() -> None:
    from .historical_analysis import summarize_history
    from .historical_store import load_draw_history

    history = load_draw_history(DEFAULT_DB_PATH)
    _json(summarize_history(history))


@app.command()
def theses(
    count: Annotated[int, typer.Option()] = 10,
    game: Annotated[str, typer.Option()] = "revancha",
) -> None:
    from .candidate_generator import analyze_time_window, generate_candidates, format_candidates_report
    from .historical_store import load_draw_history
    from .relation_graph import build_historical_relation_graph

    history = load_draw_history(DEFAULT_DB_PATH)
    if not history:
        typer.echo("No hay historial en la memoria. Importa resultados primero.")
        raise typer.Exit(1)
    analysis = analyze_time_window(history, window=30)
    graph_data = build_historical_relation_graph(history, window=30, game=game)
    candidates = generate_candidates(analysis, count=count, graph_data=graph_data)
    typer.echo(format_candidates_report(candidates))


@app.command("review-all")
def review_all(
    count: Annotated[int, typer.Option()] = 10,
    game: Annotated[str, typer.Option()] = "revancha",
    notes: Annotated[str, typer.Option()] = None,
    draw: Annotated[int, typer.Option()] = None,
) -> None:
    from .desktop_controller import run_revision_completa

    res = run_revision_completa(DEFAULT_DB_PATH, count=count, game=game, notes=notes, draw=draw)
    _json(res)


@app.command("search-candidates")
def search_candidates_cmd(
    count: Annotated[int, typer.Option()] = 200,
    game: Annotated[str, typer.Option()] = "revancha",
    seed: Annotated[int, typer.Option()] = 42,
) -> None:
    from .candidate_generator import analyze_time_window
    from .candidate_search import search_candidates
    from .historical_store import load_draw_history

    history = load_draw_history(DEFAULT_DB_PATH)
    if not history:
        typer.echo("No hay historial en la memoria. Importa resultados primero.")
        raise typer.Exit(1)
    analysis = analyze_time_window(history, window=30)
    pool = search_candidates(analysis, pool_size=count, seed=seed)
    _json({"candidates": pool, "count": len(pool)})


@app.command("rank-candidates")
def rank_candidates_cmd(
    candidates_list: Annotated[str, typer.Option("--candidates")] = "",
    game: Annotated[str, typer.Option()] = "revancha",
) -> None:
    from .candidate_ranker import rank_candidates
    from .candidate_generator import analyze_time_window
    from .feature_extractor import extract_features
    from .historical_store import load_draw_history
    from .relation_graph import build_historical_relation_graph
    
    import json

    history = load_draw_history(DEFAULT_DB_PATH)
    if not history:
        typer.echo("No hay historial en la memoria. Importa resultados primero.")
        raise typer.Exit(1)

    try:
        cand_list = json.loads(candidates_list)
    except Exception:
        typer.echo("El parámetro --candidates debe ser un JSON válido conteniendo una lista de listas de números.")
        raise typer.Exit(1)

    analysis = analyze_time_window(history, window=30)
    graph_data = build_historical_relation_graph(history, window=30, game=game)
    train_history = history[-30:] if len(history) >= 30 else history

    features = []
    for cand in cand_list:
        feats = extract_features(cand, train_history, history, graph_data)
        features.append(feats)

    common_sigs = analysis.get("common_signatures", [])
    common_bands = analysis.get("common_bands", [])
    ranked = rank_candidates(features, common_sigs, common_bands)
    _json(ranked)


@app.command("backtest")
def backtest_cmd(
    limit: Annotated[int, typer.Option()] = 10,
    game: Annotated[str, typer.Option()] = "revancha",
    seed: Annotated[int, typer.Option()] = 42,
    pool_size: Annotated[int, typer.Option()] = 200,
    top_k: Annotated[int, typer.Option()] = 10,
    use_ml: Annotated[bool, typer.Option()] = False,
) -> None:
    from .desktop_controller import run_backtest_lab, open_report

    res = run_backtest_lab(
        db_path=DEFAULT_DB_PATH,
        limit=limit,
        game=game,
        pool_size=pool_size,
        top_k=top_k,
        seed=seed,
        use_ml=use_ml,
    )
    _json(res)
    open_report(res["html_path"])


@app.command("workflow-loop")
def workflow_loop(
    draw: Annotated[int, typer.Option()],
    game: Annotated[str, typer.Option()] = "revancha",
    pool_size: Annotated[int, typer.Option()] = 100,
    seed: Annotated[int, typer.Option()] = 42,
    played: Annotated[str | None, typer.Option()] = None,
    result: Annotated[str | None, typer.Option()] = None,
) -> None:
    from .workflow_loop import run_unified_workflow

    played_indices = None
    if played is not None:
        played_indices = [int(x) for x in played.replace(",", " ").split()]

    result_numbers = None
    if result is not None:
        result_numbers = parse_numbers(result)

    res = run_unified_workflow(
        db_path=DEFAULT_DB_PATH,
        draw=draw,
        game=game,
        pool_size=pool_size,
        seed=seed,
        played_indices=played_indices,
        result_numbers=result_numbers,
    )
    _json(res)


@app.command()
def desktop() -> None:
    from .desktop_app import launch_desktop

    raise typer.Exit(launch_desktop())



@app.command("build-info")
def build_info_command() -> None:
    from .packaging import build_info

    _json(build_info())


@app.command("guardrail-scan")
def guardrail_scan_command() -> None:
    from scripts.run_guardrail_scan import run_scan

    result = run_scan()
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if result["violations"]:
        raise typer.Exit(1)


@app.command("llm-status")
def llm_status_command() -> None:
    from .llm_provider import get_llm_config

    _json(get_llm_config())


@app.command("evaluate-portfolio")
def evaluate_portfolio_cmd(
    portfolio_id: Annotated[int, typer.Option("--portfolio-id")],
    result: Annotated[str, typer.Option("--result")],
    game: Annotated[str, typer.Option("--game")] = "revancha",
) -> None:
    """Evalua una cartera de candidatos existente contra un resultado oficial sin generar nuevos candidatos."""
    from .portfolio_evaluator import evaluate_existing_portfolio
    result_numbers = parse_numbers(result)
    res = evaluate_existing_portfolio(
        db_path=DEFAULT_DB_PATH,
        portfolio_id=portfolio_id,
        result_numbers=result_numbers,
        game=game,
        persist=True,
    )
    _json(res)


@app.command("learn-feedback")
def learn_feedback_cmd(
    game: Annotated[str, typer.Option("--game")] = "revancha",
    seed: Annotated[int, typer.Option("--seed")] = 42,
) -> None:
    """Ejecuta el aprendizaje sobre carteras revisadas para recalibrar pesos."""
    from .feedback_learner import learn_from_reviewed_portfolios
    res = learn_from_reviewed_portfolios(
        db_path=DEFAULT_DB_PATH,
        game=game,
        seed=seed,
    )
    _json(res)

