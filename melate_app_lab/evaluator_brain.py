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

from .llm_analyst import LLMAnalystEngine


def _memory_lessons(db_path: Path) -> list[dict[str, object]]:
    if not db_path.exists():
        return []
    return load_recent_lessons(db_path)


def _recent_theses(db_path: Path) -> list[dict[str, object]]:
    if not db_path.exists():
        return []
    try:
        from .thesis_memory import load_recent_theses

        return load_recent_theses(db_path)
    except Exception:
        return []


def brain_review(
    draw: int,
    result_numbers: Iterable[int] | str,
    played_tickets: list[Iterable[int] | str],
    memory_lessons: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return build_deep_review(draw, result_numbers, played_tickets, memory_lessons=memory_lessons)


def build_deep_review(
    draw: int,
    result_numbers: Iterable[int] | str,
    played_tickets: list[Iterable[int] | str],
    memory_lessons: list[dict[str, object]] | None = None,
    historical_records: list[dict[str, object]] | None = None,
    recent_theses: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    result = parse_numbers(result_numbers)
    played = [parse_numbers(ticket) for ticket in played_tickets]
    trace = trace_draw(draw, result)
    postmortem = postmortem_review(draw, result, played)
    graph = build_relation_graph(draw, result, played, postmortem)
    stress = stress_review(result, played)
    lessons = memory_lessons if memory_lessons is not None else _memory_lessons(DEFAULT_DB_PATH)
    theses = recent_theses if recent_theses is not None else _recent_theses(DEFAULT_DB_PATH)
    history_summary: dict[str, object] = {}
    if historical_records:
        from .historical_analysis import summarize_history

        history_summary = summarize_history(historical_records)
    components = {
        "trace": trace,
        "postmortem": postmortem,
        "graph": graph,
        "stress_review": stress,
        "memory_lessons": lessons,
        "recent_theses": theses,
        "history_summary": history_summary,
    }
    narrative = LLMAnalystEngine().review(components, lessons)
    report = {
        "draw": int(draw),
        "result_numbers": result,
        "played_tickets": played,
        **narrative,
        "components": components,
    }
    return validate_output_json(report)
