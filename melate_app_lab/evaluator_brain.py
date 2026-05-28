from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .draw_trace import trace_draw
from .guardrails import validate_output_json
from .memory import DEFAULT_DB_PATH, load_recent_lessons
from .montecarlo_stress import stress_review
from .number_utils import parse_numbers
from .postmortem import postmortem_review
from .relation_graph import build_relation_graph


class LLMAnalystStub:
    def review(self, components: dict[str, object], memory_lessons: list[dict[str, object]]) -> dict[str, str]:
        postmortem = components["postmortem"]
        captured = postmortem["captured_numbers"]
        missed = postmortem["missed_numbers"]
        memory_note = (
            f" Memoria local consultada: {len(memory_lessons)} lecciones recientes."
            if memory_lessons
            else " Memoria local sin lecciones previas para este contexto."
        )
        return {
            "diagnosis_es": (
                "Diagnóstico de revisión: el set jugado capturó parte del rastro, "
                "pero dejó abierta una franja alta y un inicio bajo del resultado."
                + memory_note
            ),
            "what_worked_es": f"Funcionó la captura de números {', '.join(map(str, captured))}.",
            "what_was_missed_es": f"No se capturaron {', '.join(map(str, missed))}.",
            "next_cycle_review_thesis_es": (
                "Tesis de revisión siguiente ciclo: ampliar diversidad de firmas, "
                "revisar concentración de anclas y documentar cobertura por bloques."
            ),
            "risk_notes_es": (
                "Notas de revisión: evitar que anclas repetidas reduzcan diversidad del set "
                "y mantener el análisis como postmortem local."
            ),
        }


def _memory_lessons(db_path: Path) -> list[dict[str, object]]:
    if not db_path.exists():
        return []
    return load_recent_lessons(db_path)


def brain_review(
    draw: int,
    result_numbers: Iterable[int] | str,
    played_tickets: list[Iterable[int] | str],
    memory_lessons: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    result = parse_numbers(result_numbers)
    played = [parse_numbers(ticket) for ticket in played_tickets]
    trace = trace_draw(draw, result)
    postmortem = postmortem_review(draw, result, played)
    graph = build_relation_graph(draw, result, played, postmortem)
    stress = stress_review(result, played)
    lessons = memory_lessons if memory_lessons is not None else _memory_lessons(DEFAULT_DB_PATH)
    components = {
        "trace": trace,
        "postmortem": postmortem,
        "graph": graph,
        "stress_review": stress,
        "memory_lessons": lessons,
    }
    narrative = LLMAnalystStub().review(components, lessons)
    report = {
        "draw": int(draw),
        "result_numbers": result,
        "played_tickets": played,
        **narrative,
        "components": components,
    }
    return validate_output_json(report)
