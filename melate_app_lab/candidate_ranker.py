from __future__ import annotations

from typing import Any

DEFAULT_WEIGHTS = {
    "graph_support_score": 1.5,
    "pair_edges_count": 1.0,
    "diversity_score": 2.0,
    "parity_balance_3_3": 3.0,
    "parity_balance_4_2_or_2_4": 1.5,
    "block_signature_match": 3.0,
    "sum_band_match": 2.0,
    "historical_exact_match_penalty": -50.0,
}


def score_candidate(
    features: dict[str, Any],
    common_signatures: list[str],
    common_bands: list[str],
    weights: dict[str, float] | None = None,
) -> float:
    """Calcula un puntaje de ranking heuristico usando pesos parametrizados."""
    w = DEFAULT_WEIGHTS if weights is None else {**DEFAULT_WEIGHTS, **weights}
    score = 0.0

    # 1. Conectividad en grafo historico
    score += float(features.get("graph_support_score", 0)) * w.get("graph_support_score", 1.5)
    score += float(features.get("pair_edges_count", 0)) * w.get("pair_edges_count", 1.0)

    # 2. Diversidad de bloques espaciales
    diversity = int(features.get("diversity_score", 0))
    score += float(diversity) * w.get("diversity_score", 2.0)

    # 3. Balance de paridad (pares/impares)
    even_count = int(features.get("even_count", 0))
    odd_count = int(features.get("odd_count", 0))
    if even_count == 3 and odd_count == 3:
        score += w.get("parity_balance_3_3", 3.0)
    elif (even_count == 4 and odd_count == 2) or (even_count == 2 and odd_count == 4):
        score += w.get("parity_balance_4_2_or_2_4", 1.5)

    # 4. Coincidencia con firmas de bloque comunes
    if features.get("block_signature") in common_signatures:
        score += w.get("block_signature_match", 3.0)

    # 5. Coincidencia con bandas de suma comunes
    if features.get("sum_band") in common_bands:
        score += w.get("sum_band_match", 2.0)

    # 6. Penalizacion de duplicados exactos historicos
    if features.get("historical_exact_match", False):
        score += w.get("historical_exact_match_penalty", -50.0)

    return score


def rank_candidates(
    candidates_features: list[dict[str, Any]],
    common_signatures: list[str],
    common_bands: list[str],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Ordena los candidatos descendentemente segun su puntaje."""
    scored = []
    for cand in candidates_features:
        score = score_candidate(cand, common_signatures, common_bands, weights=weights)
        cand_copy = dict(cand)
        cand_copy["rank_score"] = score
        scored.append(cand_copy)

    # Ordenar descendentemente por score, y por suma como criterio secundario
    scored.sort(key=lambda c: (-c["rank_score"], c["sum"]))

    for idx, cand in enumerate(scored):
        cand["rank"] = idx + 1

    return scored
