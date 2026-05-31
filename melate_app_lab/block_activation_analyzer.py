from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Definición de bloques estándar de Melate 1-56
BLOCK_RANGES = {
    "B1": (1, 10),
    "B2": (11, 20),
    "B3": (21, 30),
    "B4": (31, 40),
    "B5": (41, 50),
    "B6": (51, 56),
}


def get_block_counts(numbers: Iterable[int]) -> dict[str, int]:
    """Cuenta cuántos números pertenecen a cada uno de los bloques B1-B6."""
    counts = {k: 0 for k in BLOCK_RANGES}
    for n in numbers:
        for block, (start, end) in BLOCK_RANGES.items():
            if start <= n <= end:
                counts[block] += 1
                break
    return counts


def get_block_signature(numbers: Iterable[int]) -> str:
    """Genera la firma de bloques (e.g. '1-1-2-1-1-0') para una combinación."""
    counts = get_block_counts(numbers)
    return "-".join(str(counts[b]) for b in ["B1", "B2", "B3", "B4", "B5", "B6"])


def analyze_block_activity(
    prior_history: list[dict[str, Any]],
    window: int = 30,
) -> dict[str, Any]:
    """Analiza la actividad de los bloques B1-B6 en el historial previo."""
    if not prior_history:
        return {
            "block_frequency": {k: 0 for k in BLOCK_RANGES},
            "block_presence": {k: 0 for k in BLOCK_RANGES},
            "common_block_signatures": [],
            "recent_block_signatures": [],
            "activated_blocks": [],
            "cold_blocks": [],
            "recent_count": 0,
        }

    # Ordenar por sorteo para asegurar consistencia cronológica
    sorted_history = sorted(prior_history, key=lambda d: d.get("draw", 0))
    n_draws = len(sorted_history)

    # Ventana reciente
    recent_start_idx = max(0, n_draws - window)
    recent_history = sorted_history[recent_start_idx:]
    recent_count = len(recent_history)

    # Frecuencia y presencia reciente
    block_frequency = {k: 0 for k in BLOCK_RANGES}
    block_presence = {k: 0 for k in BLOCK_RANGES}

    for draw in recent_history:
        draw_nums = draw.get("numbers", [])
        counts = get_block_counts(draw_nums)
        for b, count in counts.items():
            block_frequency[b] += count
            if count > 0:
                block_presence[b] += 1

    # Firmas en todo el historial y en ventana reciente
    broad_sigs = Counter(get_block_signature(d.get("numbers", [])) for d in sorted_history if d.get("numbers"))
    recent_sigs = Counter(get_block_signature(d.get("numbers", [])) for d in recent_history if d.get("numbers"))

    # Definir bloques activos y fríos
    # Frecuencia promedio esperada por bloque = (sorteos * 6) / 6 = sorteos
    avg_activity = recent_count
    activated_blocks = []
    cold_blocks = []

    for b, freq in block_frequency.items():
        if freq > avg_activity:
            activated_blocks.append(b)
        elif freq < avg_activity:
            cold_blocks.append(b)

    return {
        "block_frequency": block_frequency,
        "block_presence": block_presence,
        "common_block_signatures": broad_sigs.most_common(),
        "recent_block_signatures": recent_sigs.most_common(),
        "activated_blocks": sorted(activated_blocks),
        "cold_blocks": sorted(cold_blocks),
        "recent_count": recent_count,
    }


def score_block_composition(
    candidate_numbers: list[int],
    block_activity: dict[str, Any],
) -> dict[str, Any]:
    """Evalúa la composición y distribución de bloques para un candidato."""
    cand_sig = get_block_signature(candidate_numbers)
    if not block_activity or not block_activity.get("recent_count", 0):
        return {
            "block_activity_score": 0.0,
            "block_signature": cand_sig,
            "activated_blocks": [],
            "cold_blocks": [],
            "block_completion": False,
            "overconcentration_penalty": 0.0,
            "block_activity_notes": ["Sin soporte de bloques debido a historial insuficiente."],
        }

    cand_counts = get_block_counts(candidate_numbers)
    common_sigs = block_activity.get("common_block_signatures", [])
    
    # Detección de completado de firma: si está entre las 5 más comunes históricamente
    top_5_sigs = [sig for sig, _ in common_sigs[:5]]
    block_completion = cand_sig in top_5_sigs

    # Penalización por sobreconcentración en bloques sin soporte
    penalty = 0.0
    activated_blocks = block_activity.get("activated_blocks", [])

    for block, count in cand_counts.items():
        if count >= 4:
            base_penalty = 0.20
            if block not in activated_blocks:
                base_penalty *= 2.0
            penalty += base_penalty
        elif count == 3:
            base_penalty = 0.08
            if block not in activated_blocks:
                base_penalty *= 2.0
            penalty += base_penalty

    penalty = min(0.5, penalty)

    # Cálculo del score descriptivo
    score = 0.40 if block_completion else 0.10

    # Cobertura de bloques activos
    activated_count = sum(cand_counts[b] for b in activated_blocks)
    coverage_bonus = (activated_count / 6.0) * 0.60
    score += coverage_bonus

    # Restar penalizaciones
    score -= penalty
    score = max(0.0, min(1.0, score))

    notes = []
    if block_completion:
        notes.append("Firma de bloque con soporte histórico frecuente.")
    else:
        notes.append("Firma de bloque poco frecuente en el historial.")

    if penalty > 0:
        notes.append(f"Penalización aplicada por sobreconcentración en bloques: {round(penalty, 2)}")
    else:
        notes.append("Distribución espacial equilibrada en bloques.")

    return {
        "block_activity_score": round(score, 4),
        "block_signature": cand_sig,
        "activated_blocks": activated_blocks,
        "cold_blocks": block_activity.get("cold_blocks", []),
        "block_completion": block_completion,
        "overconcentration_penalty": round(penalty, 4),
        "block_activity_notes": notes,
    }
