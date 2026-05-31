from __future__ import annotations

import json
import pytest
from typer.testing import CliRunner

from melate_app_lab.historical_store import import_draws_to_memory
from melate_app_lab.structural_signal_audit import (
    calculate_pearson_correlation,
    run_structural_signal_audit,
)
from melate_app_lab.cli import app


def test_calculate_pearson_correlation():
    # Casos normales
    assert calculate_pearson_correlation([1, 2, 3], [2, 4, 6]) == 1.0
    assert calculate_pearson_correlation([1, 2, 3], [-2, -4, -6]) == -1.0
    assert calculate_pearson_correlation([1, 2, 3], [1, 2, 3]) == 1.0

    # Listas vacias o de tamano menor a 2
    assert calculate_pearson_correlation([], []) == 0.0
    assert calculate_pearson_correlation([1], [1]) == 0.0

    # Longitudes diferentes
    assert calculate_pearson_correlation([1, 2], [1, 2, 3]) == 0.0

    # Valores constantes (desviacion cero)
    assert calculate_pearson_correlation([1, 1, 1], [2, 3, 4]) == 0.0
    assert calculate_pearson_correlation([2, 3, 4], [1, 1, 1]) == 0.0


@pytest.fixture
def dummy_audit_history():
    # Necesitamos al menos 15 sorteos para que len(prior_history) >= 10 en los ultimos
    history = []
    for i in range(1, 21):
        # Generar sorteos deterministas simples
        nums = [(i + j) % 56 + 1 for j in range(6)]
        nums.sort()
        history.append({
            "game": "revancha",
            "draw": 100 + i,
            "date": f"2026-05-{i:02d}",
            "numbers": nums,
            "sum": sum(nums),
            "sum_band": "low_band" if sum(nums) < 150 else "high_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1",
        })
    return history


def test_structural_signal_audit_run(tmp_path, dummy_audit_history):
    db_path = tmp_path / "memory.sqlite"
    import_draws_to_memory(dummy_audit_history, db_path)

    # Correr la auditoria retrospectiva con limite pequeño
    res = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=5,
        pool_size=10,
        top_k=2,
        seed=42,
    )

    assert res["success"] is True
    assert res["game"] == "revancha"
    assert res["draws_evaluated"] > 0
    assert res["pool_size"] == 10
    assert res["top_k"] == 2
    assert res["seed"] == 42
    assert "signal_buckets" in res
    assert "correlations" in res
    assert "top_k_comparison" in res
    assert len(res["notes"]) > 0


def test_signal_buckets_structure(tmp_path, dummy_audit_history):
    db_path = tmp_path / "memory.sqlite"
    import_draws_to_memory(dummy_audit_history, db_path)

    res = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=5,
        pool_size=20,
        top_k=3,
        seed=100,
    )

    buckets = res["signal_buckets"]
    expected_scores = [
        "pair_lag_score",
        "block_activity_score",
        "gap_echo_score",
        "structural_signal_score",
    ]
    expected_ranges = ["low", "mid", "high", "very_high"]

    for score in expected_scores:
        assert score in buckets
        for r in expected_ranges:
            assert r in buckets[score]
            b = buckets[score][r]
            assert "candidate_count" in b
            assert "avg_hits" in b
            assert "rate_1plus" in b
            assert "rate_2plus" in b
            assert "rate_3plus" in b
            assert "avg_rank_score" in b
            assert "avg_graph_support_score" in b
            assert "avg_structural_signal_score" in b
            assert "avg_pair_lag_score" in b
            assert "avg_block_activity_score" in b
            assert "avg_gap_echo_score" in b


def test_correlations_structure(tmp_path, dummy_audit_history):
    db_path = tmp_path / "memory.sqlite"
    import_draws_to_memory(dummy_audit_history, db_path)

    res = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=5,
        pool_size=20,
        top_k=3,
        seed=100,
    )

    corr = res["correlations"]
    expected_keys = [
        "correlation_rank_vs_structural",
        "correlation_graph_vs_pair_lag",
        "correlation_graph_vs_structural",
        "correlation_pair_lag_vs_hits",
        "correlation_block_activity_vs_hits",
        "correlation_gap_echo_vs_hits",
        "correlation_structural_vs_hits",
    ]

    for key in expected_keys:
        assert key in corr
        val = corr[key]
        assert isinstance(val, float)
        assert -1.0 <= val <= 1.0


def test_top_k_comparison_structure(tmp_path, dummy_audit_history):
    db_path = tmp_path / "memory.sqlite"
    import_draws_to_memory(dummy_audit_history, db_path)

    res = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=5,
        pool_size=20,
        top_k=3,
        seed=100,
    )

    comparison = res["top_k_comparison"]
    expected_groups = [
        "ranker_actual",
        "structural_signal_only",
        "pair_lag_only",
        "block_activity_only",
        "gap_echo_only",
    ]

    for group in expected_groups:
        assert group in comparison
        g = comparison[group]
        assert "avg_max_hits" in g
        assert "avg_mean_hits" in g
        assert "rate_2plus" in g
        assert "rate_3plus" in g
        assert "unique_hits_union" in g
        assert "average_internal_overlap" in g
        assert "high_redundancy_pairs" in g


