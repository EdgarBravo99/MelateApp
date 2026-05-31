from __future__ import annotations

import collections
from typing import Any


def compute_portfolio_diversity_score(portfolio: list[dict[str, Any]]) -> float:
    """Calcula la cantidad de numeros unicos cubiertos por la cartera."""
    if not portfolio:
        return 0.0
    unique_numbers = set()
    for cand in portfolio:
        unique_numbers.update(cand.get("numbers", []))
    return float(len(unique_numbers))


def optimize_portfolio(
    candidates: list[dict[str, Any]],
    top_k: int,
    use_structural_diversification: bool = False,
    structural_diversity_weight: float = 1.0,
    structural_score_tiebreaker_weight: float = 0.25,
    block_signature_diversity_bonus: float = 1.0,
    gap_family_diversity_bonus: float = 1.0,
    pair_overlap_penalty: float = 1.5,
) -> list[dict[str, Any]]:
    """Selecciona top_k candidatos penalizando el solapamiento con los ya seleccionados.
    
    Si use_structural_diversification es True, aplica penalizaciones y bonus
    estructurales adicionales para diversificar las firmas de bloque y familias de gaps,
    y utiliza el structural_signal_score como desempate suave.
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
            number_penalty = 0.0
            
            if selected_so_far:
                # Penalizacion por solapamiento promedio (numeros)
                overlap_sum = 0
                for sel in selected_so_far:
                    shared = len(set(cand["numbers"]) & set(sel["numbers"]))
                    overlap_sum += shared
                    
                    # Penalizacion fuerte por pares con alta redundancia
                    if shared >= 4:
                        number_penalty += 5.0
                    if shared >= 5:
                        number_penalty += 15.0
                        
                avg_overlap = overlap_sum / len(selected_so_far)
                number_penalty += avg_overlap * 2.0
                
            if not use_structural_diversification:
                effective_score = base_score - number_penalty
            else:
                # Diversificacion estructural activa
                structural_modifiers = 0.0
                if selected_so_far:
                    # Penalizacion por overlap de pares
                    cand_pairs = {frozenset([cand["numbers"][i], cand["numbers"][j]]) for i in range(6) for j in range(i+1, 6)}
                    pair_overlap_sum = 0
                    for sel in selected_so_far:
                        sel_pairs = {frozenset([sel["numbers"][k], sel["numbers"][l]]) for k in range(6) for l in range(k+1, 6)}
                        pair_overlap_sum += len(cand_pairs & sel_pairs)
                    avg_pair_overlap = pair_overlap_sum / len(selected_so_far)
                    pair_penalty = avg_pair_overlap * pair_overlap_penalty
                    
                    # Diversificacion por firma de bloque y familia de gaps
                    block_sig = cand.get("block_signature")
                    gap_fam = cand.get("gap_family")
                    
                    selected_sigs = [sel.get("block_signature") for sel in selected_so_far if sel.get("block_signature") is not None]
                    selected_gaps = [sel.get("gap_family") for sel in selected_so_far if sel.get("gap_family") is not None]
                    
                    sig_modifier = 0.0
                    if block_sig is not None:
                        if block_sig not in selected_sigs:
                            sig_modifier = block_signature_diversity_bonus
                        else:
                            sig_modifier = -selected_sigs.count(block_sig) * block_signature_diversity_bonus
                            
                    gap_modifier = 0.0
                    if gap_fam is not None:
                        if gap_fam not in selected_gaps:
                            gap_modifier = gap_family_diversity_bonus
                        else:
                            gap_modifier = -selected_gaps.count(gap_fam) * gap_family_diversity_bonus
                            
                    structural_modifiers = -pair_penalty + sig_modifier + gap_modifier
                else:
                    block_sig = cand.get("block_signature")
                    gap_fam = cand.get("gap_family")
                    sig_modifier = block_signature_diversity_bonus if block_sig is not None else 0.0
                    gap_modifier = gap_family_diversity_bonus if gap_fam is not None else 0.0
                    structural_modifiers = sig_modifier + gap_modifier
                    
                # Desempate suave con structural_signal_score
                tiebreaker = cand.get("structural_signal_score", 0.0) * structural_score_tiebreaker_weight
                
                # Integrar modificadores estructurales ponderados
                effective_score = (
                    base_score
                    - number_penalty
                    + (structural_modifiers + tiebreaker) * structural_diversity_weight
                )
                
            if effective_score > best_effective_score:
                best_effective_score = effective_score
                best_cand = cand
                best_idx = idx
                
        if best_cand is not None and best_idx != -1:
            # Asignar selection_reason si la diversificacion esta activa
            if use_structural_diversification:
                block_sig = best_cand.get("block_signature")
                gap_fam = best_cand.get("gap_family")
                selected_sigs = [sel.get("block_signature") for sel in selected_so_far if sel.get("block_signature") is not None]
                selected_gaps = [sel.get("gap_family") for sel in selected_so_far if sel.get("gap_family") is not None]
                
                if not selected_so_far:
                    best_cand["selection_reason"] = "Candidato seleccionado por buen rank_score y baja redundancia estructural."
                elif block_sig is not None and block_sig not in selected_sigs:
                    best_cand["selection_reason"] = "Candidato seleccionado por aportar block_signature diferente a la cartera."
                elif gap_fam is not None and gap_fam not in selected_gaps:
                    best_cand["selection_reason"] = "Candidato seleccionado como cobertura estructural con gap_family distinta."
                else:
                    best_cand["selection_reason"] = "Candidato seleccionado por buen rank_score y baja redundancia estructural."
            else:
                best_cand["selection_reason"] = "Candidato seleccionado por el ranker actual."
                
            selected_so_far.append(best_cand)
            remaining.pop(best_idx)
        else:
            break
            
    return selected_so_far


def calculate_portfolio_structural_metrics(portfolio: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula metricas agregadas de diversidad estructural para una cartera."""
    if not portfolio:
        return {
            "unique_block_signatures": 0,
            "unique_gap_families": 0,
            "average_structural_signal_score": 0.0,
            "dominant_block_signature_ratio": 0.0,
            "dominant_gap_family_ratio": 0.0,
            "average_pair_overlap": 0.0,
            "structural_profile_coverage": 0.0,
        }
        
    sigs = [c.get("block_signature") for c in portfolio if c.get("block_signature") is not None]
    gaps = [c.get("gap_family") for c in portfolio if c.get("gap_family") is not None]
    scores = [c.get("structural_signal_score", 0.0) for c in portfolio]
    
    unique_sigs = len(set(sigs))
    unique_gaps = len(set(gaps))
    avg_score = round(sum(scores) / len(portfolio), 4)
    
    # Dominant ratios
    dominant_sig_ratio = 0.0
    if sigs:
        sig_counts = collections.Counter(sigs)
        dominant_sig_ratio = round(sig_counts.most_common(1)[0][1] / len(sigs), 4)
        
    dominant_gap_ratio = 0.0
    if gaps:
        gap_counts = collections.Counter(gaps)
        dominant_gap_ratio = round(gap_counts.most_common(1)[0][1] / len(gaps), 4)
        
    # Average pair overlap
    n = len(portfolio)
    if n <= 1:
        avg_pair_overlap = 0.0
    else:
        total_pair_overlap = 0
        pair_combinations_count = 0
        cand_pairs_list = []
        for c in portfolio:
            nums = c.get("numbers", [])
            if len(nums) == 6:
                cand_pairs = {frozenset([nums[i], nums[j]]) for i in range(6) for j in range(i+1, 6)}
            else:
                cand_pairs = set()
            cand_pairs_list.append(cand_pairs)
            
        for i in range(n):
            for j in range(i + 1, n):
                total_pair_overlap += len(cand_pairs_list[i] & cand_pairs_list[j])
                pair_combinations_count += 1
        avg_pair_overlap = round(total_pair_overlap / pair_combinations_count, 4) if pair_combinations_count > 0 else 0.0
        
    # Structural profile coverage
    unique_profiles = set()
    for c in portfolio:
        sig = c.get("block_signature")
        gap = c.get("gap_family")
        if sig is not None or gap is not None:
            unique_profiles.add((sig, gap))
    profile_coverage = round(len(unique_profiles) / len(portfolio), 4)
    
    return {
        "unique_block_signatures": unique_sigs,
        "unique_gap_families": unique_gaps,
        "average_structural_signal_score": avg_score,
        "dominant_block_signature_ratio": dominant_sig_ratio,
        "dominant_gap_family_ratio": dominant_gap_ratio,
        "average_pair_overlap": avg_pair_overlap,
        "structural_profile_coverage": profile_coverage,
    }
