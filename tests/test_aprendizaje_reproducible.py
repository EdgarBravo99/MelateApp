from __future__ import annotations

import json
import pytest
import sqlite3
from pathlib import Path

from melate_app_lab.metrics import (
    calculate_hits,
    rate_2plus,
    rate_3plus,
    avg_mean_hits,
    unique_hits_union,
    average_internal_overlap,
    high_redundancy_pairs,
)
from melate_app_lab.experiment_registry import build_manifest
from melate_app_lab.portfolio_evaluator import evaluate_existing_portfolio
from melate_app_lab.portfolio_optimizer import optimize_portfolio, compute_portfolio_diversity_score
from melate_app_lab.feedback_learner import learn_from_reviewed_portfolios, build_reviewed_dataset
from melate_app_lab.thesis_memory import (
    save_thesis_portfolio,
    load_thesis_candidates,
    save_experiment_run,
    load_experiment_runs,
    get_active_feedback_profile,
)
from melate_app_lab.feature_extractor import extract_features_batch
from melate_app_lab.ml_ranker import is_ml_available, train_ml_ranker, rank_candidates_ml


def test_metrics():
    # calculate_hits
    assert calculate_hits([1, 2, 3, 4, 5, 6], [1, 2, 7, 8, 9, 10]) == 2
    
    # rates and means
    hits = [0, 1, 2, 3, 4]
    assert rate_2plus(hits) == 0.6
    assert rate_3plus(hits) == 0.4
    assert avg_mean_hits(hits) == 2.0
    
    # unique hits in union
    candidates = [[1, 2, 3, 4, 5, 6], [5, 6, 7, 8, 9, 10]]
    result = [1, 2, 9, 11]
    assert unique_hits_union(candidates, result) == 3
    
    # overlap and redundancy
    assert average_internal_overlap(candidates) == 2.0
    assert high_redundancy_pairs(candidates, threshold=2) == 1
    assert high_redundancy_pairs(candidates, threshold=3) == 0


def test_experiment_registry():
    manifest = build_manifest(
        game="revancha",
        window=30,
        limit=10,
        pool_size=100,
        top_k=5,
        seed=123,
        model_name="ridge",
        use_optimizer=True,
        use_feedback_profile=False,
    )
    assert manifest["game"] == "revancha"
    assert manifest["window"] == 30
    assert manifest["limit"] == 10
    assert manifest["pool_size"] == 100
    assert manifest["top_k"] == 5
    assert manifest["seed"] == 123
    assert manifest["model_name"] == "ridge"
    assert manifest["use_optimizer"] is True
    assert manifest["use_feedback_profile"] is False
    assert "commit_sha" in manifest
    assert "branch" in manifest
    assert "python_version" in manifest


def test_portfolio_evaluator_strict(tmp_path):
    db_path = tmp_path / "data" / "test_memory.db"
    
    # Pre-init tables and save a portfolio
    candidates = [
        {
            "numbers": [1, 2, 3, 4, 5, 6],
            "classification": "relation",
            "state": "Pendiente",
            "sum": 21,
            "sum_band": "1-100",
            "block_signature": "1-1-1-1-2",
            "graph_support_score": 12,
        },
        {
            "numbers": [7, 8, 9, 10, 11, 12],
            "classification": "balance",
            "state": "Pendiente",
            "sum": 57,
            "sum_band": "1-100",
            "block_signature": "1-1-1-1-2",
            "graph_support_score": 2,
        }
    ]
    portfolio_id = save_thesis_portfolio(db_path, draw=101, game="revancha", candidates=candidates)
    
    # Evaluate portfolio
    result = [1, 2, 7, 8, 13, 14]
    eval_res = evaluate_existing_portfolio(db_path, portfolio_id, result_numbers=result, game="revancha")
    
    assert eval_res["portfolio_id"] == portfolio_id
    assert eval_res["draw"] == 101
    assert eval_res["result_numbers"] == result
    assert eval_res["metrics"]["rate_2plus"] == 1.0 # both candidates had 2 hits
    
    # Confirm DB values were updated and marked as 'Revisado'
    updated_cands = load_thesis_candidates(db_path, portfolio_id)
    assert len(updated_cands) == 2
    assert all(c["state"] == "Revisado" for c in updated_cands)
    assert all(c["result_numbers"] == result for c in updated_cands)
    assert updated_cands[0]["hits_count"] == 2
    assert updated_cands[1]["hits_count"] == 2


