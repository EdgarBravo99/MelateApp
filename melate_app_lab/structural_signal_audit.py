from __future__ import annotations

import logging
import math
from typing import Any

from melate_app_lab.candidate_generator import analyze_time_window
from melate_app_lab.candidate_search import search_candidates
from melate_app_lab.feature_extractor import extract_features_batch
from melate_app_lab.relation_graph import build_historical_relation_graph
from melate_app_lab.structural_signal_engine import compute_structural_signals_batch
from melate_app_lab.candidate_ranker import rank_candidates
from melate_app_lab.metrics import (
    rate_2plus,
    rate_3plus,
    unique_hits_union,
    average_internal_overlap,
    high_redundancy_pairs,
)

logger = logging.getLogger(__name__)


def calculate_pearson_correlation(x: list[float], y: list[float]) -> float:
    """Calcula la correlacion de Pearson entre dos secuencias sin dependencias externas."""
    n = len(x)
    if n < 2 or len(y) != n:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = 0.0
    den_x = 0.0
    den_y = 0.0
    for xi, yi in zip(x, y):
        dx = xi - mean_x
        dy = yi - mean_y
        num += dx * dy
        den_x += dx * dx
        den_y += dy * dy

    if den_x == 0.0 or den_y == 0.0:
        return 0.0

    return round(num / math.sqrt(den_x * den_y), 6)


