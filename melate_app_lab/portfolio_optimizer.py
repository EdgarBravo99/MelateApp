from __future__ import annotations

from typing import Any


def compute_portfolio_diversity_score(portfolio: list[dict[str, Any]]) -> float:
    """Calcula la cantidad de numeros unicos cubiertos por la cartera."""
    if not portfolio:
        return 0.0
    unique_numbers = set()
    for cand in portfolio:
        unique_numbers.update(cand.get("numbers", []))
    return float(len(unique_numbers))


def optimize_portfolio(candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """Selecciona top_k candidatos penalizando el solapamiento con los ya seleccionados.
    
    Usa un algoritmo voraz donde en cada paso se castiga el rank_score de cada candidato
    restante segun la redundancia que introduce a la cartera seleccionada.
    """
    if not candidates:
        return []
    
    remaining = list(candidates)
    selected_so_far: list[dict[str, Any]] = []
    
    while len(selected_so_far) < top_k and remaining:
        best_cand = None
        best_effective_score = -999999.0
        best_idx = -1
        
        for idx, cand in enumerate(remaining):
            base_score = cand.get("rank_score", 0.0)
            penalty = 0.0
            
            if selected_so_far:
                # Penalizacion por solapamiento promedio
                overlap_sum = 0
                for sel in selected_so_far:
                    shared = len(set(cand["numbers"]) & set(sel["numbers"]))
                    overlap_sum += shared
                    
                    # Penalizacion fuerte por pares con alta redundancia
                    if shared >= 4:
                        penalty += 5.0
                    if shared >= 5:
                        penalty += 15.0
                        
                avg_overlap = overlap_sum / len(selected_so_far)
                penalty += avg_overlap * 2.0
                
            effective_score = base_score - penalty
            if effective_score > best_effective_score:
                best_effective_score = effective_score
                best_cand = cand
                best_idx = idx
                
        if best_cand is not None and best_idx != -1:
            selected_so_far.append(best_cand)
            remaining.pop(best_idx)
        else:
            break
            
    return selected_so_far
