from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .importers import normalize_draw_record

SCHEMA = """
CREATE TABLE IF NOT EXISTS historical_draws (
    game TEXT NOT NULL,
    draw INTEGER NOT NULL,
    draw_date TEXT NOT NULL,
    numbers_json TEXT NOT NULL,
    sum INTEGER NOT NULL,
    sum_band TEXT NOT NULL,
    block_signature TEXT NOT NULL,
    block_presence_signature TEXT NOT NULL,
    PRIMARY KEY (game, draw)
)
"""


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    return sqlite3.connect(":memory:" if db_path is None else str(db_path))


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(SCHEMA)
    connection.commit()


def _row_to_record(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    game, draw, date, numbers_json, total, band, signature, presence = row
    return {
        "game": game,
        "draw": draw,
        "date": date,
        "numbers": json.loads(numbers_json),
        "sum": total,
        "sum_band": band,
        "block_signature": signature,
        "block_presence_signature": presence,
    }


def _insert_record(connection: sqlite3.Connection, record: dict[str, Any]) -> bool:
    normalized = normalize_draw_record(record)
    try:
        connection.execute(
            """
            INSERT INTO historical_draws (
                game, draw, draw_date, numbers_json, sum, sum_band,
                block_signature, block_presence_signature
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["game"],
                normalized["draw"],
                normalized["date"],
                json.dumps(normalized["numbers"]),
                normalized["sum"],
                normalized["sum_band"],
                normalized["block_signature"],
                normalized["block_presence_signature"],
            ),
        )
    except sqlite3.IntegrityError:
        return False
    return True


def import_draws_to_memory(
    records: Iterable[dict[str, Any]],
    db_path: str | Path | None = None,
    *,
    skip_duplicates: bool = False,
) -> sqlite3.Connection:
    connection = _connect(db_path)
    _ensure_schema(connection)

    for record in records:
        inserted = _insert_record(connection, record)
        if not inserted and not skip_duplicates:
            normalized = normalize_draw_record(record)
            raise ValueError(f"Duplicate draw for {normalized['game']} #{normalized['draw']}.")

    connection.commit()
    return connection


def load_draw_history(
    source: sqlite3.Connection | str | Path,
    game: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    connection = source if isinstance(source, sqlite3.Connection) else _connect(source)
    _ensure_schema(connection)
    limit_clause = " LIMIT ?" if limit is not None else ""

    if game is None:
        query = f"""
            SELECT game, draw, draw_date, numbers_json, sum, sum_band,
                   block_signature, block_presence_signature
            FROM historical_draws
            ORDER BY draw_date, game, draw
            {limit_clause}
            """
        params = (limit,) if limit is not None else ()
    else:
        query = f"""
            SELECT game, draw, draw_date, numbers_json, sum, sum_band,
                   block_signature, block_presence_signature
            FROM historical_draws
            WHERE game = ?
            ORDER BY draw_date, draw
            {limit_clause}
            """
        params = (game.casefold(), limit) if limit is not None else (game.casefold(),)

    return [_row_to_record(row) for row in connection.execute(query, params).fetchall()]


def get_latest_draw(source: sqlite3.Connection | str | Path, game: str | None = None) -> dict[str, Any] | None:
    connection = source if isinstance(source, sqlite3.Connection) else _connect(source)
    _ensure_schema(connection)
    if game is None:
        row = connection.execute(
            """
            SELECT game, draw, draw_date, numbers_json, sum, sum_band,
                   block_signature, block_presence_signature
            FROM historical_draws
            ORDER BY draw DESC
            LIMIT 1
            """
        ).fetchone()
    else:
        row = connection.execute(
            """
            SELECT game, draw, draw_date, numbers_json, sum, sum_band,
                   block_signature, block_presence_signature
            FROM historical_draws
            WHERE game = ?
            ORDER BY draw DESC
            LIMIT 1
            """,
            (game.casefold(),),
        ).fetchone()
    return _row_to_record(row) if row else None


def suggest_next_draw(source: sqlite3.Connection | str | Path, game: str | None = None, default_draw: int = 4218) -> int:
    latest = get_latest_draw(source, game=game)
    return int(latest["draw"]) + 1 if latest else default_draw
