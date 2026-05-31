from __future__ import annotations

from contextlib import contextmanager
import json
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


@contextmanager
def _connection_context(db_path: str | Path):
    conn = _connect(db_path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _init_db(db_path: str | Path) -> None:
    with _connection_context(db_path) as conn:
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
        conn.execute(
            """
            create table if not exists thesis_portfolios (
                id integer primary key autoincrement,
                draw integer not null,
                game text not null,
                created_at text default current_timestamp,
                notes text
            )
            """
        )
        conn.execute(
            """
            create table if not exists thesis_candidates (
                id integer primary key autoincrement,
                portfolio_id integer,
                numbers text not null,
                classification text not null,
                state text not null,
                sum integer not null,
                sum_band text not null,
                block_signature text not null,
                graph_support_score integer not null,
                rank_score real,
                pair_edges text,
                evidence_draws text,
                notes text,
                result_numbers text,
                hits_count integer,
                created_at text default current_timestamp,
                foreign key(portfolio_id) references thesis_portfolios(id) on delete cascade
            )
            """
        )
        try:
            conn.execute("ALTER TABLE thesis_candidates ADD COLUMN rank_score REAL")
        except sqlite3.OperationalError:
            pass  # Already exists

        conn.execute(
            """
            create table if not exists experiment_runs (
                id integer primary key autoincrement,
                created_at text default current_timestamp,
                game text not null,
                commit_sha text not null,
                branch text not null,
                config_json text not null,
                metrics_json text not null,
                report_paths text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists feedback_profiles (
                id integer primary key autoincrement,
                game text not null,
                created_at text default current_timestamp,
                source_from_draw integer not null,
                source_to_draw integer not null,
                objective text not null,
                algorithm text not null,
                seed integer,
                config_json text not null,
                weights_json text not null,
                metrics_json text not null,
                active integer default 0
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
    with _connection_context(db_path) as conn:
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
    with _connection_context(db_path) as conn:
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
    with _connection_context(db_path) as conn:
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
    with _connection_context(db_path) as conn:
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
    with _connection_context(db_path) as conn:
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


def save_thesis_portfolio(
    db_path: str | Path,
    draw: int,
    game: str,
    candidates: list[dict[str, Any]],
    notes: str | None = None,
) -> int:
    if not isinstance(draw, int) or draw <= 0:
        raise ValueError("draw debe ser un entero positivo.")
    if not isinstance(game, str) or not game.strip():
        raise ValueError("game debe ser un string no vacio.")

    validate_output_json({"draw": draw, "game": game, "notes": notes or ""})
    for candidate in candidates:
        validate_output_json(candidate)

    _init_db(db_path)
    with _connection_context(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "insert into thesis_portfolios (draw, game, notes) values (?, ?, ?)",
            (draw, game, notes),
        )
        portfolio_id = cursor.lastrowid
        assert portfolio_id is not None

        for cand in candidates:
            numbers_str = json.dumps(cand["numbers"])
            pair_edges_str = json.dumps(cand.get("pair_edges", []))
            evidence_draws_str = json.dumps(cand.get("evidence_draws", []))
            result_numbers_str = (
                json.dumps(cand.get("result_numbers"))
                if cand.get("result_numbers") is not None
                else None
            )

            cursor.execute(
                """
                insert into thesis_candidates (
                    portfolio_id, numbers, classification, state, sum, sum_band,
                    block_signature, graph_support_score, rank_score, pair_edges, evidence_draws,
                    notes, result_numbers, hits_count
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    portfolio_id,
                    numbers_str,
                    cand["classification"],
                    cand.get("state", "Pendiente"),
                    cand["sum"],
                    cand["sum_band"],
                    cand["block_signature"],
                    cand["graph_support_score"],
                    cand.get("rank_score"),
                    pair_edges_str,
                    evidence_draws_str,
                    cand.get("notes", ""),
                    result_numbers_str,
                    cand.get("hits_count"),
                ),
            )
        return portfolio_id


def load_thesis_portfolios(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        rows = conn.execute(
            """
            select id, draw, game, created_at, notes
            from thesis_portfolios
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    portfolios = [
        {
            "id": row[0],
            "draw": row[1],
            "game": row[2],
            "created_at": row[3],
            "notes": row[4],
        }
        for row in rows
    ]
    return validate_output_json(portfolios)


def load_thesis_candidates(db_path: str | Path, portfolio_id: int) -> list[dict[str, Any]]:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        rows = conn.execute(
            """
            select id, portfolio_id, numbers, classification, state, sum, sum_band,
                   block_signature, graph_support_score, rank_score, pair_edges, evidence_draws,
                   notes, result_numbers, hits_count, created_at
            from thesis_candidates
            where portfolio_id = ?
            order by graph_support_score desc, id asc
            """,
            (portfolio_id,),
        ).fetchall()
    candidates = [
        {
            "id": row[0],
            "portfolio_id": row[1],
            "numbers": json.loads(row[2]),
            "classification": row[3],
            "state": row[4],
            "sum": row[5],
            "sum_band": row[6],
            "block_signature": row[7],
            "graph_support_score": row[8],
            "rank_score": row[9],
            "pair_edges": json.loads(row[10]) if row[10] else [],
            "evidence_draws": json.loads(row[11]) if row[11] else [],
            "notes": row[12],
            "result_numbers": json.loads(row[13]) if row[13] else None,
            "hits_count": row[14],
            "created_at": row[15],
        }
        for row in rows
    ]
    return validate_output_json(candidates)


def update_candidate_state(db_path: str | Path, candidate_id: int, state: str) -> None:
    valid_states = {"Pendiente", "Favorito", "Jugado", "Descartado", "Revisado"}
    if state not in valid_states:
        raise ValueError(f"Estado invalido: {state}. Debe ser uno de {valid_states}")
    validate_output_json(state)
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        conn.execute(
            "update thesis_candidates set state = ? where id = ?",
            (state, candidate_id),
        )


def update_candidate_review_result(
    db_path: str | Path,
    candidate_id: int,
    result_numbers: list[int],
    hits_count: int,
) -> None:
    if not isinstance(hits_count, int) or hits_count < 0 or hits_count > 6:
        raise ValueError("hits_count debe ser un entero entre 0 y 6.")
    validate_output_json(result_numbers)
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        conn.execute(
            """
            update thesis_candidates
            set result_numbers = ?, hits_count = ?, state = 'Revisado'
            where id = ?
            """,
            (json.dumps(result_numbers), hits_count, candidate_id),
        )


def save_experiment_run(
    db_path: str | Path,
    game: str,
    commit_sha: str,
    branch: str,
    config: dict[str, Any],
    metrics: dict[str, Any],
    report_paths: list[str],
) -> int:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            insert into experiment_runs (
                game, commit_sha, branch, config_json, metrics_json, report_paths
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (
                game,
                commit_sha,
                branch,
                json.dumps(config),
                json.dumps(metrics),
                json.dumps(report_paths),
            ),
        )
        return cursor.lastrowid


def load_experiment_runs(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        rows = conn.execute(
            """
            select id, created_at, game, commit_sha, branch, config_json, metrics_json, report_paths
            from experiment_runs
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": row[0],
            "created_at": row[1],
            "game": row[2],
            "commit_sha": row[3],
            "branch": row[4],
            "config": json.loads(row[5]),
            "metrics": json.loads(row[6]),
            "report_paths": json.loads(row[7]),
        }
        for row in rows
    ]


def save_feedback_profile(
    db_path: str | Path,
    game: str,
    source_from_draw: int,
    source_to_draw: int,
    objective: str,
    algorithm: str,
    seed: int | None,
    config: dict[str, Any],
    weights: dict[str, Any],
    metrics: dict[str, Any],
    active: int = 0,
) -> int:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            insert into feedback_profiles (
                game, source_from_draw, source_to_draw, objective, algorithm,
                seed, config_json, weights_json, metrics_json, active
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game,
                source_from_draw,
                source_to_draw,
                objective,
                algorithm,
                seed,
                json.dumps(config),
                json.dumps(weights),
                json.dumps(metrics),
                active,
            ),
        )
        return cursor.lastrowid


