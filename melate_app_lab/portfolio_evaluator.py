from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Any

from .metrics import (
    calculate_hits,
    rate_2plus,
    rate_3plus,
    avg_mean_hits,
    unique_hits_union,
    average_internal_overlap,
    high_redundancy_pairs,
)
from .thesis_memory import load_thesis_candidates, update_candidate_review_result
from .historical_store import insert_draw_record
from .number_utils import parse_numbers


def evaluate_existing_portfolio(
    db_path: str | Path,
    portfolio_id: int,
    result_numbers: list[int] | str,
    game: str = "revancha",
    persist: bool = True,
) -> dict[str, Any]:
    """Evalua retrospectivamente una cartera existente contra el resultado del sorteo.
    
    REGLA DURA: No genera candidatos nuevos ni llama a modulos de busqueda/generacion.
    """
    db_path = Path(db_path)
    
    # Coercion de result_numbers
    if isinstance(result_numbers, str):
        clean_numbers = parse_numbers(result_numbers)
    else:
        clean_numbers = [int(n) for n in result_numbers]

    if len(clean_numbers) != 6:
        raise ValueError("El resultado debe contener exactamente 6 numeros.")

    # Cargar informacion de la cartera
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "select draw, game from thesis_portfolios where id = ?",
            (portfolio_id,)
        ).fetchone()
        
    if not row:
        raise ValueError(f"No se encontro la cartera con ID {portfolio_id}")
        
    draw, portfolio_game = row
    if not game:
        game = portfolio_game

    # Cargar candidatos
    candidates = load_thesis_candidates(db_path, portfolio_id)
    if not candidates:
        raise ValueError(f"La cartera {portfolio_id} no tiene candidatos registrados.")

    hits_list = []
    candidate_numbers = []
    
    for cand in candidates:
        nums = cand["numbers"]
        candidate_numbers.append(nums)
        hits = calculate_hits(nums, clean_numbers)
        hits_list.append(hits)
        
        if persist:
            update_candidate_review_result(db_path, cand["id"], clean_numbers, hits)

    # Calcular metricas
    metrics = {
        "rate_2plus": rate_2plus(hits_list),
        "rate_3plus": rate_3plus(hits_list),
        "avg_mean_hits": avg_mean_hits(hits_list),
        "unique_hits_union": unique_hits_union(candidate_numbers, clean_numbers),
        "average_internal_overlap": average_internal_overlap(candidate_numbers),
        "high_redundancy_pairs": high_redundancy_pairs(candidate_numbers),
    }

    if persist:
        # Registrar sorteo en historical_store
        record = {
            "game": game,
            "draw": draw,
            "date": datetime.date.today().isoformat(),
            "numbers": clean_numbers,
        }
        with sqlite3.connect(db_path) as conn:
            insert_draw_record(conn, record, commit=True, ensure_schema=True)

    return {
        "portfolio_id": portfolio_id,
        "draw": draw,
        "game": game,
        "result_numbers": clean_numbers,
        "metrics": metrics,
    }
