from __future__ import annotations

from typing import Iterable, Sequence


def calculate_hits(candidate: Sequence[int], result: Sequence[int]) -> int:
    """Calcula la cantidad de aciertos entre un candidato y el resultado oficial."""
    return len(set(candidate) & set(result))


def rate_2plus(hits_list: Sequence[int]) -> float:
    """Proporcion de candidatos con 2 o mas aciertos."""
    if not hits_list:
        return 0.0
    return sum(1 for h in hits_list if h >= 2) / len(hits_list)


def rate_3plus(hits_list: Sequence[int]) -> float:
    """Proporcion de candidatos con 3 o mas aciertos."""
    if not hits_list:
        return 0.0
    return sum(1 for h in hits_list if h >= 3) / len(hits_list)


def avg_mean_hits(hits_list: Sequence[int]) -> float:
    """Promedio de aciertos por candidato en la cartera."""
    if not hits_list:
        return 0.0
    return sum(hits_list) / len(hits_list)


def unique_hits_union(candidates: Sequence[Sequence[int]], result: Sequence[int]) -> int:
    """Cantidad de numeros unicos del resultado oficial cubiertos por la cartera."""
    if not candidates or not result:
        return 0
    union_numbers = set()
    for cand in candidates:
        union_numbers.update(cand)
    return len(union_numbers & set(result))


def average_internal_overlap(candidates: Sequence[Sequence[int]]) -> float:
    """Promedio de numeros compartidos entre todos los pares de la cartera."""
    n = len(candidates)
    if n <= 1:
        return 0.0
    total_overlap = 0
    pairs_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total_overlap += len(set(candidates[i]) & set(candidates[j]))
            pairs_count += 1
    return total_overlap / pairs_count if pairs_count > 0 else 0.0


def high_redundancy_pairs(candidates: Sequence[Sequence[int]], threshold: int = 4) -> int:
    """Cantidad de pares que comparten al menos `threshold` numeros."""
    n = len(candidates)
    if n <= 1:
        return 0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            shared = len(set(candidates[i]) & set(candidates[j]))
            if shared >= threshold:
                count += 1
    return count
