from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def analyze_pair_lag(
    prior_history: list[dict[str, Any]],
    window: int = 30,
    max_lag: int = 5,
) -> dict[str, Any]:
    """Analiza relaciones temporales de coaparición y desfase (lag) entre pares de números.

    Usa únicamente el historial previo disponible de manera estrictamente retrospectiva.
    """
    if not prior_history:
        return {
            "pairs_info": {},
            "recent_count": 0,
            "broad_count": 0,
        }

    # Ordenar por sorteo para asegurar consistencia cronológica
    sorted_history = sorted(prior_history, key=lambda d: d.get("draw", 0))
    n_draws = len(sorted_history)

    # Ventana reciente
    recent_start_idx = max(0, n_draws - window)
    recent_history = sorted_history[recent_start_idx:]

    def process_slice(slice_history: list[dict[str, Any]]) -> tuple[Any, Any, Any, Any]:
        m = len(slice_history)
        exact_counts: dict[tuple[int, int], int] = {}
        lag_counts: dict[tuple[int, int], int] = {}
        exact_draws: dict[tuple[int, int], list[int]] = {}
        lag_draws: dict[tuple[int, int], list[int]] = {}

        for i in range(m):
            draw_i = slice_history[i]
            draw_num_i = draw_i.get("draw", 0)
            nums_i = sorted(draw_i.get("numbers", []))

            # Coaparición exacta
            for u in range(len(nums_i)):
                for v in range(u + 1, len(nums_i)):
                    pair = (nums_i[u], nums_i[v])
                    exact_counts[pair] = exact_counts.get(pair, 0) + 1
                    if pair not in exact_draws:
                        exact_draws[pair] = []
                    if draw_num_i not in exact_draws[pair]:
                        exact_draws[pair].append(draw_num_i)

            # Coaparición con desfase (lag)
            for j in range(i + 1, min(i + max_lag + 1, m)):
                draw_j = slice_history[j]
                draw_num_j = draw_j.get("draw", 0)
                nums_j = sorted(draw_j.get("numbers", []))

                for n1 in nums_i:
                    for n2 in nums_j:
                        if n1 != n2:
                            pair = (min(n1, n2), max(n1, n2))
                            lag_counts[pair] = lag_counts.get(pair, 0) + 1
                            if pair not in lag_draws:
                                lag_draws[pair] = []
                            for dn in (draw_num_i, draw_num_j):
                                if dn not in lag_draws[pair]:
                                    lag_draws[pair].append(dn)

        return exact_counts, lag_counts, exact_draws, lag_draws

    recent_exact, recent_lag, recent_ex_draws, recent_lg_draws = process_slice(recent_history)
    broad_exact, broad_lag, _, _ = process_slice(sorted_history)

    all_pairs = set(recent_exact.keys()) | set(recent_lag.keys()) | set(broad_exact.keys()) | set(broad_lag.keys())

    pairs_info = {}
    for pair in all_pairs:
        pairs_info[pair] = {
            "recent_exact_count": recent_exact.get(pair, 0),
            "recent_lag_count": recent_lag.get(pair, 0),
            "broad_exact_count": broad_exact.get(pair, 0),
            "broad_lag_count": broad_lag.get(pair, 0),
            "recent_draws": sorted(recent_ex_draws.get(pair, [])),
            "lag_draws": sorted(recent_lg_draws.get(pair, [])),
        }

    return {
        "pairs_info": pairs_info,
        "recent_count": len(recent_history),
        "broad_count": n_draws,
        "window": window,
    }


def score_pair_lag_support(
    candidate_numbers: list[int],
    pair_lag_data: dict[str, Any],
    min_exact_count: int = 1,
    min_lag_count: int = 2,
    min_total_support: float = 2.0,
) -> dict[str, Any]:
    """Evalúa el soporte de coaparición diferida y exacta para un candidato."""
    if not pair_lag_data or "pairs_info" not in pair_lag_data:
        return {
            "pair_lag_score": 0.0,
            "bridge_pairs": [],
            "pair_lag_notes": ["Sin soporte temporal debido a historial insuficiente."],
        }

    sorted_nums = sorted(candidate_numbers)
    if len(sorted_nums) < 2:
        return {
            "pair_lag_score": 0.0,
            "bridge_pairs": [],
            "pair_lag_notes": [],
        }

    pairs_info = pair_lag_data["pairs_info"]

    bridge_pairs = []
    total_support = 0.0

    for i in range(len(sorted_nums)):
        for j in range(i + 1, len(sorted_nums)):
            pair = (sorted_nums[i], sorted_nums[j])
            if pair in pairs_info:
                info = pairs_info[pair]
                exact_c = info.get("recent_exact_count", 0)
                lag_c = info.get("recent_lag_count", 0)

                # Aplicar thresholds mínimos configurables
                is_significant = False
                if exact_c >= min_exact_count or lag_c >= min_lag_count:
                    if (exact_c + lag_c) >= min_total_support:
                        is_significant = True

                if is_significant:
                    bridge_pairs.append({
                        "pair": list(pair),
                        "exact_count": exact_c,
                        "lag_count": lag_c,
                        "recent_draws": info.get("recent_draws", []),
                        "lag_draws": info.get("lag_draws", []),
                    })
                    # Contribución al score
                    pair_score = min(2.0, exact_c * 0.5 + lag_c * 0.2)
                    total_support += pair_score

    # Normalizar score para que esté acotado entre 0.0 y 1.0
    raw_score = min(1.0, total_support / 5.0) if total_support > 0 else 0.0

    # Aplicar factor de confianza para historial pequeño
    window_val = pair_lag_data.get("window", 30)
    broad_count = pair_lag_data.get("broad_count", 0)
    confidence = min(1.0, broad_count / window_val) if window_val > 0 else 1.0
    normalized_score = raw_score * confidence

    notes = []
    if bridge_pairs:
        # Ordenar pares puente por fuerza
        bridge_pairs.sort(key=lambda x: (x["exact_count"], x["lag_count"]), reverse=True)
        strongest = bridge_pairs[0]
        notes.append(
            f"Par {strongest['pair'][0]}-{strongest['pair'][1]} con coaparición histórica exacta ({strongest['exact_count']}) y soporte lag ({strongest['lag_count']})"
        )
    else:
        notes.append("No se detectaron pares puente con soporte temporal reciente.")

    if confidence < 1.0:
        notes.append("Soporte reducido debido a volumen de historial limitado.")

    return {
        "pair_lag_score": round(normalized_score, 4),
        "bridge_pairs": bridge_pairs,
        "pair_lag_notes": notes,
    }
