import pytest

from melate_app_lab.number_utils import (
    block_presence_signature,
    block_signature,
    parse_numbers,
    sum_band,
    validate_numbers,
)


def test_parse_numbers_from_string():
    assert parse_numbers("2 18 22 38 51 52") == [2, 18, 22, 38, 51, 52]


def test_validate_numbers_rejects_duplicates():
    with pytest.raises(ValueError):
        validate_numbers([2, 18, 18, 38, 51, 52])


def test_validate_numbers_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_numbers([0, 18, 22, 38, 51, 52])


def test_validate_numbers_requires_six_numbers():
    with pytest.raises(ValueError):
        validate_numbers([2, 18, 22, 38, 51])


def test_fixture_sum_band_and_signatures():
    numbers = [2, 18, 22, 38, 51, 52]
    assert sum(numbers) == 183
    assert sum_band(sum(numbers)) == "high_tail"
    assert block_signature(numbers) == "1-1-1-1-2"
    assert block_presence_signature(numbers) == "1-1-1-1-1"


def test_analyze_portfolio_redundancy():
    from melate_app_lab.number_utils import analyze_portfolio_redundancy

    # 1. Normal case - diverse candidates
    candidates = [
        {"numbers": [1, 11, 21, 31, 41, 42], "classification": "Balance por bloques", "letter": "A"},
        {"numbers": [2, 12, 22, 32, 33, 34], "classification": "Relacion historica moderada", "letter": "B"},
        {"numbers": [3, 13, 23, 24, 25, 26], "classification": "Contraste / cobertura", "letter": "C"},
    ]
    res = analyze_portfolio_redundancy(candidates)
    assert not res["has_alerts"]
    assert len(res["redundancies"]) == 0
    assert len(res["number_concentration"]) == 0
    assert len(res["signature_concentration"]) == 0
    assert len(res["profile_concentration"]) == 0
    assert len(res["block_concentration"]) == 0

    # 2. Triggering Rule 1: Set intersection level 3 and 4
    candidates_redundant = [
        {"numbers": [1, 2, 3, 4, 5, 6], "classification": "Balance por bloques", "letter": "A"},
        {"numbers": [1, 2, 3, 10, 11, 12], "classification": "Balance por bloques", "letter": "B"},
        {"numbers": [1, 2, 3, 4, 20, 21], "classification": "Relacion historica moderada", "letter": "C"},
    ]
    res_red = analyze_portfolio_redundancy(candidates_redundant)
    assert res_red["has_alerts"]
    assert len(res_red["redundancies"]) == 3
    levels = {r["level"] for r in res_red["redundancies"]}
    assert "media" in levels
    assert "alta" in levels

    # 3. Triggering Rule 2: Concentration per number (>40%)
    manual_sets = [
        [1, 2, 3, 4, 5, 16],
        [6, 7, 8, 9, 10, 16],
        [11, 12, 13, 14, 15, 16],
        [18, 19, 20, 21, 22, 16],
        [23, 24, 25, 26, 27, 16],
        [28, 29, 30, 31, 32, 33],
        [34, 35, 36, 37, 38, 39],
        [40, 41, 42, 43, 44, 45],
        [46, 47, 48, 49, 50, 51],
        [52, 53, 54, 55, 56, 17],
    ]
    candidates_num_conc = []
    for i, nums in enumerate(manual_sets):
        candidates_num_conc.append({
            "numbers": sorted(nums),
            "classification": "Balance por bloques" if i < 5 else "Contraste / cobertura",
            "letter": chr(ord('A') + i)
        })

    res_num = analyze_portfolio_redundancy(candidates_num_conc)
    assert res_num["has_alerts"]
    assert len(res_num["number_concentration"]) == 1
    assert res_num["number_concentration"][0]["number"] == 16
    assert res_num["number_concentration"][0]["percentage"] == 50.0

    # 4. Triggering Rule 3: Concentration per signature (>60%)
    # Let's create a scenario for signature concentration (>60%)
    candidates_sig_conc = []
    # Give 7 out of 10 candidates the same numbers [1, 2, 3, 4, 5, 6] (which has signature '6-0-0-0-0')
    # but ensure they don't trigger number concentration of >40% by changing their numbers slightly
    # or just use different numbers with same block signature '6-0-0-0-0' (all numbers in block 1-10)
    # block 1-10 numbers: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    # Cand 0: [1,2,3,4,5,6] -> 6-0-0-0-0
    # Cand 1: [1,2,3,4,5,7] -> 6-0-0-0-0
    # Cand 2: [1,2,3,4,5,8] -> 6-0-0-0-0
    # etc... wait, that would trigger number concentration for 1,2,3,4,5!
    # Instead, we can just use 10 sets of 6-0-0-0-0 where we don't care if number concentration triggers,
    # or we can test rule 3 with its own candidates where we only assert signature_concentration.
    for i in range(10):
        # We want signature '6-0-0-0-0' (all numbers in block 1-10) for 7 sets
        if i < 7:
            # Generate different subsets of 1-10
            # Since size is 6 and we only have 10 numbers, we might have some overlaps, but that's fine.
            # We just want to test if signature_concentration triggers.
            nums = [1, 2, 3, 4, 5, 6] if i == 0 else [1, 2, 3, 4, 5, 7]
            if i == 2: nums = [1, 2, 3, 4, 5, 8]
            if i == 3: nums = [1, 2, 3, 4, 5, 9]
            if i == 4: nums = [1, 2, 3, 4, 5, 10]
            if i == 5: nums = [1, 2, 3, 4, 6, 7]
            if i == 6: nums = [1, 2, 3, 5, 6, 8]
        else:
            # signature: 0-6-0-0-0 (numbers in 11-20)
            nums = [11, 12, 13, 14, 15, 16]
        candidates_sig_conc.append({
            "numbers": nums,
            "classification": "Balance por bloques",
            "letter": chr(ord('A') + i)
        })
    res_sig = analyze_portfolio_redundancy(candidates_sig_conc)
    assert res_sig["has_alerts"]
    assert len(res_sig["signature_concentration"]) == 1
    assert res_sig["signature_concentration"][0]["signature"] == "6-0-0-0-0"


    # 5. Triggering Rule 4: Concentration per profile (>60%)
    candidates_prof_conc = []
    for i in range(10):
        candidates_prof_conc.append({
            "numbers": [1, 2, 3, 4, 5, 6 + i],
            "classification": "Balance por bloques" if i < 7 else "Contraste / cobertura",
            "letter": chr(ord('A') + i)
        })
    res_prof = analyze_portfolio_redundancy(candidates_prof_conc)
    assert res_prof["has_alerts"]
    assert len(res_prof["profile_concentration"]) == 1
    assert res_prof["profile_concentration"][0]["profile"] == "Balance por bloques"

    # 6. Triggering Rule 5: Concentration per block (>35%)
    candidates_block_conc = [
        {"numbers": [1, 2, 3, 4, 5, 11], "classification": "A", "letter": "A"},
        {"numbers": [1, 2, 3, 4, 6, 12], "classification": "A", "letter": "B"},
        {"numbers": [1, 2, 3, 4, 7, 13], "classification": "A", "letter": "C"},
        {"numbers": [1, 2, 3, 4, 8, 14], "classification": "A", "letter": "D"},
        {"numbers": [1, 2, 3, 4, 9, 15], "classification": "A", "letter": "E"},
    ]
    res_block = analyze_portfolio_redundancy(candidates_block_conc)
    assert res_block["has_alerts"]
    assert len(res_block["block_concentration"]) == 1
    assert res_block["block_concentration"][0]["block"] == "1_10"

