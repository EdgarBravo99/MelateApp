from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .guardrails import validate_output_json


DEFAULT_DB_PATH = Path("data/melate_app_memory.sqlite")


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            create table if not exists draws (
                draw integer primary key,
                numbers text not null,
                sum integer not null,
                sum_band text not null,
                block_signature text not null,
                block_presence_signature text not null,
                payload text not null,
                created_at text default current_timestamp
            )
            """
        )
        conn.execute(
            """
            create table if not exists played_tickets (
                id integer primary key autoincrement,
                draw integer not null,
                label text,
                numbers text not null,
                created_at text default current_timestamp
            )
            """
        )
        conn.execute(
            """
            create table if not exists postmortems (
                draw integer primary key,
                captured_numbers text not null,
                missed_numbers text not null,
                payload text not null,
                created_at text default current_timestamp
            )
            """
        )
        conn.execute(
            """
            create table if not exists lessons (
                id integer primary key autoincrement,
                draw integer not null,
                lesson text not null,
                captured_numbers text not null,
                missed_numbers text not null,
                created_at text default current_timestamp
            )
            """
        )
        conn.execute(
            """
            create table if not exists trace_patterns (
                id integer primary key autoincrement,
                draw integer not null,
                sum_band text not null,
                block_signature text not null,
                block_presence_signature text not null,
                created_at text default current_timestamp
            )
            """
        )


def remember_draw(db_path: str | Path, draw_trace: dict[str, Any]) -> None:
    validate_output_json(draw_trace)
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.execute(
            """
            insert or replace into draws
            (draw, numbers, sum, sum_band, block_signature, block_presence_signature, payload)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draw_trace["draw"],
                json.dumps(draw_trace["numbers"]),
                draw_trace["sum"],
                draw_trace["sum_band"],
                draw_trace["block_signature"],
                draw_trace["block_presence_signature"],
                json.dumps(draw_trace, ensure_ascii=False),
            ),
        )
        conn.execute(
            """
            insert into trace_patterns
            (draw, sum_band, block_signature, block_presence_signature)
            values (?, ?, ?, ?)
            """,
            (
                draw_trace["draw"],
                draw_trace["sum_band"],
                draw_trace["block_signature"],
                draw_trace["block_presence_signature"],
            ),
        )


def remember_played_tickets(
    db_path: str | Path,
    draw: int,
    played_tickets: list[list[int]],
) -> None:
    init_db(db_path)
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    with _connect(db_path) as conn:
        conn.execute("delete from played_tickets where draw = ?", (draw,))
        for index, numbers in enumerate(played_tickets):
            conn.execute(
                "insert into played_tickets (draw, label, numbers) values (?, ?, ?)",
                (draw, labels[index] if index < len(labels) else str(index + 1), json.dumps(numbers)),
            )


def remember_postmortem(db_path: str | Path, postmortem_result: dict[str, Any]) -> None:
    validate_output_json(postmortem_result)
    init_db(db_path)
    draw = int(postmortem_result["draw"])
    captured = postmortem_result["captured_numbers"]
    missed = postmortem_result["missed_numbers"]
    with _connect(db_path) as conn:
        conn.execute(
            """
            insert or replace into postmortems
            (draw, captured_numbers, missed_numbers, payload)
            values (?, ?, ?, ?)
            """,
            (
                draw,
                json.dumps(captured),
                json.dumps(missed),
                json.dumps(postmortem_result, ensure_ascii=False),
            ),
        )
        conn.execute("delete from lessons where draw = ?", (draw,))
        for lesson in postmortem_result.get("lessons_es", []):
            conn.execute(
                """
                insert into lessons (draw, lesson, captured_numbers, missed_numbers)
                values (?, ?, ?, ?)
                """,
                (draw, lesson, json.dumps(captured), json.dumps(missed)),
            )


def load_recent_lessons(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            select draw, lesson, captured_numbers, missed_numbers, created_at
            from lessons
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    lessons = [
        {
            "draw": row[0],
            "lesson": row[1],
            "captured_numbers": json.loads(row[2]),
            "missed_numbers": json.loads(row[3]),
            "created_at": row[4],
        }
        for row in rows
    ]
    return validate_output_json(lessons)
