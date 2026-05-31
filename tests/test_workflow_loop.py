import pytest
from pathlib import Path
from melate_app_lab.workflow_loop import evaluate_portfolio_coverage, run_unified_workflow
from melate_app_lab.historical_store import import_draws_to_memory, load_draw_history
from melate_app_lab.thesis_memory import load_thesis_candidates, load_thesis_portfolios

def test_evaluate_portfolio_coverage():
    candidates = [
        {"numbers": [1, 2, 3, 4, 5, 6], "block_signature": "6-0-0-0-0"},
        {"numbers": [1, 2, 3, 11, 12, 13], "block_signature": "3-3-0-0-0"},
        {"numbers": [41, 42, 43, 44, 45, 46], "block_signature": "0-0-0-0-6"}
    ]
    
    metrics = evaluate_portfolio_coverage(candidates)
    
    assert metrics["unique_numbers_covered"] == 15
    assert metrics["block_ranges_covered"] == 3
    assert metrics["unique_block_signatures"] == 3
    assert metrics["average_internal_overlap"] == 1.0


def test_evaluate_portfolio_coverage_empty():
    assert evaluate_portfolio_coverage([]) == {}


def test_run_unified_workflow_closes_connection(tmp_path):
    from unittest.mock import patch, MagicMock
    db_path = tmp_path / "data" / "memory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Let's import mock history to avoid empty history check
    history_records = [
        {"game": "revancha", "draw": 4210, "date": "2026-05-01", "numbers": [1, 2, 3, 4, 5, 6]}
    ]
    import_draws_to_memory(history_records, db_path=db_path)
    
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    
    with patch("melate_app_lab.workflow_loop._connect", return_value=mock_conn) as mock_connect:
        run_unified_workflow(
            db_path=db_path,
            draw=4211,
            game="revancha",
            pool_size=10,
            seed=123,
            result_numbers=[1, 2, 3, 4, 5, 6]
        )
        
        mock_connect.assert_called()
        mock_conn.close.assert_called()



def test_run_unified_workflow(tmp_path):
    # Setup test DB path in a valid 'data' folder to satisfy thesis_memory checks
    db_path = tmp_path / "data" / "memory.sqlite"
    
    # Import a minimal history
    history_records = [
        {
            "game": "revancha",
            "draw": 4210,
            "date": "2026-05-01",
            "numbers": [1, 2, 3, 4, 5, 6]
        },
        {
            "game": "revancha",
            "draw": 4211,
            "date": "2026-05-02",
            "numbers": [11, 12, 13, 14, 15, 16]
        },
        {
            "game": "revancha",
            "draw": 4212,
            "date": "2026-05-03",
            "numbers": [21, 22, 23, 24, 25, 26]
        }
    ]
    
    # Create the DB and import history
    db_path.parent.mkdir(parents=True, exist_ok=True)
    import_draws_to_memory(history_records, db_path=db_path)
    
    # Let's run unified workflow for draw 4213, with played indices [0, 2] and no result yet
    res = run_unified_workflow(
        db_path=db_path,
        draw=4213,
        game="revancha",
        pool_size=10,
        seed=123,
        played_indices=[0, 2]
    )
    
    assert res["portfolio_id"] > 0
    assert "coverage" in res
    assert res["played_count"] == 2
    assert res["evaluation"] == {}
    
    # Check that portfolio candidates are stored in database
    candidates = load_thesis_candidates(db_path, res["portfolio_id"])
    assert len(candidates) == 10
    
    # Candidate at index 0 and 2 should be in state 'Jugado'
    # Wait, the load_thesis_candidates function orders them by graph_support_score desc, id asc
    # So their indices might be different in the database list from candidates_payload.
    # Let's verify we have exactly 2 candidates in 'Jugado' state.
    played_cands = [c for c in candidates if c["state"] == "Jugado"]
    assert len(played_cands) == 2
    
    # Check classification and rank_score presence
    for cand in candidates:
        assert cand["classification"] in ("relation", "balance", "contrast")
        assert cand["rank_score"] is not None
        assert isinstance(cand["rank_score"], float)

    # Now, run again providing result_numbers to check evaluation and historical store integration
    result_numbers = [1, 2, 11, 21, 41, 51]
    res_eval = run_unified_workflow(
        db_path=db_path,
        draw=4213,
        game="revancha",
        pool_size=10,
        seed=123,
        played_indices=[0, 2],
        result_numbers=result_numbers
    )
    
    assert res_eval["evaluation"]["result_captured"] is True
    assert res_eval["evaluation"]["result_numbers"] == result_numbers
    
    # Load official result from historical_store
    hist = load_draw_history(db_path, game="revancha")
    latest_hist = [d for d in hist if d["draw"] == 4213]
    assert len(latest_hist) == 1
    assert latest_hist[0]["numbers"] == result_numbers
    assert latest_hist[0]["sum"] == sum(result_numbers)
    assert latest_hist[0]["sum_band"] is not None
    assert latest_hist[0]["block_signature"] is not None
    
    # Verify candidate states are 'Revisado'
    reviewed_candidates = load_thesis_candidates(db_path, res_eval["portfolio_id"])
    for cand in reviewed_candidates:
        assert cand["state"] == "Revisado"
        assert cand["result_numbers"] == result_numbers
        assert cand["hits_count"] == len(set(cand["numbers"]) & set(result_numbers))
        
    # Check union hits of played candidates
    # The played candidates in the second run are those at index 0 and 2 of reviewed_candidates
    played_candidates_in_db = [reviewed_candidates[0], reviewed_candidates[2]]
    union_hits = set()
    for pc in played_candidates_in_db:
        union_hits.update(set(pc["numbers"]) & set(result_numbers))
        
    assert res_eval["evaluation"]["portfolio_unique_hits_captured"] == len(union_hits)
    assert sorted(res_eval["evaluation"]["hit_numbers"]) == sorted(list(union_hits))


