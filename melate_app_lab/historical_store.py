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


def ensure_historical_schema(connection: sqlite3.Connection) -> None:
    connection.execute(SCHEMA)
    connection.commit()


ensure_schema = ensure_historical_schema


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


def import_draws_to_memory(
    records: Iterable[dict[str, Any]],
    db_path: str | Path | None = None,
) -> sqlite3.Connection:
    connection = _connect(db_path)
    ensure_historical_schema(connection)

    for record in records:
        insert_draw_record(connection, record, commit=False, ensure_schema=False)

    connection.commit()
    return connection


def insert_draw_record(
    connection: sqlite3.Connection,
    record: dict[str, Any],
    commit: bool = True,
    ensure_schema: bool = True,
) -> bool:
    if ensure_schema:
        ensure_historical_schema(connection)
    normalized = normalize_draw_record(record)
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO historical_draws (
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
    if commit:
        connection.commit()
    return cursor.rowcount == 1


def load_draw_history(
    source: sqlite3.Connection | str | Path,
    limit: int | None = None,
    game: str | None = None,
) -> list[dict[str, Any]]:
    is_local = not isinstance(source, sqlite3.Connection)
    connection = _connect(source) if is_local else source

    try:
        ensure_historical_schema(connection)
        limit_clause = ""
        params: tuple[Any, ...] = ()
        order_by = "draw_date, game, draw"
        if limit is not None:
            limit_clause = "LIMIT ?"
            params = (limit,)
            order_by = "draw_date DESC, game, draw DESC"

        if game is None:
            cursor = connection.execute(
                f"""
                SELECT game, draw, draw_date, numbers_json, sum, sum_band,
                       block_signature, block_presence_signature
                FROM historical_draws
                ORDER BY {order_by}
                {limit_clause}
                """,
                params,
            )
        else:
            params = (game.casefold(), *params)
            cursor = connection.execute(
                f"""
                SELECT game, draw, draw_date, numbers_json, sum, sum_band,
                       block_signature, block_presence_signature
                FROM historical_draws
                WHERE game = ?
                ORDER BY {order_by}
                {limit_clause}
                """,
                params,
            )

        records = [_row_to_record(row) for row in cursor.fetchall()]
        if limit is not None:
            records.reverse()
        return records
    finally:
        if is_local:
            connection.close()


def get_latest_draw(
    source: sqlite3.Connection | str | Path,
    game: str | None = None,
) -> int | None:
    is_local = not isinstance(source, sqlite3.Connection)
    connection = _connect(source) if is_local else source

    try:
        ensure_historical_schema(connection)
        if game is None:
            cursor = connection.execute("SELECT MAX(draw) FROM historical_draws")
        else:
            cursor = connection.execute(
                "SELECT MAX(draw) FROM historical_draws WHERE game = ?",
                (game.casefold(),),
            )
        latest = cursor.fetchone()[0]
        return None if latest is None else int(latest)
    finally:
        if is_local:
            connection.close()


def suggest_next_draw(
    source: sqlite3.Connection | str | Path,
    game: str | None = None,
) -> int:
    latest = get_latest_draw(source, game=game)
    return 4218 if latest is None else latest + 1
