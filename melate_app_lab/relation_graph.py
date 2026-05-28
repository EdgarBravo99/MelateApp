from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Iterable

from .graph_optimizer import (
    build_graph_stats,
    captured_pairs,
    select_missed_played_relations,
    severity_for_edge,
    summarize_edges,
)
from .guardrails import validate_output_json
from .number_utils import number_block, parse_numbers
from .postmortem import postmortem_review


def _node(number: int, roles: set[str]) -> dict[str, object]:
    return {"id": f"n{number}", "number": number, "block": number_block(number), "roles": sorted(roles)}


def _edge(source: int, target: int, edge_type: str, evidence: str) -> dict[str, object]:
    return {
        "source": f"n{source}",
        "target": f"n{target}",
        "numbers": sorted([source, target]),
        "type": edge_type,
        "severity": severity_for_edge(edge_type),
        "evidence_es": evidence,
    }


def build_relation_graph(
    draw: int,
    result_numbers: Iterable[int] | str,
    played_tickets: list[Iterable[int] | str] | None = None,
    postmortem_result: dict[str, object] | None = None,
) -> dict[str, object]:
    result = parse_numbers(result_numbers)
    played = [parse_numbers(ticket) for ticket in played_tickets or []]
    if postmortem_result is None and played:
        postmortem_result = postmortem_review(draw, result, played)
    captured = set(postmortem_result.get("captured_numbers", []) if postmortem_result else [])
    missed = set(postmortem_result.get("missed_numbers", []) if postmortem_result else [])
    repeated_anchors = set(postmortem_result.get("overused_played_numbers", []) if postmortem_result else [])
    played_numbers = {number for ticket in played for number in ticket}
    all_numbers = set(result) | played_numbers | captured | missed

    nodes = []
    for number in sorted(all_numbers):
        roles = set()
        if number in result:
            roles.add("result")
        if number in played_numbers:
            roles.add("played")
        if number in captured:
            roles.add("captured")
        if number in missed:
            roles.add("missed")
        nodes.append(_node(number, roles))

    edges: list[dict[str, object]] = []
    for left, right in combinations(result, 2):
        edges.append(_edge(left, right, "same_draw", f"Ambos aparecen en el sorteo {draw}."))
        if number_block(left) == number_block(right):
            edges.append(_edge(left, right, "same_block", "Comparten bloque de revisión."))
        if left >= 41 and right >= 41:
            edges.append(_edge(left, right, "high_block_pair", "Pareja dentro del bloque 41_56."))
        if abs(left - right) == 1 and left >= 41 and right >= 41:
            edges.append(_edge(left, right, "adjacent_high_pair", "Par alto adyacente en el rastro."))

    for number in result:
        edges.append(_edge(number, number, "trace_member", f"Miembro del rastro del sorteo {draw}."))

    for left, right in captured_pairs(captured):
        edges.append(_edge(left, right, "captured_together", "Capturados dentro del set jugado."))

    missed_relations = select_missed_played_relations(missed, played_numbers, captured, repeated_anchors)
    for number, played_number, reasons in missed_relations:
        reason_text = ", ".join(reasons)
        edge = _edge(
            number,
            played_number,
            "missed_from_played_set",
            f"No capturado frente a referencia jugada: {reason_text}.",
        )
        edge["relation_reasons"] = reasons
        edges.append(edge)

    graph = {
        "nodes": nodes,
        "edges": edges,
        "edge_summary": summarize_edges(edges),
        "graph_stats": build_graph_stats(nodes, edges, result, played_numbers, captured, missed, missed_relations),
        "metadata": {"draw": int(draw), "review_mode": "review_default"},
    }
    return validate_output_json(graph)


def export_relation_graph(graph: dict[str, object], output_path: str | Path) -> Path:
    validate_output_json(graph)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
