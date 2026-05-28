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
    from .historical_store import import_draws_to_memory, load_draw_history
    from .importers import parse_draw_csv, parse_draw_json

    records = parse_draw_json(file) if file.suffix.lower() == ".json" else parse_draw_csv(file)
    import_draws_to_memory(records, DEFAULT_DB_PATH)
    history = load_draw_history(DEFAULT_DB_PATH)
    _json({"imported": len(records), "history_count": len(history), "memory_path": str(DEFAULT_DB_PATH)})


@app.command("history-summary")
def history_summary() -> None:
    from .historical_analysis import summarize_history
    from .historical_store import load_draw_history

    history = load_draw_history(DEFAULT_DB_PATH)
    _json(summarize_history(history))


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
