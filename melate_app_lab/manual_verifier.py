from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .memory import DEFAULT_DB_PATH
from .historical_store import load_draw_history, suggest_next_draw
from .candidate_generator import analyze_time_window
from .relation_graph import build_historical_relation_graph
from .feature_extractor import extract_features
from .statistical_crosscheck import (
    analyze_candidate_statistical_profile,
    analyze_portfolio_statistical_profile,
)
from .metrics import average_internal_overlap, high_redundancy_pairs


def parse_manual_combinations(manual_text: str) -> dict[str, Any]:
    """Parse manual tickets in various formats: A: 1 2 3 4 5 6 or commas.

    Validates ranges, lengths, and duplicates.
    """
    candidates = []
    errors = []
    lines = manual_text.strip().split("\n")

    for idx, line in enumerate(lines):
        line_num = idx + 1
        cleaned = line.strip()
        if not cleaned:
            continue

        label = f"M{line_num}"
        if ":" in cleaned:
            parts = cleaned.split(":", 1)
            lbl = parts[0].strip()
            if lbl:
                label = lbl
            cleaned = parts[1].strip()

        raw_parts = cleaned.replace(",", " ").split()

        try:
            nums = [int(p) for p in raw_parts]
        except ValueError:
            errors.append(f"Línea {line_num}: Contiene caracteres no numéricos.")
            continue

        if len(nums) != 6:
            errors.append(
                f"Línea {line_num}: Se esperaban exactamente 6 números (se encontraron {len(nums)})."
            )
            continue

        out_of_range = [n for n in nums if n < 1 or n > 56]
        if out_of_range:
            errors.append(f"Línea {line_num}: Números fuera del rango 1-56: {out_of_range}.")
            continue

        if len(set(nums)) != 6:
            errors.append(f"Línea {line_num}: Contiene números duplicados.")
            continue

        candidates.append({"label": label, "numbers": sorted(nums)})

    success = len(errors) == 0 and len(candidates) > 0
    return {"success": success, "candidates": candidates, "errors": errors}