def test_portfolio_optimizer():
    # Diverse list of candidates
    candidates = [
        {"numbers": [1, 2, 3, 4, 5, 6], "rank_score": 10.0},
        {"numbers": [1, 2, 3, 4, 7, 8], "rank_score": 9.5},  # shares 4 numbers with first -> should be penalized
        {"numbers": [11, 12, 13, 14, 15, 16], "rank_score": 8.0},  # completely disjoint
    ]
    
    # Naive slice would take the first two (which are highly redundant)
    # Optimizer should select the first and third candidates due to overlap penalty
    optimized = optimize_portfolio(candidates, top_k=2)
    assert len(optimized) == 2
    assert optimized[0]["numbers"] == [1, 2, 3, 4, 5, 6]
    assert optimized[1]["numbers"] == [11, 12, 13, 14, 15, 16]
    
    # Diversity score
    assert compute_portfolio_diversity_score(optimized) == 12.0


def test_feedback_learner_and_manifest_storage(tmp_path):
    db_path = tmp_path / "data" / "test_memory.db"
    
    # Save experiment run manifest to DB
    run_id = save_experiment_run(
        db_path,
        game="revancha",
        commit_sha="abcdef",
        branch="main",
        config={"window": 30},
        metrics={"rate_3plus": 0.5},
        report_paths=["report.html"],
    )
    assert run_id > 0
    runs = load_experiment_runs(db_path)
    assert len(runs) == 1
    assert runs[0]["commit_sha"] == "abcdef"
    assert runs[0]["metrics"]["rate_3plus"] == 0.5

    # Trigger learn-feedback on empty reviewed portfolios
    res = learn_from_reviewed_portfolios(db_path, game="revancha")
    assert res["success"] is False
    assert res["min_reviewed"] == 0


def test_extract_features_batch():
    candidates = [[1, 2, 3, 4, 5, 6], [10, 11, 12, 13, 14, 15]]
    training_history = [
        {"draw": 1, "numbers": [1, 2, 10, 11, 20, 21]}
    ]
    full_history = [
        {"draw": 1, "numbers": [1, 2, 10, 11, 20, 21]}
    ]
    graph_data = {
        "mode": "historical",
        "nodes": [{"number": 1, "degree": 5}, {"number": 10, "degree": 3}],
        "edges": [{"source": 1, "target": 2, "count": 2, "draws": [1]}]
    }
    
    batch_results = extract_features_batch(
        candidates,
        training_history=training_history,
        full_history=full_history,
        graph_data=graph_data,
    )
    
    assert len(batch_results) == 2
    assert batch_results[0]["sum"] == 21
    assert batch_results[0]["frequency_mean"] == 2/6 # 1 and 2 appeared in draw 1
    assert batch_results[0]["graph_support_score"] == 2 # edge (1,2) count is 2


def test_ml_ranker_zoo():
    # If ML is not available, train_ml_ranker should return None, and rank_candidates_ml should fall back
    history = [{"game": "revancha", "draw": 1, "numbers": [1, 2, 3, 4, 5, 6]}]
    model = train_ml_ranker(history, training_draws=[1], window=30, game="revancha", model_type="ridge")
    
    candidates_features = [{"numbers": [1, 2, 3, 4, 5, 6], "sum": 21, "graph_support_score": 5}]
    ranked = rank_candidates_ml(model, candidates_features, [], [])
    assert len(ranked) == 1
    assert "rank_score" in ranked[0]
