from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .guardrails import validate_output_json


def _ensure_data_path(db_path: str | Path) -> Path:
    path = Path(db_path).expanduser().resolve(strict=False)
    if "data" not in {part.lower() for part in path.parts}:
        raise ValueError("La memoria local solo puede escribirse dentro de data.")
    return path


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = _ensure_data_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def _init_db(db_path: str | Path) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            create table if not exists review_theses (
                id integer primary key autoincrement,
                draw integer not null,
                thesis text not null,
                created_at text default current_timestamp
            )
            """
        )
        conn.execute(
            """
            create table if not exists cycle_notes (
                id integer primary key autoincrement,
                draw integer not null,
                note text not null,
                created_at text default current_timestamp
            )
            """
        )
        conn.execute(
            """
            create table if not exists audit_patterns (
                id integer primary key autoincrement,
                kind text not null,
                draw integer not null,
                text text not null,
                created_at text default current_timestamp
            )
            """
        )


def _validate_memory_text(draw: int, text: str, field: str) -> None:
    if not isinstance(draw, int) or draw <= 0:
        raise ValueError("draw debe ser un entero positivo.")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{field} debe ser texto no vacio.")
    validate_output_json({"draw": draw, field: text})


def remember_review_thesis(db_path: str | Path, draw: int, thesis: str) -> None:
    _validate_memory_text(draw, thesis, "thesis")
    _init_db(db_path)
    with _connect(db_path) as conn:
        conn.execute(
            "insert into review_theses (draw, thesis) values (?, ?)",
            (draw, thesis),
        )
        conn.execute(
            "insert into audit_patterns (kind, draw, text) values (?, ?, ?)",
            ("review_thesis", draw, thesis),
        )


def load_recent_theses(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    _init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            select draw, thesis, created_at
            from review_theses
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    return validate_output_json(
        [
            {"draw": row[0], "thesis": row[1], "created_at": row[2]}
            for row in rows
        ]
    )


def remember_cycle_note(db_path: str | Path, draw: int, note: str) -> None:
    _validate_memory_text(draw, note, "note")
    _init_db(db_path)
    with _connect(db_path) as conn:
        conn.execute(
            "insert into cycle_notes (draw, note) values (?, ?)",
            (draw, note),
        )
        conn.execute(
            "insert into audit_patterns (kind, draw, text) values (?, ?, ?)",
            ("cycle_note", draw, note),
        )


def load_cycle_notes(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    _init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            select draw, note, created_at
            from cycle_notes
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    return validate_output_json(
        [
            {"draw": row[0], "note": row[1], "created_at": row[2]}
            for row in rows
        ]
    )


def summarize_audit_patterns(db_path: str | Path) -> dict[str, Any]:
    _init_db(db_path)
    with _connect(db_path) as conn:
        total_theses = conn.execute("select count(*) from review_theses").fetchone()[0]
        total_cycle_notes = conn.execute("select count(*) from cycle_notes").fetchone()[0]
        draw_rows = conn.execute(
            """
            select draw
            from audit_patterns
            group by draw
            order by max(id) desc
            """
        ).fetchall()
        pattern_rows = conn.execute(
            """
            select kind, draw, text
            from audit_patterns
            order by id desc
            """
        ).fetchall()

    summary = {
        "total_theses": total_theses,
        "total_cycle_notes": total_cycle_notes,
        "draws": [row[0] for row in draw_rows],
        "patterns": [
            {"kind": row[0], "draw": row[1], "text": row[2]}
            for row in pattern_rows
        ],
    }
    return validate_output_json(summary)
