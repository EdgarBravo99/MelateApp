from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


def calculate_gaps(numbers: list[int]) -> list[int]:
    """Calcula los desfases (gaps) internos entre números ordenados."""
    sorted_nums = sorted(numbers)
    if len(sorted_nums) < 2:
        return []
    return [sorted_nums[i + 1] - sorted_nums[i] - 1 for i in range(len(sorted_nums) - 1)]


def get_gap_signature(numbers: list[int]) -> str:
    """Genera la firma de desfase (gap_signature) (e.g. '3-7-4-9-11')."""
    gaps = calculate_gaps(numbers)
    return "-".join(str(g) for g in gaps)


def classify_gap_family(gaps: list[int]) -> str:
    """Clasifica la firma de desfases en una familia estructural descriptiva."""
    if not gaps:
        return "mixed"
    total = sum(gaps)
    max_g = max(gaps)

    if total <= 15 or max_g <= 2:
        return "compact"
    elif total >= 35 or max_g >= 15:
        return "wide"
    elif 16 <= total <= 34 and max_g <= 10:
        return "balanced"
    else:
        return "mixed"


def parse_gap_signature(sig: str) -> list[int]:
    """Convierte una firma de gaps string en una lista de enteros."""
    return [int(x) for x in sig.split("-")]


def analyze_gap_patterns(
    prior_history: list[dict[str, Any]],
    window: int = 50,
) -> dict[str, Any]:
    """Analiza los patrones de desfase (gaps) en el historial previo."""
    if not prior_history:
        return {
            "gap_signatures_counts": {},
            "gap_signatures_draws": {},
            "recent_signatures_counts": {},
            "recent_family_counts": {},
            "top_recent_family": "mixed",
            "recent_count": 0,
        }

    # Ordenar por sorteo para asegurar consistencia cronológica
    sorted_history = sorted(prior_history, key=lambda d: d.get("draw", 0))
    n_draws = len(sorted_history)

    # Ventana reciente
    recent_start_idx = max(0, n_draws - window)
    recent_history = sorted_history[recent_start_idx:]
    recent_count = len(recent_history)

    # Contadores históricos y de la ventana reciente
    gap_signatures_counts: dict[str, int] = {}
    gap_signatures_draws: dict[str, list[int]] = {}
    recent_signatures_counts: dict[str, int] = {}
    recent_families: list[str] = []

    for draw in sorted_history:
        draw_nums = draw.get("numbers", [])
        if not draw_nums:
            continue
        sig = get_gap_signature(draw_nums)
        draw_num = draw.get("draw", 0)

        gap_signatures_counts[sig] = gap_signatures_counts.get(sig, 0) + 1
        if sig not in gap_signatures_draws:
            gap_signatures_draws[sig] = []
        if draw_num not in gap_signatures_draws[sig]:
            gap_signatures_draws[sig].append(draw_num)

    for draw in recent_history:
        draw_nums = draw.get("numbers", [])
        if not draw_nums:
            continue
        sig = get_gap_signature(draw_nums)
        recent_signatures_counts[sig] = recent_signatures_counts.get(sig, 0) + 1
        gaps = calculate_gaps(draw_nums)
        recent_families.append(classify_gap_family(gaps))

    recent_family_counts = Counter(recent_families)
    top_recent_family = recent_family_counts.most_common(1)[0][0] if recent_families else "mixed"

    return {
        "gap_signatures_counts": gap_signatures_counts,
        "gap_signatures_draws": gap_signatures_draws,
        "recent_signatures_counts": recent_signatures_counts,
        "recent_family_counts": dict(recent_family_counts),
        "top_recent_family": top_recent_family,
        "recent_count": recent_count,
    }


def score_gap_echo(
    candidate_numbers: list[int],
    gap_patterns: dict[str, Any],
) -> dict[str, Any]:
    """Evalúa la firma de desfase y calcula el score de eco de gaps."""
    gaps = calculate_gaps(candidate_numbers)
    cand_sig = get_gap_signature(candidate_numbers)
    family = classify_gap_family(gaps)

    if len(candidate_numbers) < 6:
        return {
            "gap_echo_score": 0.0,
            "gap_signature": cand_sig,
            "matched_gap_patterns": [],
            "gap_family": family,
            "gap_echo_notes": ["Firma de desfases no evaluable debido a candidato incompleto."],
        }

    if not gap_patterns or not gap_patterns.get("recent_count", 0):
        return {
            "gap_echo_score": 0.0,
            "gap_signature": cand_sig,
            "matched_gap_patterns": [],
            "gap_family": family,
            "gap_echo_notes": ["Sin soporte de eco de gaps debido a historial insuficiente."],
        }

    sig_counts = gap_patterns.get("gap_signatures_counts", {})
    sig_draws = gap_patterns.get("gap_signatures_draws", {})

    # 1. Coincidencia exacta de firmas de gaps
    exact_count = sig_counts.get(cand_sig, 0)
    matched_gap_patterns = []
    if exact_count > 0:
        matched_gap_patterns.append({
            "gap_signature": cand_sig,
            "count": exact_count,
            "draws": sorted(sig_draws.get(cand_sig, [])),
        })

    # 2. Similitud con otras firmas (Manhattan distance <= 4)
    similar_support_count = 0
    cand_gaps = calculate_gaps(candidate_numbers)
    for hist_sig, count in sig_counts.items():
        if hist_sig == cand_sig:
            continue
        try:
            hist_gaps = parse_gap_signature(hist_sig)
            dist = sum(abs(cg - hg) for cg, hg in zip(cand_gaps, hist_gaps))
            if dist <= 4:
                similar_support_count += count
        except Exception:
            continue

    # 3. Penalización por firmas extremadamente comprimidas o dispersas sin soporte
    total_gaps = sum(cand_gaps)
    max_gap = max(cand_gaps)
    penalty = 0.0

    if exact_count == 0 and similar_support_count == 0:
        if total_gaps <= 5:
            penalty = 0.20
        elif max_gap >= 25:
            penalty = 0.20

    # 4. Cálculo del score de eco de gaps
    if exact_count > 0:
        score = min(0.60, 0.30 + exact_count * 0.15)
    elif similar_support_count > 0:
        score = min(0.40, 0.15 + similar_support_count * 0.05)
    else:
        score = 0.10

    # Coincidencia con la familia más frecuente en la ventana reciente
    top_recent_family = gap_patterns.get("top_recent_family", "mixed")
    if family == top_recent_family:
        score += 0.30

    # Aplicar penalización
    score -= penalty
    score = max(0.0, min(1.0, score))

    notes = []
    if exact_count > 0:
        notes.append(f"Firma de gaps observada exactamente {exact_count} veces en historial previo.")
    elif similar_support_count > 0:
        notes.append(f"Soporte por similitud estructural con {similar_support_count} firmas de gaps cercanas.")
    else:
        notes.append("Firma de gaps no observada previamente en el historial.")

    if penalty > 0:
        notes.append(f"Penalización aplicada por estructura extrema sin soporte: {round(penalty, 2)}")

    return {
        "gap_echo_score": round(score, 4),
        "gap_signature": cand_sig,
        "matched_gap_patterns": matched_gap_patterns,
        "gap_family": family,
        "gap_echo_notes": notes,
    }
