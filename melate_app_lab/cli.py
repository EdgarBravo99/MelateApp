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
from .report_writer import write_html_report, write_json_report


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
    write_json_report(review, json_path)
    write_html_report(review, html_path)
    _json({"draw": draw, "json_path": str(json_path), "html_path": str(html_path)})