def run_structural_signal_audit(
    db_path: Any = None,
    game: str = "revancha",
    limit: int = 100,
    pool_size: int = 1000,
    top_k: int = 10,
    seed: int = 42,
) -> dict[str, Any]:
    """Ejecuta una auditoria walk-forward retrospectiva para medir senales estructurales."""
    from melate_app_lab.historical_store import load_draw_history
    from melate_app_lab.memory import DEFAULT_DB_PATH

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    history = load_draw_history(db_path)
    if not history:
        raise ValueError("Historial vacio en la base de datos.")

    filtered = [d for d in history if str(d.get("game", "")).casefold() == game.casefold()]
    filtered.sort(key=lambda d: d.get("draw", 0))

    if not filtered:
        raise ValueError(f"No hay sorteos en el historial para el juego: {game}")

    target_draw_records = filtered[-limit:] if limit > 0 else filtered

    evaluated_draws = 0
    all_candidates: list[dict[str, Any]] = []

    top_k_hits_by_group: dict[str, list[list[int]]] = {
        "ranker_actual": [],
        "structural_signal_only": [],
        "pair_lag_only": [],
        "block_activity_only": [],
        "gap_echo_only": [],
    }

    top_k_metrics_by_group: dict[str, dict[str, list[float]]] = {
        "ranker_actual": {"unique_hits_union": [], "average_internal_overlap": [], "high_redundancy_pairs": []},
        "structural_signal_only": {"unique_hits_union": [], "average_internal_overlap": [], "high_redundancy_pairs": []},
        "pair_lag_only": {"unique_hits_union": [], "average_internal_overlap": [], "high_redundancy_pairs": []},
        "block_activity_only": {"unique_hits_union": [], "average_internal_overlap": [], "high_redundancy_pairs": []},
        "gap_echo_only": {"unique_hits_union": [], "average_internal_overlap": [], "high_redundancy_pairs": []},
    }

    window = 30

    for target_rec in target_draw_records:
        target_draw = target_rec["draw"]
        target_numbers = target_rec["numbers"]
        target_set = set(target_numbers)

        prior_history = [d for d in filtered if d["draw"] < target_draw]
        if len(prior_history) < 10:
            continue

        train_history = prior_history[-window:] if len(prior_history) >= window else prior_history
        analysis = analyze_time_window(prior_history, window=window)
        graph_data = build_historical_relation_graph(prior_history, window=window, game=game)

        pool = search_candidates(analysis, pool_size=pool_size, seed=seed + target_draw)
        features = extract_features_batch(pool, train_history, prior_history, graph_data)

        structural_results = compute_structural_signals_batch(
            features,
            prior_history,
            window=window,
            gap_window=50,
            max_lag=5,
        )

        common_sigs = analysis.get("common_signatures", [])
        common_bands = analysis.get("common_bands", [])
        ranked_actual = rank_candidates(structural_results, common_sigs, common_bands)

        for c in ranked_actual:
            c["hits"] = len(set(c["numbers"]) & target_set)

        all_candidates.extend(ranked_actual)
        evaluated_draws += 1

        top_ranker = ranked_actual[:top_k]
        top_structural = sorted(ranked_actual, key=lambda c: (-c["structural_signal_score"], c["sum"]))[:top_k]
        top_pair_lag = sorted(ranked_actual, key=lambda c: (-c["pair_lag_score"], c["sum"]))[:top_k]
        top_block = sorted(ranked_actual, key=lambda c: (-c["block_activity_score"], c["sum"]))[:top_k]
        top_gap = sorted(ranked_actual, key=lambda c: (-c["gap_echo_score"], c["sum"]))[:top_k]

        groups = {
            "ranker_actual": top_ranker,
            "structural_signal_only": top_structural,
            "pair_lag_only": top_pair_lag,
            "block_activity_only": top_block,
            "gap_echo_only": top_gap,
        }

        for group_name, top_cands in groups.items():
            hits = [c["hits"] for c in top_cands]
            top_k_hits_by_group[group_name].append(hits)

            cands_nums = [c["numbers"] for c in top_cands]
            u_hits = unique_hits_union(cands_nums, target_numbers)
            overlap = average_internal_overlap(cands_nums)
            redundancy = high_redundancy_pairs(cands_nums)

            top_k_metrics_by_group[group_name]["unique_hits_union"].append(u_hits)
            top_k_metrics_by_group[group_name]["average_internal_overlap"].append(overlap)
            top_k_metrics_by_group[group_name]["high_redundancy_pairs"].append(redundancy)

    if evaluated_draws == 0:
        return {
            "success": False,
            "game": game,
            "draws_evaluated": 0,
            "pool_size": pool_size,
            "top_k": top_k,
            "seed": seed,
            "notes": ["Historial insuficiente para evaluar sorteos retrospectivos."],
        }

    bucket_keys = ["low", "mid", "high", "very_high"]
    scores_to_bucket = [
        "pair_lag_score",
        "block_activity_score",
        "gap_echo_score",
        "structural_signal_score",
    ]

    signal_buckets: dict[str, dict[str, dict[str, Any]]] = {}

    for score_name in scores_to_bucket:
        signal_buckets[score_name] = {}
        for bkey in bucket_keys:
            signal_buckets[score_name][bkey] = {
                "candidate_count": 0,
                "avg_hits": 0.0,
                "rate_1plus": 0.0,
                "rate_2plus": 0.0,
                "rate_3plus": 0.0,
                "avg_rank_score": 0.0,
                "avg_graph_support_score": 0.0,
                "avg_structural_signal_score": 0.0,
                "avg_pair_lag_score": 0.0,
                "avg_block_activity_score": 0.0,
                "avg_gap_echo_score": 0.0,
            }

    for c in all_candidates:
        for score_name in scores_to_bucket:
            val = max(0.0, min(1.0, c.get(score_name, 0.0)))
            if 0.0 <= val < 0.25:
                bkey = "low"
            elif 0.25 <= val < 0.50:
                bkey = "mid"
            elif 0.50 <= val < 0.75:
                bkey = "high"
            else:
                bkey = "very_high"

            b = signal_buckets[score_name][bkey]
            b["candidate_count"] += 1
            b["avg_hits"] += c.get("hits", 0)
            b["rate_1plus"] += 1 if c.get("hits", 0) >= 1 else 0
            b["rate_2plus"] += 1 if c.get("hits", 0) >= 2 else 0
            b["rate_3plus"] += 1 if c.get("hits", 0) >= 3 else 0
            b["avg_rank_score"] += c.get("rank_score", 0.0)
            b["avg_graph_support_score"] += c.get("graph_support_score", 0.0)
            b["avg_structural_signal_score"] += c.get("structural_signal_score", 0.0)
            b["avg_pair_lag_score"] += c.get("pair_lag_score", 0.0)
            b["avg_block_activity_score"] += c.get("block_activity_score", 0.0)
            b["avg_gap_echo_score"] += c.get("gap_echo_score", 0.0)

    for score_name in scores_to_bucket:
        for bkey in bucket_keys:
            b = signal_buckets[score_name][bkey]
            cnt = b["candidate_count"]
            if cnt > 0:
                b["avg_hits"] = round(b["avg_hits"] / cnt, 4)
                b["rate_1plus"] = round(b["rate_1plus"] / cnt, 4)
                b["rate_2plus"] = round(b["rate_2plus"] / cnt, 4)
                b["rate_3plus"] = round(b["rate_3plus"] / cnt, 4)
                b["avg_rank_score"] = round(b["avg_rank_score"] / cnt, 4)
                b["avg_graph_support_score"] = round(b["avg_graph_support_score"] / cnt, 4)
                b["avg_structural_signal_score"] = round(b["avg_structural_signal_score"] / cnt, 4)
                b["avg_pair_lag_score"] = round(b["avg_pair_lag_score"] / cnt, 4)
                b["avg_block_activity_score"] = round(b["avg_block_activity_score"] / cnt, 4)
                b["avg_gap_echo_score"] = round(b["avg_gap_echo_score"] / cnt, 4)

    rank_scores = [c.get("rank_score", 0.0) for c in all_candidates]
    structural_scores = [c.get("structural_signal_score", 0.0) for c in all_candidates]
    graph_supports = [c.get("graph_support_score", 0.0) for c in all_candidates]
    pair_lag_scores = [c.get("pair_lag_score", 0.0) for c in all_candidates]
    block_activity_scores = [c.get("block_activity_score", 0.0) for c in all_candidates]
    gap_echo_scores = [c.get("gap_echo_score", 0.0) for c in all_candidates]
    hits_list_float = [float(c.get("hits", 0)) for c in all_candidates]

    correlations = {
        "correlation_rank_vs_structural": calculate_pearson_correlation(rank_scores, structural_scores),
        "correlation_graph_vs_pair_lag": calculate_pearson_correlation(graph_supports, pair_lag_scores),
        "correlation_graph_vs_structural": calculate_pearson_correlation(graph_supports, structural_scores),
        "correlation_pair_lag_vs_hits": calculate_pearson_correlation(pair_lag_scores, hits_list_float),
        "correlation_block_activity_vs_hits": calculate_pearson_correlation(block_activity_scores, hits_list_float),
        "correlation_gap_echo_vs_hits": calculate_pearson_correlation(gap_echo_scores, hits_list_float),
        "correlation_structural_vs_hits": calculate_pearson_correlation(structural_scores, hits_list_float),
    }

    top_k_comparison = {}
    for group_name in top_k_hits_by_group:
        h_lists = top_k_hits_by_group[group_name]
        if not h_lists:
            top_k_comparison[group_name] = {
                "avg_max_hits": 0.0,
                "avg_mean_hits": 0.0,
                "rate_2plus": 0.0,
                "rate_3plus": 0.0,
                "unique_hits_union": 0.0,
                "average_internal_overlap": 0.0,
                "high_redundancy_pairs": 0.0,
            }
            continue

        n_draws = len(h_lists)
        sum_max_hits = sum(max(hl) if hl else 0 for hl in h_lists)
        sum_mean_hits = sum((sum(hl) / len(hl)) if hl else 0.0 for hl in h_lists)
        sum_rate_2plus = sum((sum(1 for h in hl if h >= 2) / len(hl)) if hl else 0.0 for hl in h_lists)
        sum_rate_3plus = sum((sum(1 for h in hl if h >= 3) / len(hl)) if hl else 0.0 for hl in h_lists)

        avg_max = sum_max_hits / n_draws
        avg_mean = sum_mean_hits / n_draws
        avg_r2 = sum_rate_2plus / n_draws
        avg_r3 = sum_rate_3plus / n_draws

        metrics = top_k_metrics_by_group[group_name]
        avg_unique = sum(metrics["unique_hits_union"]) / n_draws
        avg_overlap = sum(metrics["average_internal_overlap"]) / n_draws
        avg_redundancy = sum(metrics["high_redundancy_pairs"]) / n_draws

        top_k_comparison[group_name] = {
            "avg_max_hits": round(avg_max, 4),
            "avg_mean_hits": round(avg_mean, 4),
            "rate_2plus": round(avg_r2, 4),
            "rate_3plus": round(avg_r3, 4),
            "unique_hits_union": round(avg_unique, 4),
            "average_internal_overlap": round(avg_overlap, 4),
            "high_redundancy_pairs": round(avg_redundancy, 4),
        }

    return {
        "success": True,
        "game": game,
        "draws_evaluated": evaluated_draws,
        "pool_size": pool_size,
        "top_k": top_k,
        "seed": seed,
        "signal_buckets": signal_buckets,
        "correlations": correlations,
        "top_k_comparison": top_k_comparison,
        "notes": [
            "Auditoria retrospectiva completada sin modificar el ranker actual."
        ],
    }
