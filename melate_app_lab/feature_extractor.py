from __future__ import annotations

import statistics
from typing import Any, Iterable

from .number_utils import (
    block_presence_signature,
    block_signature,
    parity_signature,
    sum_band,
)


def safe_mean(data: list[float]) -> float:
    if not data:
        return 0.0
    return statistics.mean(data)


def safe_stdev(data: list[float]) -> float:
    if len(data) < 2:
        return 0.0
    return statistics.stdev(data)


def extract_features(
    numbers: list[int],
    training_history: list[dict[str, Any]],
    full_history: list[dict[str, Any]],
    graph_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract features from a 6-number combination for retrospective review.

    This function follows strict review_default guidelines, using descriptive
    names instead of prediction language.
    """
    sorted_numbers = sorted(numbers)
    total_sum = sum(sorted_numbers)

    # 1. Basic properties
    band = sum_band(total_sum)
    sig = block_signature(sorted_numbers)
    presence = block_presence_signature(sorted_numbers)
    parity_sig = parity_signature(sorted_numbers)
    even_count = sum(1 for n in sorted_numbers if n % 2 == 0)
    odd_count = 6 - even_count

    # 2. History frequency mapping
    freq_map: dict[int, int] = {i: 0 for i in range(1, 57)}
    for draw in training_history:
        for num in draw.get("numbers", []):
            if 1 <= num <= 56:
                freq_map[num] = freq_map.get(num, 0) + 1

    cand_frequencies = [float(freq_map[n]) for n in sorted_numbers]
    freq_mean = safe_mean(cand_frequencies)
    freq_std = safe_stdev(cand_frequencies)

    # 3. Graph degree and connectivity features
    node_degrees: dict[int, int] = {i: 0 for i in range(1, 57)}
    node_w_degrees: dict[int, int] = {i: 0 for i in range(1, 57)}
    edge_counts: dict[tuple[int, int], int] = {}

    if graph_data and graph_data.get("mode") == "historical":
        # Load from nodes
        for node in graph_data.get("nodes", []):
            num = int(node["number"])
            node_degrees[num] = int(node.get("degree", 0))
            node_w_degrees[num] = int(node.get("weighted_degree", 0))

        # Load from edges
        for edge in graph_data.get("edges", []):
            src = int(edge["source"])
            tgt = int(edge["target"])
            pair = (min(src, tgt), max(src, tgt))
            edge_counts[pair] = int(edge.get("count", 0))

    cand_degrees = [float(node_degrees[n]) for n in sorted_numbers]
    cand_w_degrees = [float(node_w_degrees[n]) for n in sorted_numbers]

    degree_mean = safe_mean(cand_degrees)
    degree_std = safe_stdev(cand_degrees)
    w_degree_mean = safe_mean(cand_w_degrees)
    w_degree_std = safe_stdev(cand_w_degrees)

    # Calculate candidate's graph support score and pair edge counts
    graph_support_score = 0
    pair_edges_count = 0
    for i in range(6):
        for j in range(i + 1, 6):
            pair = (sorted_numbers[i], sorted_numbers[j])
            if pair in edge_counts:
                graph_support_score += edge_counts[pair]
                pair_edges_count += 1

    # 4. Diversity score & historical exact match
    diversity_score = presence.count("1")

    full_history_sets = {frozenset(draw.get("numbers", [])) for draw in full_history}
    historical_exact_match = frozenset(sorted_numbers) in full_history_sets

    return {
        "numbers": sorted_numbers,
        "sum": total_sum,
        "sum_band": band,
        "block_signature": sig,
        "block_presence_signature": presence,
        "parity_signature": parity_sig,
        "even_count": even_count,
        "odd_count": odd_count,
        "frequency_mean": freq_mean,
        "frequency_std": freq_std,
        "degree_mean": degree_mean,
        "degree_std": degree_std,
        "weighted_degree_mean": w_degree_mean,
        "weighted_degree_std": w_degree_std,
        "graph_support_score": graph_support_score,
        "pair_edges_count": pair_edges_count,
        "diversity_score": diversity_score,
        "historical_exact_match": historical_exact_match,
    }


def extract_features_batch(
    candidates: list[list[int]],
    training_history: list[dict[str, Any]],
    full_history: list[dict[str, Any]],
    graph_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Extrae caracteristicas para un lote de candidatos optimizando el uso de CPU y RAM.

    Precomputa diccionarios de frecuencia y grafos una sola vez para todo el lote.
    """
    # 1. Precomputar mapeo de frecuencias en historial de entrenamiento
    freq_map: dict[int, int] = {i: 0 for i in range(1, 57)}
    for draw in training_history:
        for num in draw.get("numbers", []):
            if 1 <= num <= 56:
                freq_map[num] = freq_map.get(num, 0) + 1

    # 2. Precomputar grados del grafo y conectividades
    node_degrees: dict[int, int] = {i: 0 for i in range(1, 57)}
    node_w_degrees: dict[int, int] = {i: 0 for i in range(1, 57)}
    edge_counts: dict[tuple[int, int], int] = {}

    if graph_data and graph_data.get("mode") == "historical":
        for node in graph_data.get("nodes", []):
            num = int(node["number"])
            node_degrees[num] = int(node.get("degree", 0))
            node_w_degrees[num] = int(node.get("weighted_degree", 0))

        for edge in graph_data.get("edges", []):
            src = int(edge["source"])
            tgt = int(edge["target"])
            pair = (min(src, tgt), max(src, tgt))
            edge_counts[pair] = int(edge.get("count", 0))

    # 3. Precomputar sets de coincidencia exacta historica
    full_history_sets = {frozenset(draw.get("numbers", [])) for draw in full_history}

    # 4. Procesar cada candidato en el lote
    results = []
    for numbers in candidates:
        sorted_numbers = sorted(numbers)
        total_sum = sum(sorted_numbers)

        band = sum_band(total_sum)
        sig = block_signature(sorted_numbers)
        presence = block_presence_signature(sorted_numbers)
        parity_sig = parity_signature(sorted_numbers)
        even_count = sum(1 for n in sorted_numbers if n % 2 == 0)
        odd_count = 6 - even_count

        cand_frequencies = [float(freq_map[n]) for n in sorted_numbers]
        freq_mean = safe_mean(cand_frequencies)
        freq_std = safe_stdev(cand_frequencies)

        cand_degrees = [float(node_degrees[n]) for n in sorted_numbers]
        cand_w_degrees = [float(node_w_degrees[n]) for n in sorted_numbers]

        degree_mean = safe_mean(cand_degrees)
        degree_std = safe_stdev(cand_degrees)
        w_degree_mean = safe_mean(cand_w_degrees)
        w_degree_std = safe_stdev(cand_w_degrees)

        graph_support_score = 0
        pair_edges_count = 0
        for i in range(6):
            for j in range(i + 1, 6):
                pair = (sorted_numbers[i], sorted_numbers[j])
                if pair in edge_counts:
                    graph_support_score += edge_counts[pair]
                    pair_edges_count += 1

        diversity_score = presence.count("1")
        historical_exact_match = frozenset(sorted_numbers) in full_history_sets

        results.append({
            "numbers": sorted_numbers,
            "sum": total_sum,
            "sum_band": band,
            "block_signature": sig,
            "block_presence_signature": presence,
            "parity_signature": parity_sig,
            "even_count": even_count,
            "odd_count": odd_count,
            "frequency_mean": freq_mean,
            "frequency_std": freq_std,
            "degree_mean": degree_mean,
            "degree_std": degree_std,
            "weighted_degree_mean": w_degree_mean,
            "weighted_degree_std": w_degree_std,
            "graph_support_score": graph_support_score,
            "pair_edges_count": pair_edges_count,
            "diversity_score": diversity_score,
            "historical_exact_match": historical_exact_match,
        })

    return results

