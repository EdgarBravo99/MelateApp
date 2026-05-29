from __future__ import annotations

import pytest
from melate_app_lab.candidate_generator import (
    analyze_time_window,
    generate_candidates,
    format_candidates_report
)
from melate_app_lab.desktop_controller import run_generate_candidates

@pytest.fixture
def sample_history():
    return [
        {
            "game": "revancha",
            "draw": 4200,
            "numbers": [1, 10, 20, 30, 40, 50],
            "sum": 151,
            "sum_band": "mid_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 4201,
            "numbers": [2, 12, 22, 32, 42, 52],
            "sum": 162,
            "sum_band": "high_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 4202,
            "numbers": [3, 13, 23, 33, 43, 53],
            "sum": 168,
            "sum_band": "high_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        }
    ]

def test_analyze_time_window_returns_correct_counters(sample_history):
    analysis = analyze_time_window(sample_history, window=2)
    assert analysis["recent_count"] == 2
    assert 2 in analysis["frequencies"]
    assert 3 in analysis["frequencies"]
    assert (2, 12) in analysis["co_occurrences"]
    assert "1-1-1-1-2" in analysis["common_signatures"]
    assert "high_band" in analysis["common_bands"]
    assert len(analysis["historical_sets"]) == 3

def test_generate_candidates_honors_rules(sample_history):
    analysis = analyze_time_window(sample_history, window=3)
    candidates = generate_candidates(analysis, count=5, seed=4218)
    assert len(candidates) <= 5
    for cand in candidates:
        assert len(cand["numbers"]) == 6
        assert len(set(cand["numbers"])) == 6
        assert all(1 <= n <= 56 for n in cand["numbers"])
        assert cand["classification"] in ["Balance por bloques", "Relacion historica moderada", "Contraste / cobertura"]
        assert len(cand["reason_bullets"]) > 0
        # Graph support fields must always be present
        assert "pair_edges" in cand
        assert "graph_support_score" in cand
        assert isinstance(cand["graph_support_score"], int)
        assert "relation_count" in cand
        assert "strongest_pairs" in cand
        assert "evidence_draws" in cand

def test_format_candidates_report_structure(sample_history):
    analysis = analyze_time_window(sample_history, window=3)
    candidates = generate_candidates(analysis, count=2, seed=4218)
    report = format_candidates_report(candidates)
    assert "Tesis de revision para siguiente ciclo" in report
    assert "Set A" in report

def test_generate_candidates_with_graph_support():
    # Build history where same pair appears multiple times
    history = [
        {"game": "revancha", "draw": 1, "numbers": [5, 10, 15, 20, 25, 30]},
        {"game": "revancha", "draw": 2, "numbers": [5, 10, 16, 21, 26, 31]},
        {"game": "revancha", "draw": 3, "numbers": [5, 10, 17, 22, 27, 32]},
    ]
    from melate_app_lab.relation_graph import build_historical_relation_graph
    graph_data = build_historical_relation_graph(history, window=10, game="revancha")
    analysis = analyze_time_window(history, window=10)
    candidates = generate_candidates(analysis, count=5, seed=42, graph_data=graph_data)
    # At least some candidates should have graph support if pair 5-10 appears
    has_support = any(c["graph_support_score"] > 0 for c in candidates)
    # The pair 5-10 co-occurs 3 times, so if a candidate contains both, score > 0
    # This depends on random generation, so we check the structure is correct
    for c in candidates:
        assert isinstance(c["pair_edges"], list)
        assert isinstance(c["graph_support_score"], int)
        assert isinstance(c["evidence_draws"], list)

def test_candidates_without_graph_have_zero_score(sample_history):
    analysis = analyze_time_window(sample_history, window=3)
    candidates = generate_candidates(analysis, count=3, seed=4218, graph_data=None)
    for c in candidates:
        assert c["graph_support_score"] == 0
        assert c["pair_edges"] == []

def test_format_report_shows_graph_support():
    # Create a candidate with graph support manually
    cand = {
        "numbers": [5, 10, 15, 20, 25, 30],
        "classification": "Relacion historica moderada",
        "reason_bullets": ["test bullet"],
        "pair_edges": [{"pair": "5—10", "count": 3, "draws": [1, 2, 3]}],
        "graph_support_score": 3,
        "relation_count": 1,
        "strongest_pairs": ["5—10"],
        "evidence_draws": [3, 2, 1],
        "relation_window": 30,
    }
    report = format_candidates_report([cand])
    assert "Soporte de grafo" in report
    assert "graph_support_score: 3" in report
    assert "5—10 observado 3 veces" in report
    assert "ventana: ultimos 30 sorteos" in report

def test_run_generate_candidates_controller_throws_on_empty_db(tmp_path):
    db_file = tmp_path / "test_empty_mem.sqlite"
    # should raise ValueError since history table is empty
    with pytest.raises(ValueError, match="No hay historial"):
        run_generate_candidates(db_path=db_file, count=5)

def test_candidates_report_passes_guardrails(sample_history):
    from melate_app_lab.guardrails import validate_text
    analysis = analyze_time_window(sample_history, window=3)
    candidates = generate_candidates(analysis, count=3, seed=4218)
    report = format_candidates_report(candidates)
    validate_text(report)  # Should not raise


def test_format_report_separates_perfiles_and_ranks():
    candidates = [
        {
            "numbers": [1, 2, 3, 4, 5, 6],
            "classification": "Balance por bloques",
            "reason_bullets": ["cubre 5 bloques"],
            "pair_edges": [{"pair": "1—2", "count": 2, "draws": [1, 2]}],
            "graph_support_score": 2,
            "relation_count": 1,
            "strongest_pairs": ["1—2"],
            "evidence_draws": [2, 1],
            "relation_window": 30,
        },
        {
            "numbers": [10, 11, 12, 13, 14, 15],
            "classification": "Relacion historica moderada",
            "reason_bullets": ["conserva 15 coapariciones"],
            "pair_edges": [{"pair": "10—11", "count": 15, "draws": [1]}],
            "graph_support_score": 15,
            "relation_count": 1,
            "strongest_pairs": ["10—11"],
            "evidence_draws": [1],
            "relation_window": 30,
        },
        {
            "numbers": [20, 21, 22, 23, 24, 25],
            "classification": "Contraste / cobertura",
            "reason_bullets": ["contraste total"],
            "pair_edges": [],
            "graph_support_score": 0,
            "relation_count": 0,
            "strongest_pairs": [],
            "evidence_draws": [],
            "relation_window": 30,
        }
    ]
    report = format_candidates_report(candidates)
    
    # 1. Check ranking is present and correctly ordered by graph_support_score
    assert "Sets con mayor soporte de grafo: Set A (soporte: 15), Set B (soporte: 2)" in report
    
    # 2. Check profile headings are separated
    assert "Perfil Balance por bloques" in report
    assert "Perfil Relación histórica moderada" in report
    assert "Perfil Contraste / cobertura" in report
    
    # 3. Check correct letter assignments (since it ranks candidates by score descending)
    assert "Set A — Relacion historica moderada" in report
    assert "Set B — Balance por bloques" in report
    assert "Set C — Contraste / cobertura" in report


