from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .candidate_generator import analyze_time_window
from .candidate_ranker import rank_candidates
from .candidate_search import search_candidates
from .feature_extractor import extract_features
from .historical_store import insert_draw_record, load_draw_history
from .importers import normalize_draw_record
from .relation_graph import build_historical_relation_graph
from .thesis_memory import (
    _connect,
    load_thesis_candidates,
    save_thesis_portfolio,
    update_candidate_review_result,
    update_candidate_state,
)


def evaluate_portfolio_coverage(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregated structural coverage metrics for a full portfolio."""
    if not candidates:
        return {}

    all_numbers = set()
    signatures = set()

    # Blocks: 1-10, 11-20, 21-30, 31-40, 41-56
    blocks_occupied = [0] * 5
    for cand in candidates:
        nums = cand["numbers"]
        all_numbers.update(nums)
        signatures.add(cand.get("block_signature"))

        for n in nums:
            if 1 <= n <= 10:
                blocks_occupied[0] = 1
            elif 11 <= n <= 20:
                blocks_occupied[1] = 1
            elif 21 <= n <= 30:
                blocks_occupied[2] = 1
            elif 31 <= n <= 40:
                blocks_occupied[3] = 1
            elif 41 <= n <= 56:
                blocks_occupied[4] = 1

    # Average overlap
    overlap_sums = 0
    comparisons = 0
    n_cands = len(candidates)
    for i in range(n_cands):
        for j in range(i + 1, n_cands):
            overlap_sums += len(set(candidates[i]["numbers"]) & set(candidates[j]["numbers"]))
            comparisons += 1

    avg_overlap = (overlap_sums / comparisons) if comparisons > 0 else 0.0

    return {
        "unique_numbers_covered": len(all_numbers),
        "block_ranges_covered": sum(blocks_occupied),
        "unique_block_signatures": len(signatures),
        "average_internal_overlap": round(avg_overlap, 2),
    }


def classify_candidate(features: dict[str, Any]) -> str:
    """Clasifica un candidato basándose en sus características estructurales.
    
    alto graph_support -> relation
    buena cobertura/firma -> balance
    mezcla con alta diversidad -> contrast
    """
    support = features.get("graph_support_score", 0)
    diversity = features.get("diversity_score", 0)
    if support > 10:
        return "relation"
    elif diversity >= 4:
        return "balance"
    else:
        return "contrast"


def run_unified_workflow(
    db_path: str | Path,
    draw: int,
    game: str = "revancha",
    pool_size: int = 100,
    seed: int = 42,
    played_indices: list[int] | None = None,
    result_numbers: list[int] | None = None,
    top_k: int = 10,
    log_fn: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Execute the interactive workflow loop of Thesis -> Portfolio -> Play -> Evaluate."""
    history = load_draw_history(db_path, game=game)
    if not history:
        raise ValueError("No hay historial en la memoria para generar la tesis.")

    if log_fn:
        log_fn(f"Generando candidatos para sorteo {draw}...")

    # 1. Generar candidatos
    prior_history = [d for d in history if d["draw"] < draw]
    analysis = analyze_time_window(prior_history, window=30)
    graph_data = build_historical_relation_graph(prior_history, window=30, game=game)
    candidate_pool = search_candidates(analysis, pool_size=pool_size, seed=seed)

    cand_features = []
    for cand in candidate_pool:
        feats = extract_features(cand, prior_history[-30:], prior_history, graph_data)
        cand_features.append(feats)

    common_sigs = analysis.get("common_signatures", [])
    common_bands = analysis.get("common_bands", [])
    
    from .thesis_memory import get_active_feedback_profile
    active_profile = get_active_feedback_profile(db_path, game)
    weights = active_profile["weights"] if active_profile else None
    
    ranked = rank_candidates(cand_features, common_sigs, common_bands, weights=weights)

    # 2. Build candidates payload (taking top 10 ranked)
    candidates_payload = []
    # Build a lookup for pair co-occurrence details from graph_data for candidate richness
    edge_lookup = {}
    if graph_data and graph_data.get("mode") == "historical":
        for edge in graph_data.get("edges", []):
            src = int(edge["source"])
            tgt = int(edge["target"])
            pair = (min(src, tgt), max(src, tgt))
            edge_lookup[pair] = {
                "count": edge.get("count", 0),
                "draws": edge.get("draws", []),
            }

    from .portfolio_optimizer import optimize_portfolio
    selected_portfolio = optimize_portfolio(ranked, top_k)

    for idx, c in enumerate(selected_portfolio):
        # Strategy classification based on candidate details
        strat = classify_candidate(c)

        # Reconstruct detailed pair_edges and evidence_draws
        pair_edges = []
        evidence_draws = []
        nums = c["numbers"]
        for i in range(6):
            for j in range(i + 1, 6):
                pair = (nums[i], nums[j])
                if pair in edge_lookup:
                    pair_edges.append({
                        "pair": f"{nums[i]}—{nums[j]}",
                        "count": edge_lookup[pair]["count"],
                        "draws": edge_lookup[pair]["draws"],
                    })
                    evidence_draws.extend(edge_lookup[pair]["draws"])

        evidence_draws = sorted(list(set(evidence_draws)), reverse=True)[:5]

        candidates_payload.append({
            "numbers": nums,
            "classification": strat,
            "state": "Pendiente",
            "sum": c["sum"],
            "sum_band": c["sum_band"],
            "block_signature": c["block_signature"],
            "graph_support_score": c["graph_support_score"],
            "rank_score": c.get("rank_score", 0.0),
            "pair_edges": pair_edges,
            "evidence_draws": evidence_draws,
            "notes": f"Score: {c.get('rank_score', 0.0)}",
        })

    # Calculate coverage metrics of the portfolio
    coverage = evaluate_portfolio_coverage(candidates_payload)
    notes_payload = json.dumps({"coverage": coverage})

    portfolio_id = save_thesis_portfolio(
        db_path,
        draw=draw,
        game=game,
        candidates=candidates_payload,
        notes=notes_payload,
    )

    if log_fn:
        log_fn(f"Cartera {portfolio_id} guardada con {len(candidates_payload)} candidatos.")
        log_fn(
            f"Cobertura estructural de la cartera: {coverage['unique_numbers_covered']} números únicos cubiertos en {coverage['block_ranges_covered']} bloques."
        )

    # 3. Registrar JUGADAS (Played)
    db_candidates = load_thesis_candidates(db_path, portfolio_id)
    played_candidates = []
    if played_indices:
        for idx in played_indices:
            if 0 <= idx < len(db_candidates):
                cand_id = db_candidates[idx]["id"]
                update_candidate_state(db_path, cand_id, "Jugado")
                # Update our local memory trace
                db_candidates[idx]["state"] = "Jugado"
                played_candidates.append(db_candidates[idx])

    if log_fn:
        log_fn(f"Se registraron {len(played_candidates)} candidatos de la cartera como Jugados.")

    # 4 & 5. Capturar resultado oficial & Revisar aciertos
    evaluation = {}
    if result_numbers:
        # Dynamically calculate features for the winning draw before saving to historical_store
        result_record = normalize_draw_record({
            "game": game,
            "draw": draw,
            "date": "2026-05-29",
            "numbers": result_numbers,
        })

        conn = _connect(db_path)
        try:
            insert_draw_record(conn, result_record, commit=True, ensure_schema=True)
        finally:
            conn.close()

        if log_fn:
            log_fn(f"Resultado oficial registrado en historical_store: {result_numbers}")

        # Calculate hits
        target_set = set(result_numbers)
        union_hits = set()

        for cand in db_candidates:
            cand_set = set(cand["numbers"])
            hits = len(cand_set & target_set)

            # Check if it was played to add to union hits
            if cand["state"] == "Jugado":
                union_hits.update(cand_set & target_set)

            update_candidate_review_result(db_path, cand["id"], result_numbers, hits)

        evaluation = {
            "result_captured": True,
            "result_numbers": result_numbers,
            "portfolio_id": portfolio_id,
            "portfolio_unique_hits_captured": len(union_hits),
            "hit_numbers": list(union_hits),
        }

        if log_fn:
            log_fn(
                f"Evaluación de la Cartera completa: Capturó {len(union_hits)} números ganadores en total a través de la cartera jugada."
            )

    return {
        "portfolio_id": portfolio_id,
        "coverage": coverage,
        "played_count": len(played_candidates),
        "evaluation": evaluation,
    }
