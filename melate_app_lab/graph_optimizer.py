from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable

from .number_utils import number_block


Severity = str


def severity_for_edge(edge_type: str) -> Severity:
    concentration_edges = {"high_block_pair", "adjacent_high_pair", "missed_from_played_set"}
    review_edges = {"captured_together", "same_block"}
    if edge_type in concentration_edges:
        return "concentration"
    if edge_type in review_edges:
        return "review"
    return "info"


def select_missed_played_relations(
    missed: Iterable[int],
    played_numbers: Iterable[int],
    captured: Iterable[int],
    repeated_anchors: Iterable[int],
) -> list[tuple[int, int, list[str]]]:
    played_set = set(played_numbers)
    captured_set = set(captured)
    repeated_set = set(repeated_anchors)
    relations: list[tuple[int, int, list[str]]] = []

    for missed_number in sorted(set(missed)):
        same_block = {
            played_number
            for played_number in played_set
            if number_block(played_number) == number_block(missed_number)
        }
        candidates = sorted((repeated_set | captured_set | same_block) & played_set)
        for played_number in candidates:
            reasons = []
            if played_number in repeated_set:
                reasons.append("repeated_anchor")
            if played_number in captured_set:
                reasons.append("captured")
            if played_number in same_block:
                reasons.append("same_block")
            relations.append((missed_number, played_number, reasons))

    return relations


def summarize_edges(edges: Iterable[dict[str, object]]) -> dict[str, object]:
    edge_list = list(edges)
    by_type = Counter(str(edge["type"]) for edge in edge_list)
    by_severity = Counter(str(edge.get("severity", "info")) for edge in edge_list)
    return {
        "total_edges": len(edge_list),
        "by_type": dict(sorted(by_type.items())),
        "by_severity": dict(sorted(by_severity.items())),
    }


def build_graph_stats(
    nodes: Iterable[dict[str, object]],
    edges: Iterable[dict[str, object]],
    result_numbers: Iterable[int],
    played_numbers: Iterable[int],
    captured: Iterable[int],
    missed: Iterable[int],
    missed_relations: Iterable[tuple[int, int, list[str]]],
) -> dict[str, int]:
    node_list = list(nodes)
    edge_list = list(edges)
    return {
        "node_count": len(node_list),
        "edge_count": len(edge_list),
        "result_count": len(set(result_numbers)),
        "played_unique_count": len(set(played_numbers)),
        "captured_count": len(set(captured)),
        "missed_count": len(set(missed)),
        "missed_from_played_set_count": len(list(missed_relations)),
    }


def captured_pairs(captured: Iterable[int]) -> list[tuple[int, int]]:
    return list(combinations(sorted(set(captured)), 2))
