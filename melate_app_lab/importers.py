from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .number_utils import block_presence_signature, block_signature, parse_numbers, sum_band


REQUIRED_FIELDS = ("game", "draw", "date", "numbers")


def _read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _coerce_numbers(raw: dict[str, Any]) -> list[int]:
    if "numbers" in raw and raw["numbers"] not in (None, ""):
        return parse_numbers(raw["numbers"])

    numbered_fields = [f"n{index}" for index in range(1, 7)]
    if all(field in raw for field in numbered_fields):
        return parse_numbers([raw[field] for field in numbered_fields])

    raise ValueError("Record must include numbers or n1..n6 fields.")


def normalize_draw_record(record: dict[str, Any]) -> dict[str, Any]:
    raw = dict(record)
    numbers = _coerce_numbers(raw)
    draw = int(raw["draw"])
    game = str(raw["game"]).strip().casefold()
    date = str(raw["date"]).strip()

    if not game:
        raise ValueError("Game is required.")
    if not date:
        raise ValueError("Date is required.")

    total = sum(numbers)
    return {
        "game": game,
        "draw": draw,
        "date": date,
        "numbers": numbers,
        "sum": total,
        "sum_band": sum_band(total),
        "block_signature": block_signature(numbers),
        "block_presence_signature": block_presence_signature(numbers),
    }


def parse_draw_csv(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [normalize_draw_record(row) for row in reader]


def parse_draw_json(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(_read_text(path))
    rows: Iterable[dict[str, Any]]
    if isinstance(payload, dict):
        rows = payload.get("draws", [payload])
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("JSON history must be an object or list.")

    return [normalize_draw_record(row) for row in rows]

