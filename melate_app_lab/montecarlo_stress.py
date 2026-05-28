from __future__ import annotations

import random
from collections import Counter
from typing import Iterable

from .guardrails import validate_output_json
from .number_utils import block_presence_signature, block_signature, parse_numbers, sum_band


def generate_random_ticket(rng: random.Random | None = None) -> list[int]:
    source = rng or random.Random()
    return sorted(source.sample(range(1, 57), 6))


def summarize_structural_coverage(tickets: list[Iterable[int] | str]) -> dict[str, object]:
    parsed = [parse_numbers(ticket) for ticket in tickets]
    signatures = Counter(block_signature(ticket) for ticket in parsed)
    presence = Counter(block_presence_signature(ticket) for ticket in parsed)
    bands = Counter(sum_band(sum(ticket)) for ticket in parsed)
    repeated = Counter(number for ticket in parsed for number in ticket)
    return {
        "ticket_count": len(parsed),
        "unique_numbers_count": len(repeated),
        "block_signatures": dict(sorted(signatures.items())),
        "block_presence_signatures": dict(sorted(presence.items())),
        "sum_bands": dict(sorted(bands.items())),
        "repeated_numbers": sorted(number for number, count in repeated.items() if count > 1),
    }


def stress_review(
    result_numbers: Iterable[int] | str,
    played_tickets: list[Iterable[int] | str],
    simulations: int = 1000,
    seed: int = 4218,
) -> dict[str, object]:
    result = parse_numbers(result_numbers)
    played = [parse_numbers(ticket) for ticket in played_tickets]
    rng = random.Random(seed)
    sample_tickets = [generate_random_ticket(rng) for _ in range(simulations)]
    played_coverage = summarize_structural_coverage(played)
    sample_coverage = summarize_structural_coverage(sample_tickets)
    repeated_counts = Counter(number for ticket in played for number in ticket)
    repeated_numbers = sorted(number for number, count in repeated_counts.items() if count > 1)
    played_blocks = {
        block
        for signature in played_coverage["block_presence_signatures"]
        for block, present in enumerate(signature.split("-"), start=1)
        if present == "1"
    }
    result_structure = {
        "numbers": result,
        "sum": sum(result),
        "sum_band": sum_band(sum(result)),
        "block_signature": block_signature(result),
        "block_presence_signature": block_presence_signature(result),
    }
    review = {
        "result_structure": result_structure,
        "played_coverage": played_coverage,
        "anchor_concentration": {
            "repeated_numbers": repeated_numbers,
            "max_repeat_count": max(repeated_counts.values()) if repeated_counts else 0,
        },
        "band_coverage": {
            "played_sum_bands": played_coverage["sum_bands"],
            "reference_sample_sum_bands": sample_coverage["sum_bands"],
        },
        "signature_coverage": {
            "played_block_signatures": played_coverage["block_signatures"],
            "played_presence_signatures": played_coverage["block_presence_signatures"],
            "distinct_signature_count": len(played_coverage["block_signatures"]),
        },
        "redundancy_notes_es": [
            f"Concentración detectada en anclas repetidas: {repeated_numbers}."
            if repeated_numbers
            else "Sin concentración fuerte de anclas repetidas en el set jugado."
        ],
        "missing_coverage_es": [
            "La cobertura estructural debe revisarse contra bloques presentes y firmas repetidas.",
            f"Bloques con presencia en jugadas: {sorted(played_blocks)}.",
        ],
        "review_alerts_es": [
            "Alerta de revisión: revisar dependencia de números repetidos entre boletos.",
            "Alerta de revisión: contrastar diversidad de firmas antes del siguiente ciclo.",
        ],
    }
    return validate_output_json(review)
