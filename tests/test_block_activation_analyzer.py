from __future__ import annotations

import pytest
from melate_app_lab.block_activation_analyzer import (
    analyze_block_activity,
    get_block_signature,
    score_block_composition,
)


def test_block_signature_calculation():
    # Números: 1, 2 (B1), 11 (B2), 21, 22 (B3), 51 (B6)
    # B1: 2, B2: 1, B3: 2, B4: 0, B5: 0, B6: 1
    # Signature: 2-1-2-0-0-1
    numbers = [1, 2, 11, 21, 22, 51]
    assert get_block_signature(numbers) == "2-1-2-0-0-1"


def test_block_activity_and_activation():
    # Historial de 3 sorteos
    prior_history = [
        {"draw": 1, "numbers": [1, 2, 3, 4, 5, 6]},  # Todos en B1
        {"draw": 2, "numbers": [1, 2, 11, 12, 21, 22]},  # B1:2, B2:2, B3:2
        {"draw": 3, "numbers": [11, 12, 13, 14, 15, 16]},  # Todos en B2
    ]

    analysis = analyze_block_activity(prior_history, window=3)

    # total en B1: 6 + 2 = 8
    # total en B2: 2 + 6 = 8
    # total en B3: 2
    # Otros bloques: 0
    # Sorteos = 3. Promedio esperado de frecuencia = 3.
    # Bloques activos (freq > 3): B1 (8) y B2 (8)
    # Bloques fríos (freq < 3): B3 (2), B4 (0), B5 (0), B6 (0)
    assert "B1" in analysis["activated_blocks"]
    assert "B2" in analysis["activated_blocks"]
    assert "B6" in analysis["cold_blocks"]


def test_block_completion_and_overconcentration():
    prior_history = [
        {"draw": 1, "numbers": [1, 11, 21, 31, 41, 51]},  # Firma "1-1-1-1-1-1"
        {"draw": 2, "numbers": [1, 11, 21, 31, 41, 51]},
        {"draw": 3, "numbers": [1, 11, 21, 31, 41, 51]},
    ]

    analysis = analyze_block_activity(prior_history, window=3)

    # Candidato 1: Tiene la misma firma común "1-1-1-1-1-1"
    cand1 = [2, 12, 22, 32, 42, 52]
    res1 = score_block_composition(cand1, analysis)
    assert res1["block_completion"] is True
    assert res1["overconcentration_penalty"] == 0.0

    # Candidato 2: Concentra 4 números en B3 (21, 22, 23, 24)
    # B3 no está activado, por lo que la penalización por 4 números debe duplicarse (0.2 * 2 = 0.4)
    cand2 = [21, 22, 23, 24, 1, 11]
    res2 = score_block_composition(cand2, analysis)
    assert res2["overconcentration_penalty"] > 0.0


def test_block_activation_empty_history():
    analysis = analyze_block_activity([], window=10)
    assert analysis["activated_blocks"] == []
    assert analysis["cold_blocks"] == []

    res = score_block_composition([1, 2, 3, 4, 5, 6], analysis)
    assert res["block_activity_score"] == 0.0
    assert res["overconcentration_penalty"] == 0.0
    assert len(res["block_activity_notes"]) > 0


def test_block_activation_determinism():
    prior_history = [
        {"draw": 1, "numbers": [1, 2, 3, 4, 5, 6]},
        {"draw": 2, "numbers": [11, 12, 13, 14, 15, 16]},
    ]

    res1 = analyze_block_activity(prior_history, window=2)
    res2 = analyze_block_activity(prior_history, window=2)
    assert res1 == res2

    score1 = score_block_composition([1, 2, 3, 11, 12, 13], res1)
    score2 = score_block_composition([1, 2, 3, 11, 12, 13], res2)
    assert score1 == score2
