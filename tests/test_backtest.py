from __future__ import annotations

import pytest
from melate_app_lab.candidate_generator import analyze_time_window
from melate_app_lab.feature_extractor import extract_features
from melate_app_lab.candidate_search import search_candidates
from melate_app_lab.candidate_ranker import score_candidate, rank_candidates
from melate_app_lab.backtest_lab import run_backtest
from melate_app_lab.desktop_controller import run_backtest_lab


@pytest.fixture
def sample_history():
    return [
        {
            "game": "revancha",
            "draw": 100,
            "date": "2026-05-01",
            "numbers": [1, 2, 3, 4, 5, 6],
            "sum": 21,
            "sum_band": "low_band",
            "block_signature": "6-0-0-0-0",
            "block_presence_signature": "1-0-0-0-0"
        },
        {
            "game": "revancha",
            "draw": 101,
            "date": "2026-05-02",
            "numbers": [1, 2, 3, 4, 5, 7],
            "sum": 22,
            "sum_band": "low_band",
            "block_signature": "6-0-0-0-0",
            "block_presence_signature": "1-0-0-0-0"
        },
        {
            "game": "revancha",
            "draw": 102,
            "date": "2026-05-03",
            "numbers": [10, 20, 30, 40, 50, 55],
            "sum": 205,
            "sum_band": "high_tail",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 103,
            "date": "2026-05-04",
            "numbers": [5, 10, 15, 20, 25, 30],
            "sum": 105,
            "sum_band": "low_band",
            "block_signature": "2-2-2-0-0",
            "block_presence_signature": "1-1-1-0-0"
        },
        {
            "game": "revancha",
            "draw": 104,
            "date": "2026-05-05",
            "numbers": [5, 10, 15, 20, 25, 31],
            "sum": 106,
            "sum_band": "low_band",
            "block_signature": "2-2-1-1-0",
            "block_presence_signature": "1-1-1-1-0"
        },
        {
            "game": "revancha",
            "draw": 105,
            "date": "2026-05-06",
            "numbers": [2, 12, 22, 32, 42, 52],
            "sum": 162,
            "sum_band": "high_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 106,
            "date": "2026-05-07",
            "numbers": [3, 13, 23, 33, 43, 53],
            "sum": 168,
            "sum_band": "high_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 107,
            "date": "2026-05-08",
            "numbers": [4, 14, 24, 34, 44, 54],
            "sum": 174,
            "sum_band": "high_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 108,
            "date": "2026-05-09",
            "numbers": [6, 16, 26, 36, 46, 56],
            "sum": 186,
            "sum_band": "high_tail",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 109,
            "date": "2026-05-10",
            "numbers": [8, 18, 28, 38, 48, 51],
            "sum": 191,
            "sum_band": "high_tail",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 110,
            "date": "2026-05-11",
            "numbers": [9, 19, 29, 39, 49, 52],
            "sum": 197,
            "sum_band": "high_tail",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
        {
            "game": "revancha",
            "draw": 111,
            "date": "2026-05-12",
            "numbers": [1, 11, 21, 31, 41, 53],
            "sum": 158,
            "sum_band": "mid_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1"
        },
    ]


def test_feature_extractor(sample_history):
    training_history = sample_history[:5]
    full_history = sample_history
    numbers = [5, 10, 15, 20, 25, 30]

    feats = extract_features(numbers, training_history, full_history, graph_data=None)

    assert feats["numbers"] == numbers
    assert feats["sum"] == 105
    assert feats["sum_band"] == "low_band"
    assert feats["block_signature"] == "2-2-2-0-0"
    assert feats["block_presence_signature"] == "1-1-1-0-0"
    assert feats["even_count"] == 3
    assert feats["odd_count"] == 3
    assert feats["frequency_mean"] > 0
    assert feats["diversity_score"] == 3
    assert feats["historical_exact_match"] is True


def test_candidate_search(sample_history):
    analysis = analyze_time_window(sample_history, window=5)
    pool = search_candidates(analysis, pool_size=10, seed=42)

    assert len(pool) <= 10
    for cand in pool:
        assert len(cand) == 6
        assert len(set(cand)) == 6
        assert all(1 <= n <= 56 for n in cand)


def test_candidate_ranker(sample_history):
    training_history = sample_history[:5]
    full_history = sample_history
    cand_1 = [5, 10, 15, 20, 25, 30]
    cand_2 = [1, 2, 3, 4, 5, 6]

    feats_1 = extract_features(cand_1, training_history, full_history)
    feats_2 = extract_features(cand_2, training_history, full_history)

    common_sigs = ["2-2-2-0-0", "1-1-1-1-2"]
    common_bands = ["low_band"]

    score_1 = score_candidate(feats_1, common_sigs, common_bands)
    score_2 = score_candidate(feats_2, common_sigs, common_bands)

    assert isinstance(score_1, float)
    assert isinstance(score_2, float)

    ranked = rank_candidates([feats_1, feats_2], common_sigs, common_bands)
    assert len(ranked) == 2
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2


def test_run_backtest(sample_history):
    # Evaluate draw 111 using preceding history
    results = run_backtest(
        history=sample_history,
        target_draws=[111],
        window=5,
        pool_size=10,
        top_k=2,
        seed=123,
        game="revancha"
    )

    assert results["draws_evaluated"] == 1
    assert "metrics" in results
    assert "results" in results
    assert len(results["results"]) == 1
    assert results["results"][0]["draw"] == 111


def test_run_backtest_lab_controller(tmp_path, sample_history):
    db_file = tmp_path / "data" / "test_backtest_mem.sqlite"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Setup SQLite memory and load history
    from melate_app_lab.historical_store import import_draws_to_memory
    import_draws_to_memory(sample_history, db_path=db_file)

    # Execute backtest lab run
    res = run_backtest_lab(
        db_path=db_file,
        limit=2,
        game="revancha",
        pool_size=10,
        top_k=2,
        seed=42,
        use_ml=False
    )

    assert res["draws_evaluated"] == 2
    assert "metrics" in res
    assert "html_path" in res
    assert "results" in res
