from __future__ import annotations

import os
import re
import webbrowser
from pathlib import Path
from typing import Any

from .draw_trace import trace_draw
from .evaluator_brain import brain_review
from .guardrails import validate_output_json
from .historical_store import import_draws_to_memory, load_draw_history, suggest_next_draw
from .importers import parse_draw_json, parse_resultados_csv
from .memory import DEFAULT_DB_PATH, init_db, remember_draw, remember_played_tickets, remember_postmortem
from .montecarlo_stress import stress_review
from .number_utils import parse_numbers
from .postmortem import postmortem_review
from .report_writer import write_csv_summary, write_html_report, write_json_report


def parse_played_tickets_flexible(text: str) -> list[list[int]]:
    lines = [re.sub(r"^[A-Za-z]\s*[:.)-]\s*", "", line.strip()) for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        return [parse_numbers(line) for line in lines]
    numbers = [int(value) for value in re.findall(r"\d+", " ".join(lines))]
    if not numbers:
        raise ValueError("Agrega al menos un boleto.")
    if len(numbers) % 6 != 0:
        raise ValueError("Los boletos deben venir en grupos completos de 6 numeros.")
    return [parse_numbers(numbers[index:index + 6]) for index in range(0, len(numbers), 6)]


def parse_multiline_tickets(text: str) -> list[list[int]]:
    return parse_played_tickets_flexible(text)


def suggest_next_draw_from_memory(db_path: str | Path = DEFAULT_DB_PATH) -> int:
    return suggest_next_draw(db_path, game="revancha")


def import_history_file(path: str | Path, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    source = Path(path)
    records = parse_draw_json(source) if source.suffix.lower() == ".json" else parse_resultados_csv(source)
    connection = import_draws_to_memory(records, db_path, skip_duplicates=True)
    history = load_draw_history(connection)
    return validate_output_json({
        "imported": len(records),
        "history_count": len(history),
        "suggested_next_draw": suggest_next_draw(connection, game="revancha"),
        "memory_path": str(db_path),
    })


def load_history_table(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    return load_draw_history(db_path)


def list_report_files(outputs_path: str | Path = "outputs") -> list[dict[str, Any]]:
    root = Path(outputs_path)
    if not root.exists():
        return []
    reports = [
        {"name": path.name, "path": str(path), "type": path.suffix.lower().lstrip("."), "modified": int(path.stat().st_mtime)}
        for path in sorted(root.glob("postmortem_*.*"))
        if path.suffix.lower() in {".html", ".json", ".csv"}
    ]
    return validate_output_json(reports)


def run_trace(draw: int, result_text: str) -> dict[str, Any]:
    return trace_draw(draw, result_text)


def run_postmortem(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    return postmortem_review(draw, parse_numbers(result_text), parse_played_tickets_flexible(played_text))


def run_stress(result_text: str, played_text: str) -> dict[str, Any]:
    return stress_review(parse_numbers(result_text), parse_played_tickets_flexible(played_text))


def run_brain(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    return brain_review(draw, parse_numbers(result_text), parse_played_tickets_flexible(played_text))


def run_remember(draw: int, result_text: str, played_text: str) -> dict[str, Any]:
    result_numbers = parse_numbers(result_text)
    tickets = parse_played_tickets_flexible(played_text)
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
    return validate_output_json({"draw": int(draw), "json_path": str(json_path), "html_path": str(html_path), "csv_path": str(csv_path)})


def open_report(path: str | Path) -> dict[str, str]:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(str(report_path))
    if hasattr(os, "startfile"):
        os.startfile(report_path)  # type: ignore[attr-defined]
    else:
        webbrowser.open(report_path.resolve().as_uri())
    return {"opened": str(report_path)}


def open_outputs_folder(outputs_path: str | Path = "outputs") -> dict[str, str]:
    folder = Path(outputs_path)
    folder.mkdir(parents=True, exist_ok=True)
    return open_report(folder)
