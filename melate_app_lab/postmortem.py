from __future__ import annotations

from collections import Counter
from typing import Iterable

from .draw_trace import trace_draw
from .guardrails import validate_output_json
from .models import TicketReview
from .number_utils import parse_numbers


def _labels(count: int) -> list[str]:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [alphabet[index] if index < len(alphabet) else str(index + 1) for index in range(count)]


def compare_ticket_to_draw(
    ticket_numbers: Iterable[int] | str,
    draw_numbers: Iterable[int] | str,
    label: str | None = None,
) -> dict[str, object]:
    ticket = parse_numbers(ticket_numbers)
    draw = parse_numbers(draw_numbers)
    hit_numbers = sorted(set(ticket) & set(draw))
    review = TicketReview(
        label=label,
        numbers=ticket,
        hits=len(hit_numbers),
        hit_numbers=hit_numbers,
        missed_ticket_numbers=[number for number in ticket if number not in hit_numbers],
        missed_draw_numbers=[number for number in draw if number not in hit_numbers],
    )
    return review.to_dict()


def postmortem_review(
    draw: int,
    result_numbers: Iterable[int] | str,
    played_tickets: list[Iterable[int] | str],
) -> dict[str, object]:
    result = parse_numbers(result_numbers)
    labels = _labels(len(played_tickets))
    comparisons = [
        compare_ticket_to_draw(ticket, result, label=labels[index])
        for index, ticket in enumerate(played_tickets)
    ]
    best_hit_count = max((item["hits"] for item in comparisons), default=0)
    captured_numbers = sorted({number for item in comparisons for number in item["hit_numbers"]})
    played_numbers = [number for ticket in played_tickets for number in parse_numbers(ticket)]
    overused = sorted(number for number, count in Counter(played_numbers).items() if count > 1)
    review = {
        "draw": int(draw),
        "result_numbers": result,
        "ticket_reviews": comparisons,
        "best_matches": [item for item in comparisons if item["hits"] == best_hit_count],
        "captured_numbers": captured_numbers,
        "missed_numbers": [number for number in result if number not in captured_numbers],
        "overused_played_numbers": overused,
        "result_trace": trace_draw(draw, result),
        "lessons_es": [
            "Aprendizaje de auditoría: la captura quedó concentrada en boletos B y C.",
            "La revisión debe observar anclas repetidas y cobertura de bloques antes del cierre.",
        ],
        "next_review_actions_es": [
            "Revisar diversidad de firmas entre boletos.",
            "Contrastar números repetidos contra cobertura total del set jugado.",
            "Registrar el rastro para comparación local posterior.",
        ],
    }
    return validate_output_json(review)
