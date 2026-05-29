from __future__ import annotations

import logging
import random
from typing import Any

from .candidate_ranker import rank_candidates
from .candidate_search import search_candidates
from .candidate_generator import analyze_time_window
from .feature_extractor import extract_features
from .relation_graph import build_historical_relation_graph
from .ml_ranker import is_ml_available, train_ml_ranker, rank_candidates_ml

logger = logging.getLogger(__name__)


def generate_random_combinations(
    count: int,
    exclude_sets: set[frozenset[int]],
    seed: int = 42,
) -> list[list[int]]:
    """Generate unique random combinations of 6 numbers in 1-56, excluding historical sets."""
    rng = random.Random(seed)
    combinations: list[list[int]] = []
    seen = set()

    attempts = 0
    max_attempts = count * 20
    while len(combinations) < count and attempts < max_attempts:
        attempts += 1
        nums = sorted(rng.sample(range(1, 57), 6))
        f_set = frozenset(nums)
        if f_set not in exclude_sets and f_set not in seen:
            seen.add(f_set)
            combinations.append(nums)

    return combinations


def run_backtest(
    history: list[dict[str, Any]],
    target_draws: list[int],
    window: int = 30,
    pool_size: int = 200,
    top_k: int = 10,
    seed: int = 42,
    game: str = "revancha",
    use_ml: bool = False,
    log_fn: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Execute a walk-forward retrospective evaluation of candidates against historical draws.

    Compares the heuristic or ML ranker's top_k selections against a random baseline
    using descriptive metrics and strict guardrails.
    """
    results: list[dict[str, Any]] = []

    # Filter history by game
    filtered_history = [d for d in history if str(d.get("game", "")).casefold() == game.casefold()]
    filtered_history.sort(key=lambda d: d.get("draw", 0))

    history_by_draw = {d["draw"]: d for d in filtered_history}

    actual_use_ml = use_ml and is_ml_available()
    if use_ml and not actual_use_ml:
        logger.warning("ML solicitado pero scikit-learn no está instalado. Usando Heuristic Ranker por defecto.")

    for target_draw in sorted(target_draws):
        if target_draw not in history_by_draw:
            continue

        if log_fn:
            log_fn(f"Evaluando sorteo retrospectivo {target_draw}...")

        target_record = history_by_draw[target_draw]
        target_numbers = target_record["numbers"]
        target_set = set(target_numbers)

        # Get history prior to target draw
        prior_history = [d for d in filtered_history if d["draw"] < target_draw]
        if len(prior_history) < 10:
            # Not enough history to extract window
            continue

        # Extract features relative to training window
        train_history = prior_history[-window:] if len(prior_history) >= window else prior_history
        analysis = analyze_time_window(prior_history, window=window)

        # Build historical relation graph for training window
        graph_data = build_historical_relation_graph(prior_history, window=window, game=game)

        # 1. Candidate Generation & Feature Extraction
        candidate_pool = search_candidates(analysis, pool_size=pool_size, seed=seed + target_draw)

        cand_features = []
        for cand in candidate_pool:
            feats = extract_features(cand, train_history, prior_history, graph_data)
            cand_features.append(feats)

        # 2. Random Baseline Generation & Feature Extraction
        historical_sets = {frozenset(d["numbers"]) for d in prior_history}
        baseline_pool = generate_random_combinations(pool_size, historical_sets, seed=seed + target_draw + 1)

        baseline_features = []
        for base_cand in baseline_pool:
            feats = extract_features(base_cand, train_history, prior_history, graph_data)
            baseline_features.append(feats)

        # 3. Ranking
        common_sigs = analysis.get("common_signatures", [])
        common_bands = analysis.get("common_bands", [])

        if actual_use_ml:
            prior_draw_ids = [d["draw"] for d in prior_history]
            ml_train_draws = prior_draw_ids[-30:] if len(prior_draw_ids) >= 30 else prior_draw_ids
            if log_fn:
                log_fn(f"  Entrenando ML Ranker en sorteo {target_draw} usando {len(ml_train_draws)} sorteos pasados...")
            model = train_ml_ranker(history, ml_train_draws, window=window, game=game)
            ranked_candidates = rank_candidates_ml(model, cand_features, common_sigs, common_bands)
            ranked_baseline = rank_candidates_ml(model, baseline_features, common_sigs, common_bands)
        else:
            ranked_candidates = rank_candidates(cand_features, common_sigs, common_bands)
            ranked_baseline = rank_candidates(baseline_features, common_sigs, common_bands)

        # 4. Score & Hits Evaluation
        top_candidates = ranked_candidates[:top_k]
        top_baseline = ranked_baseline[:top_k]

        cand_hits = [len(set(c["numbers"]) & target_set) for c in top_candidates]
        base_hits = [len(set(b["numbers"]) & target_set) for b in top_baseline]

        all_cand_hits = [len(set(c["numbers"]) & target_set) for c in ranked_candidates]
        all_base_hits = [len(set(b["numbers"]) & target_set) for b in ranked_baseline]

        # Count distribution
        def get_dist(hits_list: list[int]) -> dict[str, int]:
            return {f"hits_{i}": hits_list.count(i) for i in range(7)}

        draw_metrics = {
            "draw": target_draw,
            "numbers": target_numbers,
            "ranker_top_k_max_hits": max(cand_hits) if cand_hits else 0,
            "ranker_top_k_mean_hits": sum(cand_hits) / len(cand_hits) if cand_hits else 0.0,
            "baseline_top_k_max_hits": max(base_hits) if base_hits else 0,
            "baseline_top_k_mean_hits": sum(base_hits) / len(base_hits) if base_hits else 0.0,
            "ranker_all_max_hits": max(all_cand_hits) if all_cand_hits else 0,
            "ranker_all_mean_hits": sum(all_cand_hits) / len(all_cand_hits) if all_cand_hits else 0.0,
            "baseline_all_max_hits": max(all_base_hits) if all_base_hits else 0,
            "baseline_all_mean_hits": sum(all_base_hits) / len(all_base_hits) if all_base_hits else 0.0,
            "ranker_hits_distribution": get_dist(cand_hits),
            "baseline_hits_distribution": get_dist(base_hits),
        }
        results.append(draw_metrics)

    if not results:
        return {
            "draws_evaluated": 0,
            "metrics": {},
            "results": [],
            "game": game,
        }

    # Aggregate metrics
    draws_count = len(results)
    avg_ranker_top_k_max = sum(r["ranker_top_k_max_hits"] for r in results) / draws_count
    avg_ranker_top_k_mean = sum(r["ranker_top_k_mean_hits"] for r in results) / draws_count
    avg_baseline_top_k_max = sum(r["baseline_top_k_max_hits"] for r in results) / draws_count
    avg_baseline_top_k_mean = sum(r["baseline_top_k_mean_hits"] for r in results) / draws_count

    ranker_3plus_draws = sum(1 for r in results if r["ranker_top_k_max_hits"] >= 3)
    baseline_3plus_draws = sum(1 for r in results if r["baseline_top_k_max_hits"] >= 3)

    ranker_4plus_draws = sum(1 for r in results if r["ranker_top_k_max_hits"] >= 4)
    baseline_4plus_draws = sum(1 for r in results if r["baseline_top_k_max_hits"] >= 4)

    aggregated = {
        "draws_evaluated": draws_count,
        "avg_ranker_top_k_max_hits": round(avg_ranker_top_k_max, 2),
        "avg_ranker_top_k_mean_hits": round(avg_ranker_top_k_mean, 2),
        "avg_baseline_top_k_max_hits": round(avg_baseline_top_k_max, 2),
        "avg_baseline_top_k_mean_hits": round(avg_baseline_top_k_mean, 2),
        "ranker_3plus_rate": round(ranker_3plus_draws / draws_count * 100, 1),
        "baseline_3plus_rate": round(baseline_3plus_draws / draws_count * 100, 1),
        "ranker_4plus_rate": round(ranker_4plus_draws / draws_count * 100, 1),
        "baseline_4plus_rate": round(baseline_4plus_draws / draws_count * 100, 1),
    }

    return {
        "game": game,
        "draws_evaluated": draws_count,
        "metrics": aggregated,
        "results": results,
    }
