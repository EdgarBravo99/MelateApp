from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .draw_trace import trace_draw
from .evaluator_brain import brain_review
from .guardrails import validate_output_json
from .memory import DEFAULT_DB_PATH, init_db, remember_draw, remember_played_tickets, remember_postmortem
from .montecarlo_stress import stress_review
from .number_utils import parse_numbers
from .postmortem import postmortem_review
from .report_writer import write_csv_summary, write_html_report, write_json_report


def parse_multiline_tickets(text: str) -> list[list[int]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [parse_numbers(line) for line in lines]


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


def open_report(path: str | Path) -> dict[str, str]:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(str(report_path))
    os.startfile(report_path)  # type: ignore[attr-defined]
    return {"opened": str(report_path)}
