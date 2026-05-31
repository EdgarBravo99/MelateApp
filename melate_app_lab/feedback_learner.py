from __future__ import annotations

import json
import logging
import random
import sqlite3
from pathlib import Path
from typing import Any

from .candidate_generator import analyze_time_window
from .candidate_ranker import DEFAULT_WEIGHTS, rank_candidates
from .feature_extractor import extract_features_batch
from .historical_store import load_draw_history
from .relation_graph import build_historical_relation_graph
from .thesis_memory import (
    deactivate_all_feedback_profiles,
    get_active_feedback_profile,
    load_feedback_profiles,
    save_feedback_profile,
    set_feedback_profile_active,
)

logger = logging.getLogger(__name__)


def build_reviewed_dataset(db_path: str | Path, game: str) -> list[dict[str, Any]]:
    """Carga todas las carteras en estado 'Revisado' y reconstruye sus caracteristicas históricas."""
    db_path = Path(db_path)
    
    # Cargar carteras revisadas
    with sqlite3.connect(db_path) as conn:
        portfolios = conn.execute(
            """
            select id, draw, game from thesis_portfolios
            where game = ? and id in (
                select distinct portfolio_id from thesis_candidates where state = 'Revisado'
            )
            order by draw asc
            """,
            (game,),
        ).fetchall()

    dataset = []
    history = load_draw_history(db_path, game=game)
    if not history:
        return []

    for port_id, draw, port_game in portfolios:
        # Cargar candidatos de esta cartera
        with sqlite3.connect(db_path) as conn:
            cand_rows = conn.execute(
                "select numbers, hits_count, result_numbers from thesis_candidates where portfolio_id = ?",
                (port_id,),
            ).fetchall()

        if not cand_rows:
            continue

        result_numbers = json.loads(cand_rows[0][2]) if cand_rows[0][2] else None
        if not result_numbers:
            continue

        # Evitar lookahead bias: solo historia previa al sorteo de la cartera
        prior_history = [d for d in history if d["draw"] < draw]
        if len(prior_history) < 10:
            continue

        analysis = analyze_time_window(prior_history, window=30)
        graph_data = build_historical_relation_graph(prior_history, window=30, game=game)
        train_history = prior_history[-30:] if len(prior_history) >= 30 else prior_history

        common_sigs = analysis.get("common_signatures", [])
        common_bands = analysis.get("common_bands", [])

        cand_list = [json.loads(row[0]) for row in cand_rows]
        batch_feats = extract_features_batch(cand_list, train_history, prior_history, graph_data)

        candidates_features = []
        for i, (numbers_str, hits, _) in enumerate(cand_rows):
            feats = batch_feats[i]
            feats["_hits_count"] = hits
            candidates_features.append(feats)

        dataset.append({
            "portfolio_id": port_id,
            "draw": draw,
            "result_numbers": result_numbers,
            "common_signatures": common_sigs,
            "common_bands": common_bands,
            "features": candidates_features,
        })

    return dataset


def evaluate_weights_on_dataset(dataset: list[dict[str, Any]], weights: dict[str, float]) -> float:
    """Evalua un conjunto de pesos sobre el dataset de carteras revisadas."""
    total_top_hits = 0.0
    for item in dataset:
        ranked = rank_candidates(
            item["features"],
            item["common_signatures"],
            item["common_bands"],
            weights=weights,
        )
        # Tomar los top 3 candidatos segun el nuevo ranking y promediar sus hits
        top_k = min(3, len(ranked))
        hits = sum(cand.get("_hits_count", 0) for cand in ranked[:top_k])
        total_top_hits += hits / top_k
    return total_top_hits / len(dataset) if dataset else 0.0


def optimize_ranker_weights_walkforward(
    dataset: list[dict[str, Any]],
    seed: int = 42,
) -> tuple[dict[str, float], float, float]:
    """Optimiza los pesos del ranker buscando maximizar la efectividad retrospectiva."""
    rng = random.Random(seed)
    
    # Evaluar baseline (DEFAULT_WEIGHTS)
    baseline_score = evaluate_weights_on_dataset(dataset, DEFAULT_WEIGHTS)
    
    best_weights = dict(DEFAULT_WEIGHTS)
    best_score = baseline_score

    # Optimizacion heuristica simple por perturbacion aleatoria
    keys_to_optimize = [
        "graph_support_score",
        "pair_edges_count",
        "diversity_score",
        "parity_balance_3_3",
        "parity_balance_4_2_or_2_4",
        "block_signature_match",
        "sum_band_match",
    ]

    for _ in range(500):
        # Clonar pesos actuales y perturbar un subconjunto
        candidate_weights = dict(best_weights)
        for key in keys_to_optimize:
            if rng.random() < 0.4:
                # Modificar levemente el peso
                delta = rng.uniform(-1.0, 1.0)
                candidate_weights[key] = max(0.0, candidate_weights[key] + delta)
        
        # Evaluar
        score = evaluate_weights_on_dataset(dataset, candidate_weights)
        if score > best_score:
            best_score = score
            best_weights = candidate_weights

    return best_weights, best_score, baseline_score


def learn_from_reviewed_portfolios(db_path: str | Path, game: str = "revancha", seed: int = 42) -> dict[str, Any]:
    """Cierra el ciclo de aprendizaje extrayendo señal de carteras revisadas."""
    db_path = Path(db_path)
    dataset = build_reviewed_dataset(db_path, game)
    n_reviewed = len(dataset)

    if n_reviewed == 0:
        return {
            "success": False,
            "message": "No se encontraron carteras en estado 'Revisado' para aprender.",
            "min_reviewed": 0,
        }

    # Definir rango de draws de origen
    draws = [item["draw"] for item in dataset]
    from_draw = min(draws)
    to_draw = max(draws)

    # Optimizar pesos
    best_weights, best_score, baseline_score = optimize_ranker_weights_walkforward(dataset, seed)

    # Reglas de confianza
    status = "insufficient_data"
    should_activate = False

    if n_reviewed < 5:
        status = "experimental_insufficient_data"
    elif n_reviewed >= 20:
        if best_score > baseline_score:
            status = "active_recalibrated"
            should_activate = True
        else:
            status = "inactive_baseline_optimal"
    else:
        # Entre 5 y 19 carteras revisadas: guardamos como experimental
        status = "experimental_data"

    # Si se decide activar, desactivar perfiles anteriores primero
    if should_activate:
        deactivate_all_feedback_profiles(db_path, game)

    # Guardar en base de datos
    config_json = {"n_reviewed": n_reviewed, "seed": seed}
    metrics_json = {
        "best_score": round(best_score, 4),
        "baseline_score": round(baseline_score, 4),
        "improvement": round(best_score - baseline_score, 4),
    }

    profile_id = save_feedback_profile(
        db_path=db_path,
        game=game,
        source_from_draw=from_draw,
        source_to_draw=to_draw,
        objective="maximize_top3_hits",
        algorithm="random_search_perturbation",
        seed=seed,
        config=config_json,
        weights=best_weights,
        metrics=metrics_json,
        active=1 if should_activate else 0,
    )

    return {
        "success": True,
        "profile_id": profile_id,
        "game": game,
        "reviewed_count": n_reviewed,
        "status": status,
        "activated": should_activate,
        "baseline_score": baseline_score,
        "optimized_score": best_score,
        "weights": best_weights,
    }
