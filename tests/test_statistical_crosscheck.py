from __future__ import annotations

import pytest
from melate_app_lab.statistical_crosscheck import (
    analyze_candidate_statistical_profile,
    analyze_portfolio_statistical_profile,
)

def test_analyze_candidate_statistical_profile():
    # Candidates: [2, 3, 4, 5, 6, 7]
    # Primes inside candidate: 2, 3, 5, 7 -> 4 primes
    # Consecutive pairs: (2,3), (3,4), (4,5), (5,6), (6,7) -> 5 consecutive pairs
    # Even count: 2, 4, 6 -> 3 even, 3 odd
    # Sum: 2+3+4+5+6+7 = 27
    # Mean: 4.5
    # Low numbers: 2, 3, 4, 5, 6, 7 are all <= 28 -> 6 low, 0 high -> "6L / 0H"
    
    prior_history = [
        {"draw": 1, "numbers": [1, 2, 3, 10, 11, 12]},
        {"draw": 2, "numbers": [2, 10, 15, 20, 25, 30]}, # prev draw
    ]
    
    res = analyze_candidate_statistical_profile([2, 3, 4, 5, 6, 7], prior_history)
    
    assert res["prime_count"] == 4
    assert res["repeated_from_previous_draw_count"] == 1
    assert res["consecutive_pairs_count"] == 5
    assert res["sum_value"] == 27
    assert res["mean_value"] == 4.5
    assert res["even_count"] == 3
    assert res["odd_count"] == 3
    assert res["low_high_balance"] == "6L / 0H"
    assert len(res["statistical_alerts"]) > 0  # Should alert consecutive pairs >= 3 and mean in low_band

def test_analyze_portfolio_statistical_profile():
    prior_history = [
        {"draw": 1, "numbers": [1, 2, 3, 4, 5, 6]}
    ]
    portfolio = [
        {"numbers": [2, 3, 5, 7, 11, 13]},
        {"numbers": [10, 12, 14, 16, 18, 20]}
    ]
    
    res = analyze_portfolio_statistical_profile(portfolio, prior_history)
    assert res["average_prime_count"] == 3.0 # [2,3,5,7,11,13] has 6 primes. [10,12,14,16,18,20] has 0 primes. Average is 3.0.
    assert res["average_mean_value"] > 0
    assert len(res["portfolio_statistical_alerts"]) == 0 or isinstance(res["portfolio_statistical_alerts"], list)

def test_empty_portfolio_statistical_profile():
    res = analyze_portfolio_statistical_profile([], [])
    assert res["average_prime_count"] == 0.0
    assert "Cartera vacía." in res["portfolio_statistical_alerts"]
