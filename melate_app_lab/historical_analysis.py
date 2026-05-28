from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .guardrails import validate_output_json
from .importers import normalize_draw_record
from .number_utils import block_presence_signature, block_signature, parse_numbers, sum_band


def _normalized_history(history: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_draw_record(record) for record in history]


def summarize_history(history: Iterable[dict[str, Any]]) -> dict[str, Any]:
    records = _normalized_history(history)
    sum_bands = Counter(record["sum_band"] for record in records)
    block_signatures = Counter(record["block_signature"] for record in records)
    presence_signatures = Counter(record["block_presence_signature"] for record in records)

    result = {
        "total_draws": len(records),
        "draw_count": len(records),
        "sum_band_counts": dict(sorted(sum_bands.items())),
        "sum_bands": dict(sorted(sum_bands.items())),
        "block_signature_counts": dict(sorted(block_signatures.items())),
        "block_signatures": dict(sorted(block_signatures.items())),
        "block_presence_counts": dict(sorted(presence_signatures.items())),
        "block_presence_signatures": dict(sorted(presence_signatures.items())),
        "recurrent_structures": {
            "top_sum_bands": _top_items(dict(sorted(sum_bands.items()))),
            "top_block_signatures": _top_items(dict(sorted(block_signatures.items()))),
            "top_block_presence_signatures": _top_items(dict(sorted(presence_signatures.items()))),
        },
        "review_notes_es": [
            "Revision descriptiva de huellas historicas locales.",
            "Comparar suma, firma de bloques y presencia de bloques con el rastro actual.",
        ],
        "review_default": {
            "mode": "review_default",
            "notes_es": "Resumen descriptivo local para revisar huellas historicas.",
        },
    }
    return validate_output_json(result)


def compare_trace_to_history(
    trace: dict[str, Any],
    history: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    records = _normalized_history(history)
    numbers = parse_numbers(trace["numbers"])
    total = sum(numbers)
    signature = trace.get("block_signature", block_signature(numbers))
    presence = trace.get("block_presence_signature", block_presence_signature(numbers))
    band = trace.get("sum_band", sum_band(total))

    result = {
        "trace": {
            "draw": int(trace["draw"]),
            "numbers": numbers,
            "sum": total,
            "sum_band": band,
            "block_signature": signature,
            "block_presence_signature": presence,
        },
        "matches": {
            "same_sum_band": sum(1 for record in records if record["sum_band"] == band),
            "same_block_signature": sum(
                1 for record in records if record["block_signature"] == signature
            ),
            "same_block_presence_signature": sum(
                1
                for record in records
                if record["block_presence_signature"] == presence
            ),
        },
        "review_default": {
            "mode": "review_default",
            "notes_es": "Contraste descriptivo contra el historial cargado.",
        },
    }
    return validate_output_json(result)


def detect_recurrent_structures(history: Iterable[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_history(history)
    result = {
        "top_sum_bands": _top_items(summary["sum_bands"]),
        "top_block_signatures": _top_items(summary["block_signatures"]),
        "top_block_presence_signatures": _top_items(
            summary["block_presence_signatures"]
        ),
        "review_default": {
            "mode": "review_default",
            "notes_es": "Estructuras repetidas observadas en datos historicos locales.",
        },
    }
    return validate_output_json(result)


def build_history_review_thesis(
    trace: dict[str, Any],
    history: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    comparison = compare_trace_to_history(trace, history)
    result = {
        "review_default": {
            "mode": "review_default",
            "notes_es": (
                "Tesis de revision: contrastar suma, huella de bloques y presencia "
                "de bloques contra el historial local antes de emitir observaciones."
            ),
        },
        "focus": [
            "suma",
            "huella de bloques",
            "presencia de bloques",
        ],
        "comparison": comparison["matches"],
    }
    return validate_output_json(result)


def _top_items(counter_dict: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in sorted(
            counter_dict.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