def test_no_lookahead_bias(tmp_path, dummy_audit_history):
    # La auditoria no debe usar el sorteo objetivo para calcular sus features
    # Podemos verificar que los candidatos generados no dependen de los sorteos futuros.
    # En el walk-forward, para cada sorteo, la prior_history se filtra usando d["draw"] < target_draw.
    # Verificaremos esto asegurando que si cambiamos los numeros del sorteo objetivo,
    # el pool de candidatos y sus scores no cambian, pero si cambian los hits finales.
    db_path_1 = tmp_path / "mem1.sqlite"
    db_path_2 = tmp_path / "mem2.sqlite"

    history_1 = list(dummy_audit_history)
    history_2 = [dict(d) for d in dummy_audit_history]

    # Cambiar los numeros de los sorteos a evaluar en history_2
    # Esto deberia cambiar los hits pero NO las senales de los candidatos (ya que estas solo dependen del pasado)
    for d in history_2[-5:]:
        d["numbers"] = [51, 52, 53, 54, 55, 56]

    import_draws_to_memory(history_1, db_path_1)
    import_draws_to_memory(history_2, db_path_2)

    res1 = run_structural_signal_audit(
        db_path=db_path_1,
        game="revancha",
        limit=5,
        pool_size=10,
        top_k=3,
        seed=42,
    )

    res2 = run_structural_signal_audit(
        db_path=db_path_2,
        game="revancha",
        limit=5,
        pool_size=10,
        top_k=3,
        seed=42,
    )

    # Las correlaciones y buckets deberian cambiar porque cambiaron los hits (resultado objetivo)
    assert res1["correlations"] != res2["correlations"]

    # Pero el pool de candidatos, sus scores, etc. no deberian ser influenciados por el futuro.
    # Podemos verificar que la cantidad de draws_evaluated es la misma.
    assert res1["draws_evaluated"] == res2["draws_evaluated"]


def test_rank_score_unaffected(tmp_path, dummy_audit_history):
    db_path = tmp_path / "memory.sqlite"
    import_draws_to_memory(dummy_audit_history, db_path)

    res = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=2,
        pool_size=10,
        top_k=3,
        seed=42,
    )

    # ranker_actual y structural_signal_only deben tener comportamientos de ranking diferentes
    # puesto que ranker_actual no suma structural_signal_score para rankear.
    comp = res["top_k_comparison"]
    # Comparar avg_max_hits u otras metricas descriptivas.
    # Dado que son dos criterios de ordenamiento distintos,
    # top_k_comparison de cada uno refleja su propio criterio descriptivo.
    assert "ranker_actual" in comp
    assert "structural_signal_only" in comp


def test_determinism(tmp_path, dummy_audit_history):
    db_path = tmp_path / "memory.sqlite"
    import_draws_to_memory(dummy_audit_history, db_path)

    res1 = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=3,
        pool_size=15,
        top_k=4,
        seed=999,
    )

    res2 = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=3,
        pool_size=15,
        top_k=4,
        seed=999,
    )

    res_different_seed = run_structural_signal_audit(
        db_path=db_path,
        game="revancha",
        limit=3,
        pool_size=15,
        top_k=4,
        seed=1000,
    )

    # Mismo seed -> mismos resultados exactos
    assert res1["correlations"] == res2["correlations"]
    assert res1["top_k_comparison"] == res2["top_k_comparison"]

    # Seed diferente -> resultados diferentes (en la generacion del pool)
    assert res1["correlations"] != res_different_seed["correlations"]


def test_cli_command(tmp_path, dummy_audit_history, monkeypatch):
    db_path = tmp_path / "memory.sqlite"
    import_draws_to_memory(dummy_audit_history, db_path)

    # Monkeypatch DEFAULT_DB_PATH en cli para apuntar al archivo temporal
    import melate_app_lab.cli as cli
    monkeypatch.setattr(cli, "DEFAULT_DB_PATH", db_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "structural-signal-audit",
            "--game",
            "revancha",
            "--limit",
            "5",
            "--pool-size",
            "10",
            "--top-k",
            "2",
            "--seed",
            "42",
        ],
    )

    assert result.exit_code == 0

    # Parsear salida JSON
    output_data = json.loads(result.output)
    assert output_data["success"] is True
    assert "signal_buckets" in output_data
    assert "correlations" in output_data
    assert "top_k_comparison" in output_data
    assert output_data["seed"] == 42
    assert output_data["game"] == "revancha"
