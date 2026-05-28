from __future__ import annotations

from .guardrails import validate_output_json
from .number_utils import (
    block_presence_signature,
    block_signature,
    parse_numbers,
    parity_signature,
    sum_band,
)


def trace_draw(draw: int, numbers: list[int] | str) -> dict[str, object]:
    parsed = parse_numbers(numbers)
    total = sum(parsed)
    signature = block_signature(parsed)
    presence = block_presence_signature(parsed)
    band = sum_band(total)
    result = {
        "draw": int(draw),
        "numbers": parsed,
        "sum": total,
        "sum_band": band,
        "parity": parity_signature(parsed),
        "block_signature": signature,
        "block_presence_signature": presence,
        "visual_label_es": f"Sorteo {draw}: huella {signature}, suma {total}",
        "trace_es": (
            f"La huella del sorteo {draw} dejó suma {total}, banda {band} "
            f"y presencia en los cinco bloques."
        ),
        "next_review_thesis_es": (
            "Tesis de revisión siguiente ciclo: contrastar cobertura de bloques, "
            "concentración de anclas y diversidad de firmas contra este rastro."
        ),
    }
    return validate_output_json(result)
