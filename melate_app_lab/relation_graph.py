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


def build_historical_relation_graph(
    history: list[dict[str, object]],
    window: int = 30,
    game: str = "revancha",
) -> dict[str, object]:
    """Build a relation graph from the last *window* draws of *game* in history.

    Returns a dict with mode="historical", nodes with frequency/degree data,
    and edges with co-occurrence counts and draw evidence.
    """
    # Filter by game (case-insensitive) and take last N
    filtered = [d for d in history if str(d.get("game", "")).casefold() == game.casefold()]
    recent = filtered[-window:] if len(filtered) >= window else filtered

    # --- gather per-number stats ---
    from collections import Counter, defaultdict

    frequency: Counter[int] = Counter()
    number_draws: defaultdict[int, list[int]] = defaultdict(list)
    pair_count: Counter[tuple[int, int]] = Counter()
    pair_draws: defaultdict[tuple[int, int], list[int]] = defaultdict(list)

    draw_ids_used: list[int] = []

    for draw_record in recent:
        draw_id = int(draw_record.get("draw", 0))
        draw_ids_used.append(draw_id)
        nums = sorted(draw_record.get("numbers", []))
        for n in nums:
            frequency[n] += 1
            number_draws[n].append(draw_id)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                pair = (nums[i], nums[j])
                pair_count[pair] += 1
                pair_draws[pair].append(draw_id)

    # --- build nodes ---
    # Compute degree / weighted degree
    degree: Counter[int] = Counter()
    weighted_degree: Counter[int] = Counter()
    for (a, b), cnt in pair_count.items():
        degree[a] += 1
        degree[b] += 1
        weighted_degree[a] += cnt
        weighted_degree[b] += cnt

    nodes: list[dict[str, object]] = []
    for number in sorted(frequency):
        nodes.append({
            "id": str(number),
            "number": number,
            "frequency": frequency[number],
            "block": number_block(number),
            "last_seen_draws": number_draws[number][-3:],
            "degree": degree.get(number, 0),
            "weighted_degree": weighted_degree.get(number, 0),
        })

    # --- build edges ---
    edges: list[dict[str, object]] = []
    for (a, b), cnt in pair_count.items():
        edges.append({
            "id": f"{a}-{b}",
            "source": str(a),
            "target": str(b),
            "type": "historical_cooccurrence",
            "count": cnt,
            "draws": pair_draws[(a, b)],
            "last_seen_draw": pair_draws[(a, b)][-1],
        })

    graph = {
        "mode": "historical",
        "game": game,
        "window": window,
        "draws_used": draw_ids_used,
        "draws_count": len(recent),
        "nodes": nodes,
        "edges": edges,
    }
    return validate_output_json(graph)