def verify_manual_combinations(
    manual_text: str,
    game: str = "revancha",
    draw: int | None = None,
    seed: int = 42,
    pool_size: int = 1000,
    use_structural_diversification: bool = True,
    include_statistical_crosscheck: bool = True,
    use_feedback_profile: bool = False,
    use_ml: bool = False,
    ml_model: str | None = None,
    compare_against_generated: bool = True,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Calculate model features, rank scores, structural signals, and statistical profiles

    for manual combinations, and optionally compare them against a generated portfolio.
    """
    # 1. Parse manual input
    parsed = parse_manual_combinations(manual_text)
    if not parsed["success"]:
        return {
            "success": False,
            "errors": parsed["errors"],
            "notes": ["Fallo al parsear las combinaciones manuales."],
        }

    manual_candidates = parsed["candidates"]

    # 2. Load DB history
    history = load_draw_history(db_path)
    if not history:
        return {
            "success": False,
            "errors": ["El historial en la base de datos está vacío."],
        }

    target_draw = draw if draw is not None else suggest_next_draw(db_path)
    prior_history = [d for d in history if d["draw"] < target_draw]
    if not prior_history:
        prior_history = history

    train_history = prior_history[-30:] if len(prior_history) >= 30 else prior_history
    analysis = analyze_time_window(prior_history, window=30)
    graph_data = build_historical_relation_graph(prior_history, window=30, game=game)

    # 3. Process each manual candidate
    processed_manuals = []
    for cand in manual_candidates:
        nums = cand["numbers"]
        lbl = cand["label"]

        # Extract baseline features
        feats = extract_features(nums, train_history, prior_history, graph_data)

        # Apply ranker
        common_sigs = analysis.get("common_signatures", [])
        common_bands = analysis.get("common_bands", [])

        # Weights if feedback active
        weights = None
        if use_feedback_profile:
            from .thesis_memory import get_active_feedback_profile
            active = get_active_feedback_profile(db_path, game)
            if active:
                weights = active["weights"]

        # Machine learning scoring if active and available
        from .candidate_ranker import score_candidate
        rank_score = score_candidate(feats, common_sigs, common_bands, weights=weights)

        if use_ml:
            from .ml_ranker import is_ml_available, train_ml_ranker, rank_candidates_ml
            if is_ml_available():
                prior_draw_ids = [d["draw"] for d in prior_history]
                ml_train_draws = prior_draw_ids[-30:] if len(prior_draw_ids) >= 30 else prior_draw_ids
                model = train_ml_ranker(history, ml_train_draws, window=30, game=game)
                ml_res = rank_candidates_ml(model, [feats], common_sigs, common_bands)
                if ml_res:
                    rank_score = ml_res[0].get("rank_score", rank_score)

        feats["rank_score"] = rank_score

        # Apply structural signals
        from .structural_signal_engine import compute_structural_signals_batch
        struct_res = compute_structural_signals_batch([feats], prior_history, window=30)
        feats = struct_res[0]

        # Apply statistical crosscheck
        stat_prof = {}
        if include_statistical_crosscheck:
            stat_prof = analyze_candidate_statistical_profile(nums, prior_history)

        processed_manuals.append({
            "label": lbl,
            "numbers": nums,
            "rank_score": round(feats.get("rank_score", 0.0), 4),
            "classification": feats.get("classification", "Manual"),
            "graph_support_score": feats.get("graph_support_score", 0.0),
            "structural": {
                "structural_signal_score": round(feats.get("structural_signal_score", 0.0), 4),
                "pair_lag_score": round(feats.get("pair_lag_score", 0.0), 4),
                "block_activity_score": round(feats.get("block_activity_score", 0.0), 4),
                "gap_echo_score": round(feats.get("gap_echo_score", 0.0), 4),
                "block_signature": feats.get("block_signature", ""),
                "gap_family": feats.get("gap_family", ""),
            },
            "statistical_crosscheck": stat_prof,
            "manual_review_notes": stat_prof.get("statistical_notes", []),
        })

    # 4. Calculate manual portfolio-level stats
    nums_only = [c["numbers"] for c in processed_manuals]
    avg_overlap = average_internal_overlap(nums_only)
    high_red = high_redundancy_pairs(nums_only)

    avg_rank = sum(c["rank_score"] for c in processed_manuals) / len(processed_manuals)
    avg_struct = sum(c["structural"]["structural_signal_score"] for c in processed_manuals) / len(processed_manuals)

    unique_sigs = len({c["structural"]["block_signature"] for c in processed_manuals})
    unique_gaps = len({c["structural"]["gap_family"] for c in processed_manuals if c["structural"]["gap_family"]})

    manual_portfolio_metrics = {
        "average_rank_score": round(avg_rank, 4),
        "average_internal_overlap": round(avg_overlap, 4),
        "high_redundancy_pairs": high_red,
        "unique_block_signatures": unique_sigs,
        "unique_gap_families": unique_gaps,
        "average_structural_signal_score": round(avg_struct, 4),
    }

    # 5. Optional generated comparison
    comparison_data = {}
    notes = ["Revisión manual completada."]
    alerts = []

    if compare_against_generated:
        from .desktop_controller import generate_automatic_review
        gen_res = generate_automatic_review(
            db_path=db_path,
            game=game,
            draw=target_draw,
            count=len(processed_manuals),
            pool_size=pool_size,
            seed=seed,
            use_structural_diversification=use_structural_diversification,
            structural_diversity_weight=1.0,
            include_statistical_crosscheck=include_statistical_crosscheck,
            use_optimizer=True,
            use_feedback_profile=use_feedback_profile,
            use_ml=use_ml,
            ml_model=ml_model,
            auto_save=False,
        )

        if gen_res.get("success"):
            gen_portfolio = gen_res["final_portfolio"]

            # Match checks
            exact_matches = []
            highest_overlap = []

            for m_idx, m_cand in enumerate(processed_manuals):
                m_set = set(m_cand["numbers"])
                best_over = 0
                best_label = ""
                for g_cand in gen_portfolio:
                    g_set = set(g_cand["numbers"])
                    intersect = len(m_set & g_set)
                    g_label = g_cand.get("letter", "?")

                    if intersect == 6:
                        exact_matches.append({
                            "manual_label": m_cand["label"],
                            "generated_label": g_label,
                            "numbers": m_cand["numbers"]
                        })
                    if intersect > best_over:
                        best_over = intersect
                        best_label = g_label

                if best_over in (3, 4, 5):
                    highest_overlap.append({
                        "manual_label": m_cand["label"],
                        "generated_label": best_label,
                        "overlap_count": best_over,
                        "numbers": m_cand["numbers"]
                    })

            # Redundancy comparison
            gen_metrics = gen_res.get("internal_checks", {})

            comparison_data = {
                "generated_portfolio_id": gen_res.get("portfolio_id"),
                "exact_matches": exact_matches,
                "highest_overlap_matches": highest_overlap,
                "manual_vs_generated_overlap": round(avg_overlap - gen_metrics.get("average_internal_overlap", 0.0), 4),
                "manual_average_rank_score": round(avg_rank, 4),
                "generated_average_rank_score": gen_metrics.get("average_rank_score", 0.0),
                "manual_average_structural_signal_score": round(avg_struct, 4),
                "generated_average_structural_signal_score": gen_metrics.get("average_structural_signal_score", 0.0),
                "manual_average_internal_overlap": round(avg_overlap, 4),
                "generated_average_internal_overlap": gen_metrics.get("average_internal_overlap", 0.0),
                "comparison_notes": [
                    f"Se encontraron {len(exact_matches)} coincidencias exactas con la cartera modelo.",
                    f"Se encontraron {len(highest_overlap)} combinaciones manuales con solapamientos altos (>=3 números) con el modelo.",
                ],
            }

            if len(exact_matches) > 0:
                notes.append("Consistencia descriptiva detectada: Combinaciones manuales coinciden exactamente con la cartera de tesis del modelo.")
            if avg_rank < gen_metrics.get("average_rank_score", 0.0) * 0.8:
                alerts.append("Menor soporte histórico promedio en la cartera manual respecto a la cartera modelo.")
        else:
            notes.append("No fue posible generar la cartera de contraste modelo.")

    return {
        "success": True,
        "game": game,
        "draw": target_draw,
        "config": {
            "game": game,
            "draw": target_draw,
            "seed": seed,
            "pool_size": pool_size,
            "use_structural_diversification": use_structural_diversification,
            "use_feedback_profile": use_feedback_profile,
            "use_ml": use_ml,
            "ml_model": ml_model,
        },
        "manual_candidates": processed_manuals,
        "manual_portfolio_metrics": manual_portfolio_metrics,
        "generated_portfolio_comparison": comparison_data,
        "alerts": alerts,
        "notes": notes,
    }


def save_manual_portfolio(
    manual_verify_result: dict[str, Any],
    notes: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Save manual verify results into the database as a thesis portfolio.

    Contains 'source': 'manual_verification' inside its JSON notes.
    """
    from .thesis_memory import save_thesis_portfolio

    m_cands = manual_verify_result["manual_candidates"]
    formatted_candidates = []

    # Map manual verify objects to thesis candidates schema
    for idx, c in enumerate(m_cands):
        # We save detailed metadata as a JSON string inside notes
        c_notes = {
            "label": c["label"],
            "rank_score": c["rank_score"],
            "selection_reason": "Verificación manual del usuario",
            "source": "manual_verification",
            "structural": c["structural"],
            "statistical_crosscheck": c["statistical_crosscheck"],
        }
        from .number_utils import sum_band, block_signature
        s_val = sum(c["numbers"])
        formatted_candidates.append({
            "numbers": c["numbers"],
            "classification": c["classification"],
            "graph_support_score": c["graph_support_score"],
            "sum": s_val,
            "sum_band": sum_band(s_val),
            "block_signature": block_signature(c["numbers"]),
            "notes": json.dumps(c_notes, ensure_ascii=False),
        })

    portfolio_notes = {
        "source": "manual_verification",
        "user_notes": notes or "",
        "config": manual_verify_result["config"],
        "metrics": manual_verify_result["manual_portfolio_metrics"],
    }

    portfolio_id = save_thesis_portfolio(
        db_path=db_path,
        draw=manual_verify_result["draw"],
        game=manual_verify_result["game"],
        candidates=formatted_candidates,
        notes=json.dumps(portfolio_notes, ensure_ascii=False),
    )

    return portfolio_id