def get_active_feedback_profile(db_path: str | Path, game: str) -> dict[str, Any] | None:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        row = conn.execute(
            """
            select id, source_from_draw, source_to_draw, objective, algorithm,
                   seed, config_json, weights_json, metrics_json, active, created_at
            from feedback_profiles
            where game = ? and active = 1
            order by id desc
            limit 1
            """,
            (game,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "game": game,
        "source_from_draw": row[1],
        "source_to_draw": row[2],
        "objective": row[3],
        "algorithm": row[4],
        "seed": row[5],
        "config": json.loads(row[6]),
        "weights": json.loads(row[7]),
        "metrics": json.loads(row[8]),
        "active": bool(row[9]),
        "created_at": row[10],
    }


def deactivate_all_feedback_profiles(db_path: str | Path, game: str) -> None:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        conn.execute(
            "update feedback_profiles set active = 0 where game = ?",
            (game,),
        )


def set_feedback_profile_active(db_path: str | Path, profile_id: int, active: int) -> None:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        conn.execute(
            "update feedback_profiles set active = ? where id = ?",
            (active, profile_id),
        )


def load_feedback_profiles(db_path: str | Path, game: str, limit: int = 10) -> list[dict[str, Any]]:
    _init_db(db_path)
    with _connection_context(db_path) as conn:
        rows = conn.execute(
            """
            select id, source_from_draw, source_to_draw, objective, algorithm,
                   seed, config_json, weights_json, metrics_json, active, created_at
            from feedback_profiles
            where game = ?
            order by id desc
            limit ?
            """,
            (game, limit),
        ).fetchall()
    return [
        {
            "id": row[0],
            "game": game,
            "source_from_draw": row[1],
            "source_to_draw": row[2],
            "objective": row[3],
            "algorithm": row[4],
            "seed": row[5],
            "config": json.loads(row[6]),
            "weights": json.loads(row[7]),
            "metrics": json.loads(row[8]),
            "active": bool(row[9]),
            "created_at": row[10],
        }
        for row in rows
    ]

