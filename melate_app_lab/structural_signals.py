from __future__ import annotations

import logging
from typing import Any

from .pair_lag_analyzer import analyze_pair_lag, score_pair_lag_support
from .block_activation_analyzer import analyze_block_activity, score_block_composition
from .gap_echo_analyzer import analyze_gap_patterns, score_gap_echo

logger = logging.getLogger(__name__)


def analyze_structural_signals(
    prior_history: list[dict[str, Any]],
    window: int = 30,
    gap_window: int = 50,
    max_lag: int = 5,
) -> dict[str, Any]:
    """Precalcula los datos de los tres analizadores estructurales sobre el historial previo."""
    pair_lag_data = analyze_pair_lag(prior_history, window=window, max_lag=max_lag)
    block_activity = analyze_block_activity(prior_history, window=window)
    gap_patterns = analyze_gap_patterns(prior_history, window=gap_window)

    return {
        "pair_lag_data": pair_lag_data,
        "block_activity": block_activity,
        "gap_patterns": gap_patterns,
    }


def score_candidate_structural_signals(
    candidate_features: list[int] | dict[str, Any],
    structural_data: dict[str, Any],
) -> dict[str, Any]:
    """Evalúa un candidato combinando las tres señales estructurales con pesos ponderados."""
    if isinstance(candidate_features, dict):
        candidate_numbers = candidate_features.get("numbers", [])
    else:
        candidate_numbers = candidate_features

    if not structural_data:
        return {
            "pair_lag_score": 0.0,
            "block_activity_score": 0.0,
            "gap_echo_score": 0.0,
            "structural_signal_score": 0.0,
            "bridge_pairs": [],
            "activated_blocks": [],
            "block_signature": "",
            "gap_signature": "",
            "gap_family": "",
            "structural_notes": ["Sin datos estructurales debido a historial insuficiente."],
        }

    pair_lag_data = structural_data.get("pair_lag_data", {})
    block_activity = structural_data.get("block_activity", {})
    gap_patterns = structural_data.get("gap_patterns", {})

    # Calcular resultados individuales
    pair_lag_res = score_pair_lag_support(candidate_numbers, pair_lag_data)
    block_res = score_block_composition(candidate_numbers, block_activity)
    gap_res = score_gap_echo(candidate_numbers, gap_patterns)

    pair_lag_score = pair_lag_res["pair_lag_score"]
    block_activity_score = block_res["block_activity_score"]
    gap_echo_score = gap_res["gap_echo_score"]

    # Calcular score estructural descriptivo ponderado
    # 0.40 * pair_lag_score + 0.35 * block_activity_score + 0.25 * gap_echo_score
    raw_score = (
        0.40 * pair_lag_score
        + 0.35 * block_activity_score
        + 0.25 * gap_echo_score
    )
    structural_signal_score = max(0.0, min(1.0, raw_score))

    # Consolidar notas descriptivas
    structural_notes = []
    structural_notes.extend(pair_lag_res.get("pair_lag_notes", []))
    structural_notes.extend(block_res.get("block_activity_notes", []))
    structural_notes.extend(gap_res.get("gap_echo_notes", []))

    return {
        "pair_lag_score": pair_lag_score,
        "block_activity_score": block_activity_score,
        "gap_echo_score": gap_echo_score,
        "structural_signal_score": round(structural_signal_score, 4),
        "bridge_pairs": pair_lag_res.get("bridge_pairs", []),
        "activated_blocks": block_res.get("activated_blocks", []),
        "block_signature": block_res.get("block_signature", ""),
        "gap_signature": gap_res.get("gap_signature", ""),
        "gap_family": gap_res.get("gap_family", ""),
        "structural_notes": structural_notes,
    }


def compute_structural_signals(
    candidate: list[int] | dict[str, Any],
    prior_history: list[dict[str, Any]],
    window: int = 30,
    gap_window: int = 50,
    max_lag: int = 5,
    structural_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calcula y puntúa las señales estructurales para un único candidato."""
    if structural_data is None:
        structural_data = analyze_structural_signals(
            prior_history,
            window=window,
            gap_window=gap_window,
            max_lag=max_lag,
        )
    score_res = score_candidate_structural_signals(candidate, structural_data)
    if isinstance(candidate, dict):
        new_dict = dict(candidate)
        new_dict.update(score_res)
        return new_dict
    return score_res


def compute_structural_signals_batch(
    candidates: list[list[int]] | list[dict[str, Any]],
    prior_history: list[dict[str, Any]],
    window: int = 30,
    gap_window: int = 50,
    max_lag: int = 5,
) -> list[dict[str, Any]]:
    """Calcula y puntúa las señales estructurales para un lote de candidatos."""
    structural_data = analyze_structural_signals(
        prior_history,
        window=window,
        gap_window=gap_window,
        max_lag=max_lag,
    )
    results = []
    for c in candidates:
        score_res = score_candidate_structural_signals(c, structural_data)
        if isinstance(c, dict):
            new_dict = dict(c)
            new_dict.update(score_res)
            results.append(new_dict)
        else:
            results.append(score_res)
    return results
