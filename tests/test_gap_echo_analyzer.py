from __future__ import annotations

import pytest
from melate_app_lab.gap_echo_analyzer import (
    analyze_gap_patterns,
    classify_gap_family,
    get_gap_signature,
    score_gap_echo,
)


def test_gap_signature_generation():
    # Números: 1, 5, 13, 18, 28, 40
    # Gaps:
    # 5 - 1 - 1 = 3
    # 13 - 5 - 1 = 7
    # 18 - 13 - 1 = 4
    # 28 - 18 - 1 = 9
    # 40 - 28 - 1 = 11
    # Signature: 3-7-4-9-11
    assert get_gap_signature([1, 5, 13, 18, 28, 40]) == "3-7-4-9-11"


def test_gap_family_classification():
    # Compact: total <= 15 o max_g <= 4
    assert classify_gap_family([1, 1, 1, 1, 1]) == "compact"

    # Wide: total >= 35 o max_g >= 15
    assert classify_gap_family([16, 2, 2, 2, 2]) == "wide"
    assert classify_gap_family([5, 6, 7, 8, 9]) == "wide"  # total = 35

    # Balanced: 16 <= total <= 34 y max_g <= 10
    assert classify_gap_family([4, 4, 4, 4, 4]) == "balanced"  # total = 20, max_g = 4

    # Mixed: de otro modo
    assert classify_gap_family([12, 1, 1, 1, 1]) == "mixed"  # total = 16, max_g = 12


def test_gap_signature_repetition_and_similarity():
    prior_history = [
        {"draw": 1, "numbers": [1, 5, 13, 18, 28, 40]},  # Signature: 3-7-4-9-11
        {"draw": 2, "numbers": [1, 5, 13, 18, 28, 40]},
    ]

    analysis = analyze_gap_patterns(prior_history, window=2)

    # 1. Exact match
    res1 = score_gap_echo([1, 5, 13, 18, 28, 40], analysis)
    assert len(res1["matched_gap_patterns"]) > 0
    assert res1["matched_gap_patterns"][0]["count"] == 2
    assert res1["gap_echo_score"] > 0.30

    # 2. Similar match (Manhattan distance <= 4)
    # Candidato: 1, 5, 13, 18, 28, 39 (Signature: 3-7-4-9-10)
    # Distancia Manhattan con 3-7-4-9-11 es |10 - 11| = 1 <= 4.
    res2 = score_gap_echo([1, 5, 13, 18, 28, 39], analysis)
    assert res2["gap_echo_score"] > 0.10


def test_gap_extreme_penalization():
    prior_history = [
        {"draw": 1, "numbers": [1, 10, 20, 30, 40, 50]},  # Balanced gaps
    ]

    analysis = analyze_gap_patterns(prior_history, window=1)

    # Candidato con gaps extremadamente comprimidos (total = 0, gaps = [0, 0, 0, 0, 0])
    # Sin soporte exacto ni similar, debe recibir penalización
    cand_compressed = [1, 2, 3, 4, 5, 6]
    res_compressed = score_gap_echo(cand_compressed, analysis)
    assert res_compressed["gap_echo_score"] == 0.0  # Penalización aplicada, baja a 0


def test_gap_echo_empty_history():
    analysis = analyze_gap_patterns([], window=10)
    assert analysis["gap_signatures_counts"] == {}

    res = score_gap_echo([1, 2, 3, 4, 5, 6], analysis)
    assert res["gap_echo_score"] == 0.0
    assert res["matched_gap_patterns"] == []
    assert len(res["gap_echo_notes"]) > 0


def test_gap_echo_determinism():
    prior_history = [
        {"draw": 1, "numbers": [1, 5, 13, 18, 28, 40]},
    ]

    res1 = analyze_gap_patterns(prior_history, window=1)
    res2 = analyze_gap_patterns(prior_history, window=1)
    assert res1 == res2

    score1 = score_gap_echo([1, 5, 13, 18, 28, 40], res1)
    score2 = score_gap_echo([1, 5, 13, 18, 28, 40], res2)
    assert score1 == score2
