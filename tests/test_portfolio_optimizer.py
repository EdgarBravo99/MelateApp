from __future__ import annotations

import pytest
from melate_app_lab.portfolio_optimizer import (
    optimize_portfolio,
    calculate_portfolio_structural_metrics,
)


def test_calculate_portfolio_structural_metrics_empty():
    res = calculate_portfolio_structural_metrics([])
    assert res["unique_block_signatures"] == 0
    assert res["unique_gap_families"] == 0
    assert res["average_structural_signal_score"] == 0.0
    assert res["dominant_block_signature_ratio"] == 0.0
    assert res["dominant_gap_family_ratio"] == 0.0
    assert res["average_pair_overlap"] == 0.0
    assert res["structural_profile_coverage"] == 0.0


def test_calculate_portfolio_structural_metrics_values():
    portfolio = [
        {
            "numbers": [1, 2, 3, 4, 5, 6],
            "block_signature": "6-0-0-0-0",
            "gap_family": "compact",
            "structural_signal_score": 0.8,
        },
        {
            "numbers": [1, 2, 3, 7, 8, 9],
            "block_signature": "6-0-0-0-0",
            "gap_family": "balanced",
            "structural_signal_score": 0.6,
        },
        {
            "numbers": [10, 11, 12, 13, 14, 15],
            "block_signature": "0-6-0-0-0",
            "gap_family": "compact",
            "structural_signal_score": 0.4,
        }
    ]
    res = calculate_portfolio_structural_metrics(portfolio)
    assert res["unique_block_signatures"] == 2
    assert res["unique_gap_families"] == 2
    assert res["average_structural_signal_score"] == pytest.approx(0.6)
    assert res["dominant_block_signature_ratio"] == round(2 / 3, 4)
    assert res["dominant_gap_family_ratio"] == round(2 / 3, 4)
    # pair overlap between 1 and 2: set([1,2,3]) overlap -> 3 numbers -> 3 pairs
    # pair overlap between 1 and 3: 0 pairs
    # pair overlap between 2 and 3: 0 pairs
    # average pair overlap = 3 / 3 = 1.0
    assert res["average_pair_overlap"] == pytest.approx(1.0)
    # unique profiles: (6-0-0-0-0, compact), (6-0-0-0-0, balanced), (0-6-0-0-0, compact) -> 3 unique profiles
    # coverage = 3 / 3 = 1.0
    assert res["structural_profile_coverage"] == 1.0


def test_optimize_portfolio_default_behavior():
    candidates = [
        {"numbers": [1, 2, 3, 4, 5, 6], "rank_score": 10.0},
        {"numbers": [1, 2, 3, 4, 5, 7], "rank_score": 9.5},  # high overlap
        {"numbers": [10, 11, 12, 13, 14, 15], "rank_score": 8.0},  # low overlap
    ]
    
    # use_structural_diversification=False
    selected_normal = optimize_portfolio(candidates, top_k=2, use_structural_diversification=False)
    # Cand 1 and Cand 3 should be selected since Cand 2 has a high overlap penalty
    assert len(selected_normal) == 2
    assert selected_normal[0]["numbers"] == [1, 2, 3, 4, 5, 6]
    assert selected_normal[1]["numbers"] == [10, 11, 12, 13, 14, 15]


def test_optimize_portfolio_structural_diversification():
    # Cand 1 and Cand 2 have same block signature, Cand 3 has a different one.
    # Base scores: Cand 1 (10.0), Cand 2 (9.8), Cand 3 (9.0).
    candidates = [
        {
            "numbers": [1, 2, 3, 4, 5, 6],
            "rank_score": 10.0,
            "block_signature": "6-0-0-0-0",
            "gap_family": "compact",
            "structural_signal_score": 0.9,
        },
        {
            "numbers": [7, 8, 9, 10, 11, 12],  # No number overlap, but same signature/gap family
            "rank_score": 9.8,
            "block_signature": "6-0-0-0-0",
            "gap_family": "compact",
            "structural_signal_score": 0.8,
        },
        {
            "numbers": [13, 14, 15, 16, 17, 18],  # Different signature and gap family
            "rank_score": 9.0,
            "block_signature": "0-6-0-0-0",
            "gap_family": "balanced",
            "structural_signal_score": 0.5,
        }
    ]
    
    # With diversification active, Cand 3 should be selected instead of Cand 2 to maximize diversity
    selected_div = optimize_portfolio(candidates, top_k=2, use_structural_diversification=True, structural_diversity_weight=2.0)
    assert len(selected_div) == 2
    assert selected_div[0]["numbers"] == [1, 2, 3, 4, 5, 6]
    assert selected_div[1]["numbers"] == [13, 14, 15, 16, 17, 18]
    
    # Verify selection_reason is present
    assert "selection_reason" in selected_div[1]
    assert "block_signature" in selected_div[1]["selection_reason"] or "gap_family" in selected_div[1]["selection_reason"] or "baja redundancia" in selected_div[1]["selection_reason"]


def test_optimize_portfolio_no_rank_score_modified():
    candidates = [
        {
            "numbers": [1, 2, 3, 4, 5, 6],
            "rank_score": 10.0,
            "block_signature": "6-0-0-0-0",
            "gap_family": "compact",
            "structural_signal_score": 0.9,
        },
        {
            "numbers": [10, 11, 12, 13, 14, 15],
            "rank_score": 8.0,
            "block_signature": "0-6-0-0-0",
            "gap_family": "balanced",
            "structural_signal_score": 0.4,
        }
    ]
    
    optimize_portfolio(candidates, top_k=2, use_structural_diversification=True)
    # Check that rank_score was not mutated/altered
    assert candidates[0]["rank_score"] == 10.0
    assert candidates[1]["rank_score"] == 8.0


def test_optimize_portfolio_missing_fields_robustness():
    # Should not crash if structural fields are missing
    candidates = [
        {"numbers": [1, 2, 3, 4, 5, 6], "rank_score": 10.0},
        {"numbers": [10, 11, 12, 13, 14, 15], "rank_score": 8.0},
    ]
    selected = optimize_portfolio(candidates, top_k=2, use_structural_diversification=True)
    assert len(selected) == 2