def test_run_unified_workflow_with_structural_diversification(tmp_path):
    db_path = tmp_path / "data" / "memory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Import minimal history
    history_records = [
        {"game": "revancha", "draw": 4210, "date": "2026-05-01", "numbers": [1, 2, 3, 4, 5, 6]},
        {"game": "revancha", "draw": 4211, "date": "2026-05-02", "numbers": [11, 12, 13, 14, 15, 16]},
        {"game": "revancha", "draw": 4212, "date": "2026-05-03", "numbers": [21, 22, 23, 24, 25, 26]}
    ]
    import_draws_to_memory(history_records, db_path=db_path)

    # Run workflow loop with diversification
    res = run_unified_workflow(
        db_path=db_path,
        draw=4213,
        game="revancha",
        pool_size=15,
        seed=42,
        use_structural_diversification=True,
        structural_diversity_weight=1.2,
    )

    assert res["portfolio_id"] > 0
    candidates = load_thesis_candidates(db_path, res["portfolio_id"])
    assert len(candidates) == 10

    # Verify notes field format contains structural JSON payload
    import json
    for cand in candidates:
        notes_dict = json.loads(cand["notes"])
        assert "structural_signal_score" in notes_dict
        assert "selection_reason" in notes_dict
        assert "gap_family" in notes_dict
        assert "structural_notes" in notes_dict
        assert isinstance(notes_dict["structural_signal_score"], float)
        assert isinstance(notes_dict["selection_reason"], str)


def test_run_unified_workflow_identical_when_flag_off(tmp_path):
    db_path = tmp_path / "data" / "memory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    history_records = [
        {"game": "revancha", "draw": 4210, "date": "2026-05-01", "numbers": [1, 2, 3, 4, 5, 6]},
        {"game": "revancha", "draw": 4211, "date": "2026-05-02", "numbers": [11, 12, 13, 14, 15, 16]},
        {"game": "revancha", "draw": 4212, "date": "2026-05-03", "numbers": [21, 22, 23, 24, 25, 26]}
    ]
    import_draws_to_memory(history_records, db_path=db_path)

    # Flag explicitly off
    res_off = run_unified_workflow(
        db_path=db_path,
        draw=4213,
        game="revancha",
        pool_size=15,
        seed=100,
        use_structural_diversification=False,
    )

    # Flag off by default
    res_default = run_unified_workflow(
        db_path=db_path,
        draw=4213,
        game="revancha",
        pool_size=15,
        seed=100,
    )

    cands_off = load_thesis_candidates(db_path, res_off["portfolio_id"])
    cands_default = load_thesis_candidates(db_path, res_default["portfolio_id"])

    assert len(cands_off) == len(cands_default)
    for c_off, c_def in zip(cands_off, cands_default):
        assert c_off["numbers"] == c_def["numbers"]
        assert c_off["rank_score"] == pytest.approx(c_def["rank_score"])

