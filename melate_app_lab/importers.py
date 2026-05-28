from __future__ import annotations

import csv
import json
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from .number_utils import block_presence_signature, block_signature, parse_numbers, sum_band

DRAW_KEYS = {"draw", "sorteo", "concurso"}
DATE_KEYS = {"date", "fecha", "draw_date"}
GAME_KEYS = {"game", "juego", "tipo"}
NUMBER_GROUPS = [
    [f"n{index}" for index in range(1, 7)],
    [f"r{index}" for index in range(1, 7)],
    [f"numero{index}" for index in range(1, 7)],
]


def _read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).replace(" ", "_")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {_normalize_key(str(key)): value for key, value in row.items()}


def _first(row: dict[str, Any], keys: set[str], default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _coerce_numbers(raw: dict[str, Any]) -> list[int]:
    if "numbers" in raw and raw["numbers"] not in (None, ""):
        return parse_numbers(raw["numbers"])

    for fields in NUMBER_GROUPS:
        if all(field in raw and raw[field] not in (None, "") for field in fields):
            return parse_numbers([raw[field] for field in fields])

    raise ValueError("Record must include numbers or six number fields.")


def normalize_draw_record(record: dict[str, Any]) -> dict[str, Any]:
    raw = _normalize_row(dict(record))
    numbers = _coerce_numbers(raw)
    draw = int(_first(raw, DRAW_KEYS))
    game = str(_first(raw, GAME_KEYS, "revancha")).strip().casefold()
    date = str(_first(raw, DATE_KEYS, "sin-fecha")).strip()

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
    with Path(path).open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        return [normalize_draw_record(row) for row in reader]


def parse_resultados_csv(path: str | Path, default_game: str = "revancha") -> list[dict[str, Any]]:
    records = []
    with Path(path).open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_number, row in enumerate(reader, start=2):
            try:
                records.append(normalize_draw_record({"game": default_game, **row}))
            except Exception as exc:
                raise ValueError(f"Fila {row_number}: {exc}") from exc
    return records


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
