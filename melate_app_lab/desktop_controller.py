from __future__ import annotations

import os
import re
import webbrowser
from pathlib import Path
from typing import Any

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

