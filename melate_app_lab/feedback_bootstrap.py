from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .candidate_generator import analyze_time_window
from .candidate_ranker import rank_candidates
from .candidate_search import search_candidates
from .feature_extractor import extract_features_batch
from .historical_store import load_draw_history
from .portfolio_evaluator import evaluate_existing_portfolio
from .portfolio_optimizer import optimize_portfolio
from .relation_graph import build_historical_relation_graph
from .thesis_memory import get_active_feedback_profile, save_thesis_portfolio
from .workflow_loop import classify_candidate, evaluate_portfolio_coverage
from .metrics import calculate_hits

logger = logging.getLogger(__name__)


def _is_draw_already_bootstrapped(db_path: Path, draw: int, game: str, config: dict[str, Any]) -> bool:
    """Verifica si ya existe un portafolio de bootstrap con exactamente la misma configuración."""
    import sqlite3
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "select notes from thesis_portfolios where draw = ? and game = ?",
                (draw, game)
            )
            for row in cursor.fetchall():
                notes_str = row[0]
                if not notes_str:
                    continue
                try:
                    notes = json.loads(notes_str)
                    existing_config = notes.get("bootstrap_config")
                    if existing_config == config:
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def bootstrap_reviewed_portfolios(
    db_path: str | Path,
    game: str = "revancha",
    from_draw: int | None = None,
    to_draw: int | None = None,
    limit: int = 20,
    pool_size: int = 1000,
    top_k: int = 10,
    seed: int = 42,
    mark_all_as_played: bool = True,
    use_feedback_profile: bool = False,
    use_optimizer: bool = True,
    skip_existing: bool = True,
) -> dict[str, Any]:
    """Crea carteras retrospectivas revisadas para alimentar el loop de retroalimentación (feedback loop).
    
    Usa evaluación walk-forward estricta sin lookahead bias.
    """
    db_path = Path(db_path)
    
    # 1. Cargar historial del juego específico
    history = load_draw_history(db_path, game=game)
    filtered_history = [d for d in history if str(d.get("game", "")).casefold() == game.casefold()]
    filtered_history.sort(key=lambda d: d.get("draw", 0))

    # 2. Identificar sorteos elegibles (requieren mínimo de 30 sorteos previos de historial)
    eligible_draws = []
    for i, d in enumerate(filtered_history):
        prior_history = filtered_history[:i]
        if len(prior_history) >= 30:
            eligible_draws.append(d)

    # Filtrar por rango de sorteos
    if from_draw is not None:
        eligible_draws = [d for d in eligible_draws if d["draw"] >= from_draw]
    if to_draw is not None:
        eligible_draws = [d for d in eligible_draws if d["draw"] <= to_draw]

    # Limitar la cantidad a los últimos 'limit' sorteos elegibles
    if limit is not None and limit > 0:
        target_draws = eligible_draws[-limit:]
    else:
        target_draws = eligible_draws

    if not target_draws:
        return {
            "success": False,
            "message": "No se encontraron sorteos elegibles en el historial.",
            "portfolios_created": 0,
            "draws_processed": [],
            "skipped_draws": [],
            "seed": seed,
            "pool_size": pool_size,
            "top_k": top_k,
            "from_draw": from_draw,
            "to_draw": to_draw,
            "use_optimizer": use_optimizer,
            "use_feedback_profile": use_feedback_profile,
            "mark_all_as_played": mark_all_as_played,
            "high_redundancy_pairs": 0.0,
        }

    config_dict = {
        "seed": seed,
        "pool_size": pool_size,
        "top_k": top_k,
        "use_optimizer": use_optimizer,
        "use_feedback_profile": use_feedback_profile,
    }

    portfolios_created = 0
    draws_processed = []
    skipped_draws = []
    all_max_hits = []
    rate_2plus_list = []
    rate_3plus_list = []
    unique_hits_union_list = []
    average_internal_overlaps = []
    high_redundancy_pairs_list = []

    for d in target_draws:
        target_draw = d["draw"]
        target_numbers = d["numbers"]

        # Evitar duplicados
        if skip_existing and _is_draw_already_bootstrapped(db_path, target_draw, game, config_dict):
            skipped_draws.append(target_draw)
            continue

        # Evitar lookahead bias: solo historial strictly menor al target_draw
        prior_history = [x for x in filtered_history if x["draw"] < target_draw]
        
        # Pipeline idéntico a producción
        analysis = analyze_time_window(prior_history, window=30)
        graph_data = build_historical_relation_graph(prior_history, window=30, game=game)
        
        # Semilla reproducible por sorteo
        candidate_pool = search_candidates(analysis, pool_size=pool_size, seed=seed + target_draw)
        
        # Extracción de características
        train_history = prior_history[-30:] if len(prior_history) >= 30 else prior_history
        cand_features = extract_features_batch(candidate_pool, train_history, prior_history, graph_data)
        
        common_sigs = analysis.get("common_signatures", [])
        common_bands = analysis.get("common_bands", [])
        
        # Aplicar feedback profile si use_feedback_profile=True y existe
        weights = None
        if use_feedback_profile:
            active_profile = get_active_feedback_profile(db_path, game)
            weights = active_profile["weights"] if active_profile else None
        
        # Rankear candidatos
        ranked = rank_candidates(cand_features, common_sigs, common_bands, weights=weights)
        
        # Selección por optimizador o naive top_k
        if use_optimizer:
            selected_portfolio = optimize_portfolio(ranked, top_k)
        else:
            selected_portfolio = ranked[:top_k]

        # Construir estructura para persistencia
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

        candidates_payload = []
        for c in selected_portfolio:
            strat = classify_candidate(c)
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
                "state": "Jugado" if mark_all_as_played else "Pendiente",
                "sum": c["sum"],
                "sum_band": c["sum_band"],
                "block_signature": c["block_signature"],
                "graph_support_score": c["graph_support_score"],
                "rank_score": c.get("rank_score", 0.0),
                "pair_edges": pair_edges,
                "evidence_draws": evidence_draws,
                "notes": f"Generado en bootstrap retrospectivo para sorteo {target_draw}",
            })

        coverage = evaluate_portfolio_coverage(candidates_payload)
        
        notes_dict = {
            "coverage": coverage,
            "bootstrap_config": config_dict
        }
        notes_payload = json.dumps(notes_dict)

        # 5. Guardar thesis_portfolio
        portfolio_id = save_thesis_portfolio(
            db_path,
            draw=target_draw,
            game=game,
            candidates=candidates_payload,
            notes=notes_payload,
        )

        # 6. Evaluar la cartera usando evaluate_existing_portfolio
        # Esto automáticamente calcula hits_count, result_numbers y marca como 'Revisado'
        eval_res = evaluate_existing_portfolio(
            db_path=db_path,
            portfolio_id=portfolio_id,
            result_numbers=target_numbers,
            game=game,
            persist=True,
        )

        # Calcular métricas para el resumen
        hits_list = [calculate_hits(c["numbers"], target_numbers) for c in selected_portfolio]
        max_hits = max(hits_list) if hits_list else 0

        portfolios_created += 1
        draws_processed.append(target_draw)
        all_max_hits.append(max_hits)
        
        metrics = eval_res["metrics"]
        rate_2plus_list.append(metrics["rate_2plus"])
        rate_3plus_list.append(metrics["rate_3plus"])
        unique_hits_union_list.append(metrics["unique_hits_union"])
        average_internal_overlaps.append(metrics["average_internal_overlap"])
        high_redundancy_pairs_list.append(metrics["high_redundancy_pairs"])

    return {
        "success": True,
        "portfolios_created": portfolios_created,
        "draws_processed": draws_processed,
        "skipped_draws": skipped_draws,
        "avg_max_hits": round(sum(all_max_hits) / portfolios_created, 2) if portfolios_created else 0.0,
        "rate_2plus": round(sum(rate_2plus_list) / portfolios_created, 2) if portfolios_created else 0.0,
        "rate_3plus": round(sum(rate_3plus_list) / portfolios_created, 2) if portfolios_created else 0.0,
        "unique_hits_union_avg": round(sum(unique_hits_union_list) / portfolios_created, 2) if portfolios_created else 0.0,
        "average_internal_overlap": round(sum(average_internal_overlaps) / portfolios_created, 2) if portfolios_created else 0.0,
        "high_redundancy_pairs": round(sum(high_redundancy_pairs_list) / portfolios_created, 2) if portfolios_created else 0.0,
        "seed": seed,
        "pool_size": pool_size,
        "top_k": top_k,
        "from_draw": from_draw,
        "to_draw": to_draw,
        "use_optimizer": use_optimizer,
        "use_feedback_profile": use_feedback_profile,
        "mark_all_as_played": mark_all_as_played,
    }
