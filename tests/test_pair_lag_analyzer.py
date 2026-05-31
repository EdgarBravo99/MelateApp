from __future__ import annotations

import pytest
from melate_app_lab.pair_lag_analyzer import analyze_pair_lag, score_pair_lag_support


def test_pair_lag_exact_and_lagged_cooccurrence():
    # Sorteos cronológicos ordenados por "draw"
    prior_history = [
        {"draw": 101, "numbers": [1, 2, 3, 4, 5, 6]},
        {"draw": 102, "numbers": [10, 11, 12, 13, 14, 15]},
        {"draw": 103, "numbers": [1, 2, 20, 21, 22, 23]},  # 1 y 2 coaparecen exactamente aquí y en el 101
    ]

    analysis = analyze_pair_lag(prior_history, window=3, max_lag=2)
    pairs_info = analysis["pairs_info"]

    # 1 y 2 aparecen en sorteo 101 y 103 -> recent_exact_count para (1, 2) debe ser 2
    assert (1, 2) in pairs_info
    assert pairs_info[(1, 2)]["recent_exact_count"] == 2
    assert 101 in pairs_info[(1, 2)]["recent_draws"]
    assert 103 in pairs_info[(1, 2)]["recent_draws"]

    # Lag: 1 y 10: 1 en 101, 10 en 102 -> lag_count para (1, 10) debe ser mayor a 0 (desfase de 1 sorteo <= max_lag=2)
    assert (1, 10) in pairs_info
    assert pairs_info[(1, 10)]["recent_lag_count"] > 0
    assert 101 in pairs_info[(1, 10)]["lag_draws"]
    assert 102 in pairs_info[(1, 10)]["lag_draws"]


def test_pair_lag_ignores_outside_max_lag():
    # Sorteos separados por 4 sorteos (desfase de 4)
    prior_history = [
        {"draw": 101, "numbers": [1, 2, 3, 4, 5, 6]},
        {"draw": 102, "numbers": [30, 31, 32, 33, 34, 35]},
        {"draw": 103, "numbers": [30, 31, 32, 33, 34, 35]},
        {"draw": 104, "numbers": [30, 31, 32, 33, 34, 35]},
        {"draw": 105, "numbers": [10, 11, 12, 13, 14, 15]},
    ]

    # max_lag = 2, por lo que el desfase de 4 sorteos (101 y 105) entre 1 y 10 debe ser ignorado
    analysis = analyze_pair_lag(prior_history, window=5, max_lag=2)
    pairs_info = analysis["pairs_info"]

    # (1, 10) no debe registrarse con lag support
    if (1, 10) in pairs_info:
        assert pairs_info[(1, 10)]["recent_lag_count"] == 0


def test_pair_lag_empty_history():
    analysis = analyze_pair_lag([], window=10, max_lag=3)
    assert analysis == {
        "pairs_info": {},
        "recent_count": 0,
        "broad_count": 0,
    }

    score_res = score_pair_lag_support([1, 2, 3, 4, 5, 6], analysis)
    assert score_res["pair_lag_score"] == 0.0
    assert score_res["bridge_pairs"] == []
    assert len(score_res["pair_lag_notes"]) > 0


def test_pair_lag_determinism():
    prior_history = [
        {"draw": 101, "numbers": [1, 2, 3, 4, 5, 6]},
        {"draw": 102, "numbers": [10, 11, 12, 13, 14, 15]},
        {"draw": 103, "numbers": [1, 2, 20, 21, 22, 23]},
    ]

    res1 = analyze_pair_lag(prior_history, window=3, max_lag=2)
    res2 = analyze_pair_lag(prior_history, window=3, max_lag=2)
    assert res1 == res2

    score1 = score_pair_lag_support([1, 2, 10, 11, 12, 13], res1)
    score2 = score_pair_lag_support([1, 2, 10, 11, 12, 13], res2)
    assert score1 == score2


def test_pair_lag_thresholds_and_confidence():
    # Historial muy corto (solo 4 sorteos)
    prior_history = [
        {"draw": 1, "numbers": [1, 2, 3, 4, 5, 6]},
        {"draw": 2, "numbers": [1, 2, 10, 20, 30, 40]},
        {"draw": 3, "numbers": [1, 3, 11, 21, 31, 41]},
        {"draw": 4, "numbers": [1, 4, 12, 22, 32, 42]},
    ]

    # Analizar con ventana de 30 sorteos
    analysis = analyze_pair_lag(prior_history, window=30, max_lag=5)

    # 1. El score para un candidato no debe saturar en 1.0 con historial muy pequeño (debido al confidence factor)
    res_short = score_pair_lag_support([1, 2, 3, 4, 5, 6], analysis, min_exact_count=1, min_lag_count=2, min_total_support=2)
    # confidence = 4 / 30 = 0.1333, el score debe ser muy bajo y ciertamente menor que 0.5
    assert res_short["pair_lag_score"] < 0.5
    assert any("Soporte reducido" in note for note in res_short["pair_lag_notes"])

    # 2. bridge_pairs no debe incluir pares sin soporte suficiente
    # Un par con exact_count=1 y lag_count=0 tiene total_support=1 < min_total_support=2, por tanto no debe ser bridge_pair
    for bp in res_short["bridge_pairs"]:
        assert bp["exact_count"] + bp["lag_count"] >= 2

    # 3. Con historial amplio y soporte repetido, sí puede subir el score
    large_history = []
    # Generar 40 sorteos donde el par (1, 2) aparece en la mitad de ellos
    for d in range(1, 41):
        if d % 2 == 0:
            large_history.append({"draw": d, "numbers": [1, 2, 10, 20, 30, 40]})
        else:
            large_history.append({"draw": d, "numbers": [3, 4, 11, 21, 31, 41]})

    analysis_large = analyze_pair_lag(large_history, window=30, max_lag=5)
    res_large = score_pair_lag_support([1, 2, 10, 20, 30, 40], analysis_large, min_exact_count=1, min_lag_count=2, min_total_support=2)
    
    # Con historial amplio y soporte frecuente, el score puede subir significativamente (p. ej., > 0.7)
    assert res_large["pair_lag_score"] > 0.7

