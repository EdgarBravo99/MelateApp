from __future__ import annotations

import pytest
from melate_app_lab.structural_signals import (
    analyze_structural_signals,
    score_candidate_structural_signals,
)


def test_structural_signals_integration():
    prior_history = [
        {"draw": 101, "numbers": [1, 5, 13, 18, 28, 40]},
        {"draw": 102, "numbers": [1, 2, 3, 4, 5, 6]},
    ]

    # No se requiere ni se proporciona target_draw
    structural_data = analyze_structural_signals(prior_history, window=2, gap_window=2, max_lag=2)

    # Verificar que contiene los datos de las tres señales
    assert "pair_lag_data" in structural_data
    assert "block_activity" in structural_data
    assert "gap_patterns" in structural_data

    # Evaluar un candidato
    # Números: 1, 5, 13, 18, 28, 40 (Signature: 3-7-4-9-11)
    cand = [1, 5, 13, 18, 28, 40]
    res = score_candidate_structural_signals(cand, structural_data)

    # Verificar que produce un score de señal estructural combinando las tres señales
    assert "pair_lag_score" in res
    assert "block_activity_score" in res
    assert "gap_echo_score" in res
    assert "structural_signal_score" in res

    # 0.40 * pair_lag + 0.35 * block_activity + 0.25 * gap_echo
    expected_score = (
        0.40 * res["pair_lag_score"]
        + 0.35 * res["block_activity_score"]
        + 0.25 * res["gap_echo_score"]
    )
    assert abs(res["structural_signal_score"] - expected_score) < 0.0001
    assert len(res["structural_notes"]) > 0


def test_structural_signals_empty_history():
    structural_data = analyze_structural_signals([], window=10, gap_window=10, max_lag=2)
    res = score_candidate_structural_signals([1, 2, 3, 4, 5, 6], structural_data)

    assert res["pair_lag_score"] == 0.0
    assert res["block_activity_score"] == 0.0
    assert res["gap_echo_score"] == 0.0
    assert res["structural_signal_score"] == 0.0
    assert len(res["structural_notes"]) > 0


def test_structural_signals_determinism():
    prior_history = [
        {"draw": 101, "numbers": [1, 5, 13, 18, 28, 40]},
    ]

    res1 = analyze_structural_signals(prior_history, window=1, gap_window=1, max_lag=2)
    res2 = analyze_structural_signals(prior_history, window=1, gap_window=1, max_lag=2)
    assert res1 == res2

    score1 = score_candidate_structural_signals([1, 5, 13, 18, 28, 40], res1)
    score2 = score_candidate_structural_signals([1, 5, 13, 18, 28, 40], res2)
    assert score1 == score2


def test_structural_signal_engine_imports_and_functionality():
    # Importación explícita solicitada
    from melate_app_lab.structural_signal_engine import (
        compute_structural_signals,
        compute_structural_signals_batch,
    )

    prior_history = [
        {"draw": 101, "numbers": [1, 5, 13, 18, 28, 40]},
        {"draw": 102, "numbers": [1, 2, 3, 4, 5, 6]},
    ]

    # Test single compute
    res_single = compute_structural_signals([1, 5, 13, 18, 28, 40], prior_history, window=2, gap_window=2, max_lag=2)
    assert res_single["structural_signal_score"] > 0.0

    # Test batch compute
    candidates = [[1, 5, 13, 18, 28, 40], [1, 2, 3, 4, 5, 6]]
    res_batch = compute_structural_signals_batch(candidates, prior_history, window=2, gap_window=2, max_lag=2)
    assert len(res_batch) == 2
    assert res_batch[0]["structural_signal_score"] == res_single["structural_signal_score"]


def test_structural_signal_edge_cases():
    from melate_app_lab.structural_signal_engine import (
        compute_structural_signals,
        compute_structural_signals_batch,
    )
    from melate_app_lab.pair_lag_analyzer import score_pair_lag_support

    prior_history = [
        {"draw": 101, "numbers": [1, 5, 13, 18, 28, 40]},
    ]

    # 1. score_pair_lag_support does not crash with [] or [1]
    res_empty = score_pair_lag_support([], {})
    assert res_empty["pair_lag_score"] == 0.0
    assert res_empty["bridge_pairs"] == []

    res_single = score_pair_lag_support([1], {})
    assert res_single["pair_lag_score"] == 0.0
    assert res_single["bridge_pairs"] == []

    # 2. compute_structural_signals_batch accepts list[dict] with "numbers" and preserves rank_score
    candidates_dict = [
        {"numbers": [1, 5, 13, 18, 28, 40], "rank_score": 10.5},
        {"numbers": [1, 2, 3, 4, 5, 6], "rank_score": 8.2},
    ]

    res_batch = compute_structural_signals_batch(
        candidates_dict,
        prior_history,
        window=1,
        gap_window=1,
        max_lag=2,
    )

    assert len(res_batch) == 2
    # Should be dict type
    assert isinstance(res_batch[0], dict)
    assert res_batch[0]["rank_score"] == 10.5
    assert res_batch[1]["rank_score"] == 8.2
    assert "structural_signal_score" in res_batch[0]
    assert "structural_signal_score" in res_batch[1]


