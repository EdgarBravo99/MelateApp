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
            "draw": 4200,
            "numbers": [1, 10, 20, 30, 40, 50],
            "sum": 151,
            "sum_band": "mid_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "draw": 4201,
            "numbers": [2, 12, 22, 32, 42, 52],
            "sum": 162,
            "sum_band": "high_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
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
        assert cand["classification"] in ["Balance por bloques", "Relacion historica moderada", "Cadencia y Ciclos"]
        assert len(cand["reason_bullets"]) > 0

def test_format_candidates_report_structure(sample_history):
    analysis = analyze_time_window(sample_history, window=3)
    candidates = generate_candidates(analysis, count=2, seed=4218)
    report = format_candidates_report(candidates)
    assert "Tesis de revisión para siguiente ciclo" in report
    assert "Set A —" in report

def test_run_generate_candidates_controller_throws_on_empty_db(tmp_path):
    db_file = tmp_path / "test_empty_mem.sqlite"
    # should raise ValueError since history table is empty
    with pytest.raises(ValueError, match="No hay historial"):
        run_generate_candidates(db_path=db_file, count=5)
