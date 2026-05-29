from __future__ import annotations

from typing import Any


def score_candidate(
    features: dict[str, Any],
    common_signatures: list[str],
    common_bands: list[str],
) -> float:
    """Calculate a heuristic rank score for a candidate's features.

    Higher scores indicate better structural alignment with historical patterns,
    better spatial coverage, and higher graph support, without using prediction language.
    """
    score = 0.0

    # 1. Graph connectivity (weights)
    score += float(features.get("graph_support_score", 0)) * 1.5
    score += float(features.get("pair_edges_count", 0)) * 1.0

    # 2. Block diversity
    # diversity_score is 1 to 5 (number of occupied blocks)
    diversity = int(features.get("diversity_score", 0))
    score += float(diversity) * 2.0

    # 3. Parity balance
    even_count = int(features.get("even_count", 0))
    odd_count = int(features.get("odd_count", 0))
    if even_count == 3 and odd_count == 3:
        score += 3.0
    elif (even_count == 4 and odd_count == 2) or (even_count == 2 and odd_count == 4):
        score += 1.5
    else:
        score += 0.0

    # 4. Signature matching
    if features.get("block_signature") in common_signatures:
        score += 3.0

    # 5. Sum band matching
    if features.get("sum_band") in common_bands:
        score += 2.0

    # 6. Exclude exact match duplicates from history
    if features.get("historical_exact_match", False):
        score -= 50.0

    return score


def rank_candidates(
    candidates_features: list[dict[str, Any]],
    common_signatures: list[str],
    common_bands: list[str],
) -> list[dict[str, Any]]:
    """Rank candidates descending by their score.

    Adds 'rank_score' and 'rank' keys to each candidate's feature dictionary.
    """
    scored = []
    for cand in candidates_features:
        score = score_candidate(cand, common_signatures, common_bands)
        cand_copy = dict(cand)
        cand_copy["rank_score"] = score
        scored.append(cand_copy)

    # Sort descending by score, ascending by sum as secondary
    scored.sort(key=lambda c: (-c["rank_score"], c["sum"]))

    for idx, cand in enumerate(scored):
        cand["rank"] = idx + 1

    return scored
