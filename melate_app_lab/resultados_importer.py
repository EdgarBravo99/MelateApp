from __future__ import annotations

import csv
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from .historical_store import (
    _ensure_schema,
    get_latest_draw,
    insert_draw_record,
    load_draw_history,
    suggest_next_draw,
)
from .importers import normalize_draw_record


def _normalize_header(header: str | None) -> str:
    if header is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", header)
    ascii_header = "".join(char for char in decomposed if not unicodedata.combining(char))
    return "".join(char for char in ascii_header.casefold().strip() if char.isalnum())


def _pick(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def _numbers_from_columns(row: dict[str, Any]) -> list[Any] | None:
    for prefix in ("n", "r", "numero"):
        columns = [f"{prefix}{index}" for index in range(1, 7)]
        if all(row.get(column) not in (None, "") for column in columns):
            return [row[column] for column in columns]
    return None


def _record_from_row(row: dict[str, Any], default_game: str) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "game": _pick(row, "game", "juego") or default_game,
        "draw": _pick(row, "draw", "sorteo", "concurso"),
        "date": _pick(row, "date", "fecha"),
    }

    numbers = _pick(row, "numbers", "numeros")
    if numbers is not None:
        raw["numbers"] = numbers
    else:
        column_numbers = _numbers_from_columns(row)
        if column_numbers is not None:
            raw["numbers"] = column_numbers

    return normalize_draw_record(raw)


def _get_encoding(path: str | Path) -> str:
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    for encoding in encodings:
        try:
            with Path(path).open(newline="", encoding=encoding) as f:
                f.read(4096)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _iter_normalized_rows(path: str | Path, encoding: str):
    with Path(path).open(newline="", encoding=encoding) as csv_file:
        reader = csv.DictReader(csv_file)
        for row_number, row in enumerate(reader, start=2):
            if not any(v.strip() for v in row.values() if v):
                continue
            yield row_number, {_normalize_header(key): value for key, value in row.items()}


def parse_resultados_csv(
    path: str | Path,
    default_game: str = "revancha",
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    encoding = _get_encoding(path)
    for _row_number, row in _iter_normalized_rows(path, encoding):
        records.append(_record_from_row(row, default_game))
    return records


def import_resultados_csv_to_memory(
    path: str | Path,
    db_path: str | Path,
    default_game: str = "revancha",
) -> dict[str, Any]:
    connection = sqlite3.connect(str(db_path))
    imported = 0
    duplicates_skipped = 0
    invalid_rows = 0
    invalid_row_samples = []

    encoding_used = _get_encoding(path)

    try:
        _ensure_schema(connection)
        
        connection.execute("BEGIN TRANSACTION")

        for _row_number, row in _iter_normalized_rows(path, encoding_used):
            try:
                record = _record_from_row(row, default_game)
                if insert_draw_record(connection, record, commit=False, ensure_schema=False):
                    imported += 1
                else:
                    duplicates_skipped += 1
            except (KeyError, TypeError, ValueError):
                invalid_rows += 1
                if len(invalid_row_samples) < 10:
                    invalid_row_samples.append(row)

            if (imported + duplicates_skipped + invalid_rows) % 500 == 0:
                connection.commit()
                connection.execute("BEGIN TRANSACTION")

        connection.commit()

        history_count = len(load_draw_history(connection, game=default_game))
        latest_draw = get_latest_draw(connection, game=default_game)
        suggested_next = suggest_next_draw(connection, game=default_game)
        return {
            "imported": imported,
            "duplicates_skipped": duplicates_skipped,
            "invalid_rows": invalid_rows,
            "invalid_row_samples": invalid_row_samples,
            "encoding_used": encoding_used,
            "history_count": history_count,
            "latest_draw": latest_draw,
            "suggested_next_draw": suggested_next,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
